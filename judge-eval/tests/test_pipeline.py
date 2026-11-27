"""판정·집계 파이프라인 시험(LLM·키 불필요). 결과는 임시 폴더에만 쓴다(analysis/에 섞이지 않게).

  python -m unittest discover -s tests -t .      (judge-eval/에서)
"""
import csv
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

EVAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL / "scripts"))
sys.path.insert(0, str(EVAL / "judges"))
import aggregate as ag  # noqa: E402
import judge as jg  # noqa: E402
from anonymize import redact  # noqa: E402
from schema import validate  # noqa: E402


def abs_rec(judge, label, run, s, model=None):
    return {"judge": judge, "judge_model": model, "run_id": f"abs_{label}_r{run}", "status": "ok", "retries": 0,
            "parsed": {"mode": "absolute", "scores": dict(zip(ag.ITEMS, s)), "rationale": ["a", "b", "c"]}}


def pw_rec(judge, order, run, pick):
    return {"judge": judge, "run_id": f"pw_{order}_r{run}", "status": "ok", "retries": 0,
            "parsed": {"mode": "pairwise", "order": order, "pairwise": {k: pick for k in ag.PAIR_ITEMS},
                       "rationale": ["a", "b", "c"]}}


class Alpha(unittest.TestCase):
    def test_hand_computed_interval(self):
        # u1=[1,2], u2=[3,3]: Do=0.5, De=22/12 → 1-0.5/(22/12)=0.72727
        a, n = ag.krippendorff_alpha({"u1": [1, 2], "u2": [3, 3]}, "interval")
        self.assertAlmostEqual(a, 1 - 0.5 / (22 / 12), places=6)
        self.assertEqual(n, 2)

    def test_perfect_agreement(self):
        self.assertEqual(ag.krippendorff_alpha({"u1": [2, 2], "u2": [5, 5]}, "interval")[0], 1.0)
        self.assertEqual(ag.krippendorff_alpha({"u1": [0, 0, 0], "u2": [1, 1]}, "nominal")[0], 1.0)

    def test_against_reference_package(self):
        try:
            import krippendorff  # pip install krippendorff (선택)
            import numpy as np
        except ImportError:
            self.skipTest("krippendorff 패키지 없음")
        rng = random.Random(7)
        for metric in ("interval", "nominal"):
            coders = [[rng.randint(1, 5) for _ in range(12)] for _ in range(3)]
            units = {i: [c[i] for c in coders] for i in range(12)}
            ours, _ = ag.krippendorff_alpha(units, metric)
            ref = krippendorff.alpha(reliability_data=np.array(coders, dtype=float), level_of_measurement=metric)
            self.assertAlmostEqual(ours, ref, places=6, msg=metric)


class Aggregate(unittest.TestCase):
    def run_pipeline(self, records, mapping):
        tmp = Path(tempfile.mkdtemp())
        raw = tmp / "raw"
        raw.mkdir()
        by = {}
        for r in records:
            by.setdefault(r["judge"], []).append(r)
        for j, rs in by.items():
            (raw / f"{j}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rs), encoding="utf-8")
        rows = ag.compute(ag.load(raw), mapping)
        ag.write_csv(rows, tmp / "summary.csv")
        ag.report(tmp / "summary.csv", tmp / "report.md")
        with open(tmp / "summary.csv", encoding="utf-8") as f:
            return {(r["metric"], r["judge"], r["app"], r["item"]): r for r in csv.DictReader(f)}, (tmp / "report.md").read_text(encoding="utf-8")

    def test_mapping_and_position_bias(self):
        # X=B, Y=A로 배정. 판정 모델 g는 늘 먼저 보인 쪽을 고른다 → 순서 교체 시 100% 뒤집힘
        recs = [pw_rec("g", "XY", r, "X") for r in (1, 2, 3)] + [pw_rec("g", "YX", r, "Y") for r in (1, 2, 3)]
        s, rep = self.run_pipeline(recs, {"X": "B", "Y": "A"})
        self.assertEqual(float(s[("position_flip_rate", "ALL", "", "overall")]["value"]), 1.0)
        self.assertEqual(float(s[("first_position_pick_rate", "ALL", "", "overall")]["value"]), 1.0)
        self.assertEqual(float(s[("pw_rate", "ALL", "A", "overall")]["value"]), 0.5)

    def test_absolute_means_follow_mapping(self):
        recs = [abs_rec("g", "X", r, [5, 5, 5, 5, 5]) for r in (1, 2, 3)] + [abs_rec("g", "Y", r, [1, 2, 3, 4, 5]) for r in (1, 2, 3)]
        s, _ = self.run_pipeline(recs, {"X": "B", "Y": "A"})
        self.assertEqual(float(s[("abs_mean", "ALL", "B", "total")]["value"]), 25)
        self.assertEqual(float(s[("abs_mean", "ALL", "A", "total")]["value"]), 15)
        self.assertEqual(float(s[("abs_sd", "g", "A", "accuracy")]["value"]), 0)  # 회차 간 표준편차
        self.assertEqual(s[("abs_sd", "ALL", "A", "accuracy")]["value"], "")  # 판정 모델 1개면 판정 모델 간 편차 없음

    def test_self_preference_and_failures(self):
        recs = [abs_rec("claude", "X", 1, [5] * 5), abs_rec("gemini", "X", 1, [3] * 5),
                {"judge": "gemini", "run_id": "abs_Y_r1", "status": "schema_fail", "retries": 2, "parsed": None}]
        s, _ = self.run_pipeline(recs, {"X": "A", "Y": "B"})
        self.assertEqual(float(s[("self_pref_abs_diff", "claude", "A", "accuracy")]["value"]), 2)
        self.assertAlmostEqual(float(s[("fail_rate", "ALL", "", "")]["value"]), 1 / 3, places=3)

    def test_report_numbers_come_from_csv(self):
        recs = [abs_rec("g", "X", r, [4, 4, 4, 4, 4]) for r in (1, 2, 3)] + [abs_rec("g", "Y", r, [2] * 5) for r in (1, 2, 3)]
        s, rep = self.run_pipeline(recs, {"X": "A", "Y": "B"})
        summary = rep.split("## 요약 (5줄)")[1].split("## 1.")[0]
        self.assertEqual(sum(1 for line in summary.splitlines() if line[:2] in ("1.", "2.", "3.", "4.", "5.")), 5)
        self.assertIn("A 20.00, B 10.00", summary)

    def test_import_manual_format(self):
        # import_manual.py가 만드는 형식(judge 키 없음, 파일 이름이 판정 모델)
        rec = {"source": "chatgpt_app", "run_id": "abs_X_r2", "mode": "absolute", "status": "ok",
               "parsed": {"mode": "absolute", "scores": dict(zip(ag.ITEMS, [3] * 5)), "rationale": ["a", "b", "c"]}}
        tmp = Path(tempfile.mkdtemp())
        (tmp / "chatgpt.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")
        r = ag.load(tmp)[0]
        self.assertEqual((r["judge"], r["label"], r["run"]), ("chatgpt", "X", 2))


class Mixing(unittest.TestCase):
    """Gemini 판정: flash-lite 7회차 : flash 3회차 (사용자 결정 2026-11-27)."""

    def test_default_plan_is_7_to_3_and_interleaved(self):
        plan = {m: runs for m, runs, _ in jg.gemini_plan(jg.GEMINI_PLAN_DEFAULT)}
        self.assertEqual(len(plan["gemini-3.5-flash-lite"]), 7)
        self.assertEqual(len(plan["gemini-3.5-flash"]), 3)
        self.assertEqual(sorted(plan["gemini-3.5-flash-lite"] + plan["gemini-3.5-flash"]), list(range(1, 11)))
        self.assertNotEqual(plan["gemini-3.5-flash"], [8, 9, 10])     # 끝에 몰리지 않는다

    def test_each_model_gets_balanced_apps_and_orders(self):
        for model, runs, _ in jg.gemini_plan(jg.GEMINI_PLAN_DEFAULT):
            jobs = jg.plan(runs)
            self.assertEqual(sum(j["app"] == "X" for j in jobs), sum(j["app"] == "Y" for j in jobs))
            self.assertEqual(sum(j["order"] == "XY" for j in jobs), sum(j["order"] == "YX" for j in jobs))
            self.assertEqual(len(jobs), 4 * len(runs))

    def test_judges_are_equally_weighted_and_submodels_reported(self):
        # gemini 10회차 전부 5점, claude 3회차 전부 1점 → 단순 합산이면 약 4.08, 동일 가중이면 3.0
        recs = [abs_rec("gemini", "X", r, [5] * 5, "lite" if r % 3 else "flash") for r in range(1, 11)]
        recs += [abs_rec("claude", "X", r, [1] * 5) for r in (1, 2, 3)]
        s, rep = Aggregate().run_pipeline(recs, {"X": "A", "Y": "B"})
        self.assertEqual(float(s[("abs_mean", "ALL", "A", "accuracy")]["value"]), 3.0)
        self.assertEqual(s[("abs_mean", "gemini:flash", "A", "accuracy")]["n"], "3")
        self.assertIn("gemini:lite", rep)


class Schema(unittest.TestCase):
    def test_rejects_bad_scores(self):
        self.assertTrue(validate({"mode": "absolute", "scores": {k: 6 for k in ag.ITEMS}, "rationale": ["a", "b", "c"]}, "absolute"))
        self.assertFalse(validate({"mode": "absolute", "scores": {k: 3 for k in ag.ITEMS}, "rationale": ["a", "b", "c"]}, "absolute"))


class Anonymize(unittest.TestCase):
    def test_removes_traces_without_markers(self):
        text, hits = redact("계산(eng #3 R4, D25)은 한 턴 복기 코치가 GMS로 한다 # noqa: F401")
        self.assertNotIn("[ref]", text)
        self.assertNotIn("eng", text)
        self.assertIn("noqa: F401", text)
        self.assertIn("[service]", text)
        self.assertTrue(hits)


if __name__ == "__main__":
    unittest.main()
