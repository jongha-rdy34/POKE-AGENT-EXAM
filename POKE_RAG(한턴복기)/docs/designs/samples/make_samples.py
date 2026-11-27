"""디자인 시안용 실제 응답 예시(docs/designs/samples/*.json)를 다시 만든다. 서버와 같은 함수(summary.answer)를 쓴다.
  .venv/Scripts/python -m docs.designs.samples.make_samples      # 프로젝트 루트에서. 요약은 GMS를 부른다(사례 수만큼)
서버 응답 형식이 바뀌면 다시 실행하고 디자인 인계장에 알린다.
"""
import json
from pathlib import Path

from prep import calculator as c
from prep import review as rv
from server import app as srv
from server import summary

OUT = Path(__file__).parent
CASES = {
    "friend1-calc-first": {"my_form_key": "garchomp-mega-z", "opp_form_key": "pawmot", "actor": "opp", "move_key": "ice-punch",
                           "actual": {"kind": "ko"}, "my_build": {"sp": {"hp": 2, "spa": 32, "spe": 32}, "nature": "modest"}},
    "ko": {"my_form_key": "garchomp", "opp_form_key": "dragonite", "actor": "opp", "move_key": "outrage", "actual": {"kind": "ko"}},
    "survived-differs": {"my_form_key": "garchomp", "opp_form_key": "archaludon", "actor": "me", "move_key": "earthquake",
                         "actual": {"kind": "survived", "hp_band": "50-75"}, "my_build": {"sp": {"atk": 20}}},
    "outsped": {"my_form_key": "garchomp", "opp_form_key": "dragapult", "actor": "opp", "move_key": "dragon-darts",
                "actual": {"kind": "outsped"}, "my_build": {"sp": {"spe": 32}, "nature": "jolly", "item": ""}},
    "slower": {"my_form_key": "garchomp", "opp_form_key": "dragonite", "actor": "me", "move_key": "earthquake", "actual": {"kind": "slower"}},
    "reference-only-crit": {"my_form_key": "dragonite", "opp_form_key": "garchomp", "actor": "opp", "move_key": "outrage",
                            "actual": {"kind": "ko"}, "flags": ["crit"]},
    "unsupported-move": {"my_form_key": "garchomp", "opp_form_key": "garchomp", "actor": "opp", "move_key": "body-press", "actual": {"kind": "ko"}},
}


def main():
    db = c.connect()
    for name, req in CASES.items():
        out = rv.review(db, req)
        text, degraded, _ = summary.summarize(db, out)
        ans = dict(summary.answer(db, out, req, text, degraded), review_id="sample-" + name)
        sse = [{"event": "status", "data": {"state": "computing"}}, {"event": "answer", "data": ans}]
        (OUT / f"review-{name}.json").write_text(json.dumps({"request": req, "sse": sse}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{name:20} | {ans['headline']}")
    srv.EXTRACT_LLM = lambda t: json.dumps({"type": "review", "my": "AS한카", "opp": "드래펄트", "move": None, "actor": "opp",
                                            "result": "outsped"}, ensure_ascii=False)  # 재현 가능하게 고정 응답
    x = srv._extract(db, "상대 드래펄트 드래곤애로가 내 AS한카보다 먼저 들어옴")
    x.pop("llm_calls", None)
    x["extraction_id"] = "sample-eid"
    (OUT / "extract-review.json").write_text(json.dumps(x, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
