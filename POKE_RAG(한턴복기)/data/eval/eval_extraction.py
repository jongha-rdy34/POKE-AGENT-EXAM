"""추출 정확도 평가 (CEO C1-1, eng #3 R5). 정답: data/eval/extraction_gold.jsonl (커뮤니티 review 18건 + 직접 쓴 17건, 사용자 확인 전 초안).
  .venv/Scripts/python -m data.eval.eval_extraction            # 실제 LLM(GMS) 호출, 35회
  .venv/Scripts/python -m data.eval.eval_extraction --gold-only # LLM 없이 정답 칸이 계산되는지만 확인
보고: 칸별 정확도(정답이 있는 칸만), 전부 맞은 비율, 그리고 따로 "계산 가능 여부"(정답 칸으로 / 추출 칸으로).
"""
import json
import sys
from datetime import date
from pathlib import Path

from prep import calculator as c
from prep import review as rv
from server import extract as ex

GOLD = Path(__file__).with_name("extraction_gold.jsonl")
REPORTS = Path(__file__).with_name("reports")


def load():
    return [json.loads(line) for line in open(GOLD, encoding="utf-8")]


def gold_request(e):
    """정답 칸 → review() 요청. 공격 측이 정해져 있어야 만든다."""
    if not (e["actor"] and e["attacker"] and e["defender"] and e["move_key"] and e["kind"]):
        return None
    me, opp = (e["attacker"], e["defender"]) if e["actor"] == "me" else (e["defender"], e["attacker"])
    req = {"my_form_key": me, "opp_form_key": opp, "actor": e["actor"], "move_key": e["move_key"], "actual": {"kind": e["kind"]}}
    if e["hp_band"]:
        req["actual"]["hp_band"] = e["hp_band"][0]
    if e["my_sp"]:
        req["my_build"] = {"sp": e["my_sp"]}
    if e["opp_sp"]:
        req["opp_sp"] = e["opp_sp"]
    return req


def runs(db, req):
    """'ok' / 'reference_only' / 'error: ...'"""
    if req is None:
        return "incomplete"
    try:
        out = rv.review(db, req)
    except ValueError as err:
        return f"error: {err}"
    return "reference_only" if out["reference_only"] else "ok"


def score(e, got):
    """칸별 (정답 있음, 맞음). 공격 측을 모르면 두 이름을 순서 없이 비교한다."""
    f = got.get("fields", {})
    actor = f.get("actor")
    me, opp = f.get("my_form_key"), f.get("opp_form_key")
    atk, dfn = ((me, opp) if actor == "me" else (opp, me)) if actor else (None, None)
    res = {"type": got["type"] == e["type"]}
    if e["type"] != "review":
        return res
    if e["actor"]:
        res["actor"] = actor == e["actor"]
        if e["attacker"]:
            res["attacker"] = atk == e["attacker"]
        if e["defender"]:
            res["defender"] = dfn == e["defender"]
    else:
        names = {x for x in (e["attacker"], e["defender"]) if x}
        if names:
            res["names"] = names <= {me, opp}
    if e["move_key"]:
        res["move_key"] = f.get("move_key") == e["move_key"]
    if e["kind"]:
        res["kind"] = f.get("actual", {}).get("kind") == e["kind"]
    if e["hp_band"]:
        res["hp_band"] = f.get("actual", {}).get("hp_band") in e["hp_band"]
    if e["my_sp"]:
        res["my_sp"] = f.get("my_build", {}).get("sp") == e["my_sp"]
    if e["opp_sp"]:
        res["opp_sp"] = f.get("opp_sp") == e["opp_sp"]
    return res


def main(gold_only=False, llm=ex.default_llm):
    db, rows, report = c.connect(), load(), []
    for r in rows:
        item = {"id": r["id"], "gold_runs": runs(db, gold_request(r["expected"])), "computable": r["computable"]}
        if not gold_only:
            got = ex.extract(db, r["text"], llm)
            item.update(got=got, score=score(r["expected"], got))
            if got["type"] == "review" and not got["missing"]:
                item["extracted_runs"] = runs(db, dict(got["fields"]))
        report.append(item)
    mismatch = [x["id"] for x in report if x["computable"] != (x["gold_runs"] in ("ok", "reference_only"))]
    summary = {"cases": len(report), "gold_computable_mismatch": mismatch}
    if not gold_only:
        fields = {}
        for x in report:
            for k, ok in x["score"].items():
                fields.setdefault(k, []).append(ok)
        summary["field_accuracy"] = {k: f"{sum(v)}/{len(v)}" for k, v in fields.items()}
        summary["all_correct"] = f"{sum(all(x['score'].values()) for x in report)}/{len(report)}"
        summary["fail_reasons"] = [x["got"].get("reason") for x in report if x["got"]["type"] == "fail"]
        comp = [x for x in report if x["computable"]]
        summary["computable_extracted_ok"] = f"{sum(x.get('extracted_runs') in ('ok', 'reference_only') for x in comp)}/{len(comp)}"
        REPORTS.mkdir(exist_ok=True)
        (REPORTS / f"extraction-{date.today().isoformat()}.json").write_text(
            json.dumps({"summary": summary, "cases": report}, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(main(gold_only="--gold-only" in sys.argv), ensure_ascii=False, indent=1))
