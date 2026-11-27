"""복기 서버(server/app.py) 흐름: 토큰 → 문장 읽기 → 확인된 칸으로 계산(SSE) → 피드백·삭제. LLM은 고정 응답, 기록은 임시 파일."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import config
from prep import calculator as c
from server import app as srv
from server import logs, summary

EXTRACTED = {"type": "review", "my": "한카리아스", "opp": "망나뇽", "move": "역린", "actor": "opp", "result": "ko"}
REQ = {"my_form_key": "garchomp", "opp_form_key": "dragonite", "actor": "opp", "move_key": "outrage", "actual": {"kind": "ko"}}


def events(resp):
    out = []
    for block in resp.text.strip().split("\n\n"):
        ev, data = block.split("\n", 1)
        out.append((ev.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return out


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not c.DB_PATH.exists():
            raise unittest.SkipTest("pokedex.sqlite 없음: python -m prep.build_db")

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.log = Path(self.dir.name) / "reviews.jsonl"
        self.summary_reply = "이 타격은 상대가 '이 타격에 영향 없는 도구(도구 없음 포함)'일 때 가장 잘 맞아요."
        patches = [mock.patch.multiple(config, INVITE_TOKENS={"s3cret": "친구A"}, REVIEW_LOG=self.log),
                   mock.patch.object(srv, "EXTRACT_LLM", lambda text: json.dumps(EXTRACTED, ensure_ascii=False)),
                   mock.patch.object(srv, "SUMMARY_LLM", lambda system, user: self.summary_reply),
                   mock.patch.object(srv, "quota", srv.access.Quota())]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.client = TestClient(srv.app, base_url="https://testserver")
        self.client.get("/api/quota?t=s3cret", follow_redirects=False)  # 링크 → 쿠키

    def test_requires_token(self):
        self.assertEqual(TestClient(srv.app).post("/api/feature/review/extract", json={"text": "x"}).status_code, 403)

    def test_full_flow(self):
        x = self.client.post("/api/feature/review/extract", json={"text": "망나뇽 역린에 내 한카리아스가 한 방에 죽었어"}).json()
        self.assertEqual(x["fields"], REQ)
        confirmed = dict(x["fields"], actual={"kind": "survived", "hp_band": "<25"})  # 확인 화면에서 결과를 고쳤다
        r = self.client.post("/api/feature/review", json=dict(confirmed, extraction_id=x["extraction_id"]))
        evs = events(r)
        self.assertEqual([e for e, _ in evs], ["status", "answer"])
        ans = evs[1][1]
        self.assertNotIn("%", ans["summary"] + json.dumps(ans["bases"], ensure_ascii=False))  # 원인 확률은 숨긴다(C-O1)
        self.assertNotIn("prob", json.dumps(ans))
        row = ans["calc"]["rows"][0]  # 계산표: 난수 k/16과 %는 계산 사실이라 보여 준다(사용자 지시 2026-10-23)
        self.assertEqual(row["pct"], int(row["k"] * 1000 / 16 + 0.5) / 10)
        self.assertEqual(ans["bases"]["pokedb"]["causes"][0]["rank"], 1)
        rec = [r for r in logs.read(self.log) if r["kind"] == "review"][0]
        self.assertEqual((rec["label"], rec["corrected"], rec["text"]), ("친구A", ["actual"], "망나뇽 역린에 내 한카리아스가 한 방에 죽었어"))
        self.assertNotIn("s3cret", self.log.read_text(encoding="utf-8"))
        fb = self.client.post(f"/api/feature/review/{ans['review_id']}/feedback", json={"answer": "no"})
        self.assertTrue(fb.json()["ok"])
        self.assertEqual(self.client.get("/api/quota").json()["remaining"], {"review": 49, "extract": 99})
        self.assertEqual(self.client.post("/api/feature/review/delete").json()["deleted"], 3)

    def test_summary_with_unknown_number_is_replaced(self):
        self.enterContext(mock.patch.object(config, "REVIEW_SUMMARY_LLM", True))  # 기본은 끔(W1). 켰을 때의 검사
        self.summary_reply = "상대가 생명의구슬일 확률이 80%예요. 16번 중 13번 죽어요."
        ans = events(self.client.post("/api/feature/review", json=REQ))[1][1]
        self.assertTrue(ans["degraded"])
        self.assertNotIn("80", ans["summary"])

    def test_bad_input(self):
        self.assertEqual(self.client.post("/api/feature/review/extract", json={"text": "가" * 301}).status_code, 422)
        self.assertEqual(self.client.post("/api/feature/review", json=dict(REQ, actor="both")).status_code, 422)
        evs = events(self.client.post("/api/feature/review", json=dict(REQ, move_key="no-such-move")))
        self.assertEqual(evs[-1][0], "error")
        self.assertEqual(evs[-1][1]["code"], "bad_input")

    def test_friend_case_calc_first(self):
        """친구 사례 1: 통계에 없는 구애머리띠도 계산표에 나오고, 챔피언스 도구(생명의구슬)가 먼저 온다."""
        req = {"my_form_key": "garchomp-mega-z", "opp_form_key": "pawmot", "actor": "opp", "move_key": "ice-punch", "actual": {"kind": "ko"},
               "my_build": {"sp": {"hp": 2, "spa": 32, "spe": 32}, "nature": "modest"}}
        ans = events(self.client.post("/api/feature/review", json=req))[1][1]
        self.assertEqual([(r["label"], r["k"], r["pct"], r["in_champions"]) for r in ans["calc"]["rows"][:2]],
                         [("A32 · 고집 · 특성 철주먹 · 생명의구슬", 1, 6.3, True), ("A32 · 고집 · 특성 철주먹 · 구애머리띠", 12, 75.0, False)])
        self.assertEqual(ans["headline"], "챔피언스에 있는 도구로는 16번 중 1번만 한 방이에요")  # E1 문장 규칙
        self.assertEqual(ans["calc"]["headline_row"], 0)  # 청록을 칠할 줄(W3)
        self.assertFalse(ans["degraded"])  # 요약 LLM을 부르지 않는다(W1)

    def test_headline_rules(self):
        """E1 문장 규칙 표의 줄마다 한 사례."""
        def head(**req):
            return events(self.client.post("/api/feature/review", json=req))[1][1]["headline"]
        self.assertEqual(head(my_form_key="garchomp", opp_form_key="dragapult", actor="opp", move_key="dragon-darts",
                              actual={"kind": "outsped"}, my_build={"sp": {"spe": 32}, "nature": "jolly", "item": ""}),
                         "상대 드래펄트는 도구 없이도 내 한카리아스보다 빨라요")
        self.assertTrue(head(my_form_key="garchomp", opp_form_key="dragonite", actor="opp", move_key="outrage", actual={"kind": "ko"})
                        .startswith("상대가 고집 "))
        self.assertTrue(head(my_form_key="garchomp", opp_form_key="archaludon", actor="me", move_key="earthquake",
                             actual={"kind": "survived", "hp_band": "50-75"}).endswith("이 HP로 버텨요"))
        self.assertTrue(head(my_form_key="garchomp", opp_form_key="dragonite", actor="me", move_key="earthquake",
                             actual={"kind": "slower"}).endswith("내 한카리아스보다 느려요"))
        self.assertTrue(head(my_form_key="garchomp", opp_form_key="garchomp", actor="opp", move_key="body-press", actual={"kind": "ko"}))

    def test_josa(self):
        self.assertEqual([summary.josa(w, "이면", "면") for w in ("생명의구슬", "구애스카프", "고집")], ["이면", "면", "이면"])

    def test_web_page_served(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn('<script src="app.js">', r.text)
        self.assertEqual(r.headers["referrer-policy"], "no-referrer")
        self.assertEqual(self.client.get("/app.js").status_code, 200)

    def test_lookup_routes(self):
        self.assertIn("garchomp", [p["form_key"] for p in self.client.get("/api/pokemon", params={"q": "한카"}).json()])
        moves = self.client.get("/api/moves", params={"form_key": "garchomp"}).json()
        self.assertIn("earthquake", [m["move_key"] for m in moves])
        self.assertTrue(all(m["category"] in ("물리", "특수") for m in moves))
        self.assertIn("드래곤", self.client.get("/api/pokemon", params={"q": "한카"}).json()[0]["types"])


class Summary(unittest.TestCase):
    P = {"bases": {"pokedb": {"source": "pokedb M-6", "zero_match": False, "undetermined": False,
                              "causes": [{"rank": 1, "key": "life-orb", "name": "생명의구슬", "rolls": "가장 그럴듯한 조건에서 16번 중 12번", "condition": None}]}},
         "differs": False, "reference_only": False, "unsupported": [], "assumptions": []}

    def test_check(self):
        self.assertTrue(summary.check("16번 중 12번 맞아요", self.P))
        self.assertFalse(summary.check("16번 중 13번", self.P))
        self.assertFalse(summary.check("80% 확률", self.P))
        self.assertFalse(summary.check("", self.P))

    def test_check_keeps_required_labels(self):
        facts = "계산상, 상대가 A32 · 고집 · 구애머리띠(챔피언스에 없는 도구)일 때 16번 중 12번 한 방이에요."
        p = dict(self.P, calc={"rows": [{"label": "A32 · 고집 · 구애머리띠", "k": 12, "in_champions": False}], "near": []})
        self.assertFalse(summary.check("상대가 A32 고집 구애머리띠일 때 16번 중 12번 한 방입니다.", p, facts))
        self.assertTrue(summary.check("상대가 A32 고집 구애머리띠(챔피언스에 없는 도구)라면 16번 중 12번 한 방입니다.", p, facts))

    def test_template_uses_payload_only(self):
        t = summary.template(self.P)
        self.assertIn("생명의구슬", t)
        self.assertTrue(summary.check(t, self.P))

    def test_summary_llm_off_by_default(self):
        called = []
        db = c.connect()
        text, degraded, calls = summary.summarize(db, srv.rv.review(db, REQ), lambda s, u: called.append(1) or "x")
        self.assertEqual((called, degraded, calls), ([], False, 0))

    def test_share_under_one_percent(self):
        self.assertEqual([summary._share(x) for x in (0.0004, 0.004, 0.3125)], ["1% 미만", "1% 미만", "31%"])

    def test_no_llm_is_degraded(self):
        self.enterContext(mock.patch.object(config, "REVIEW_SUMMARY_LLM", True))
        def boom(system, user):
            raise RuntimeError("키 없음")
        db = c.connect()
        out = srv.rv.review(db, REQ)
        text, degraded, calls = summary.summarize(db, out, boom)
        self.assertTrue(degraded)
        self.assertEqual(calls, 0)


if __name__ == "__main__":
    unittest.main()
