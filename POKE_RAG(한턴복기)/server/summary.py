"""복기 결과 → 짧은 설명 (D32: 계산은 코드가 두 번, LLM은 한 번). LLM은 아래 payload에 있는 사실만 문장으로 옮긴다.
- 결론은 타격 단위·조건부(CEO C-O3), %는 쓰지 않는다(C-O1), Smogon은 시뮬레이터 데이터라고 밝힌다(D31).
- R7: 요약의 숫자가 payload에 없거나 %가 있으면 버리고 템플릿으로 바꾼다(degraded). 키가 없거나 호출이 실패해도 템플릿.
"""
import json
import math
import re

import config

from server import llm

PROMPT = """너는 포켓몬 챔피언스 랭크배틀 뉴비에게 한 턴 복기 결과를 설명한다. 사용자가 준 facts 문장을 뉴비가 읽기 쉬운 한국어로 다듬기만 한다.
규칙:
1. facts에 없는 주장·도구나 특성의 효과 설명·추측·조언을 덧붙이지 않는다. facts의 순서와 뜻을 그대로 지킨다.
2. 퍼센트(%)·확률 숫자를 쓰지 않는다. 숫자는 facts에 있는 것만 그대로 쓴다.
3. "~일 때 가장 잘 맞아요" 같은 조건부 표현을 단정으로 바꾸지 않는다. "Showdown 시뮬레이터", "챔피언스에 없는 도구", "참고용" 표기는 그대로 둔다.
4. 출력은 다듬은 문장만. 문장 수는 facts 문장 수를 넘기지 않는다.
"""


def _ko(db, cause):
    if cause["key"].startswith("_"):
        return cause["label"]
    row = db.execute("SELECT name_ko FROM item WHERE key=?", (cause["key"],)).fetchone()
    return (row and row[0]) or cause["label"]


def payload(db, out):
    """LLM에 줄 사실. 확률(prob·match_ratio)은 넣지 않고 순서만 남긴다."""
    bases = {}
    for name, b in out["bases"].items():
        bases[name] = {"source": b["source"]["label"], "zero_match": b["zero_match"], "undetermined": b["undetermined"],
                       "causes": [{"rank": i + 1, "key": x["key"], "name": _ko(db, x), "rolls": x["rolls"], "condition": condition_ko(db, x["conditions_raw"][0]) if x["conditions_raw"] else None}
                                  for i, x in enumerate(b["causes"])]}
    calc = public_calc(db, out) if out.get("calc") else None
    return {"bases": bases, "calc": calc and {"rows": [{"label": r["label"], "k": r["k"], "in_champions": r["in_champions"]} for r in calc["rows"][:2]],
                                             "near": [r["label"] for r in calc["near"][:1]]},
            "kind": out.get("kind"), "actor": out.get("actor"), "differs": out["differs"], "reference_only": out["reference_only"],
            "unsupported": out["unsupported"], "assumptions": out["assumptions"]}


def template(p):
    """코드가 쓰는 사실 문장. LLM 요약은 이 문장만 다듬고(D32), LLM이 없거나 검사에 걸리면 이것을 그대로 쓴다(degraded)."""
    if not p["bases"]:
        return "이 턴은 계산하지 않는 상황이라 답할 수 없어요. " + " ".join(p["unsupported"])
    lines = ["계산하지 않은 상황이 있어 참고용이에요."] if p["reference_only"] else []
    lines += calc_lines(p)
    for name in (("pokedb", "smogon") if p["differs"] else ("pokedb",)):
        b = p["bases"][name]
        where = "Showdown 시뮬레이터 환경에서 모은 데이터 기준" if name == "smogon" else "실제 랭크배틀 통계 기준"
        if b["zero_match"] or not b["causes"]:
            lines.append(f"{where}으로는 입력한 조건에서 이 결과가 나오기 어려워요. 입력을 확인해 주세요.")
            continue
        top = b["causes"][0]
        rolls = f"({top['rolls']})" if top["rolls"] else ""
        what = "이 행동 순서는" if p.get("kind") in ("outsped", "slower") else "이 타격은"
        if top["key"] == "_atk_minus1":
            lines.append(f"{where}, {what} 내 공격이 한 단계 내려가 있었을 때(위협 등) 가장 잘 맞아요{rolls}.")
        elif b["undetermined"]:
            lines.append(f"{where}, 상대 도구로는 이 결과를 구분하기 어려워요{rolls}.")
        elif top["key"] == "_neutral":
            lines.append(f"{where}, {what} 상대가 결과를 바꾸는 도구를 들지 않았을 때 가장 잘 맞아요{rolls}.")
        else:
            lines.append(f"{where}, {what} 상대가 '{top['name']}'일 때 가장 잘 맞아요{rolls}.")
    if p["unsupported"]:
        lines.append("계산에 넣지 않은 것: " + "; ".join(p["unsupported"]) + ".")
    return " ".join(lines)


def calc_lines(p):
    """계산표 사실 문장(사용자 지시 2026-10-23: 계산을 먼저). 통계 문장보다 앞에 온다."""
    calc, kind = p.get("calc"), p.get("kind")
    if not calc:
        return []
    if not calc["rows"]:
        if calc["near"]:
            return [f"계산상, 상대가 흔한 빌드라면 이 결과가 나오기 어려워요. 가장 가까운 경우는 상대가 {calc['near'][0]}일 때예요."]
        return ["계산상, 상대가 흔한 빌드라면 이 결과가 나오기 어려워요."]
    out = []
    for i, r in enumerate(calc["rows"]):
        cond = f"상대가 {r['label']}" + ("(챔피언스에 없는 도구)" if not r["in_champions"] else "")
        if kind == "ko":
            what = f"16번 중 {r['k']}번 한 방이에요"
        elif kind == "survived":
            what = f"16번 중 {r['k']}번 이 HP로 버텨요"
        else:
            what = "상대가 먼저 움직여요" if kind == "outsped" else "내가 먼저 움직여요"
        out.append(("계산상, " if i == 0 else "또는 ") + f"{cond}일 때 {what}.")
    return out


KEEP = ("챔피언스에 없는 도구", "Showdown 시뮬레이터", "참고용")  # 사실 문장에 있으면 다듬은 문장에도 남아야 하는 표기


def check(text, p, facts=""):
    """R7: %가 없고, 모든 숫자가 payload 안에 있고, facts의 꼭 남길 표기(KEEP)가 지워지지 않아야 통과."""
    if not text or "%" in text or "퍼센트" in text:
        return False
    if any(k in facts and k not in text for k in KEEP):
        return False
    allowed = set(re.findall(r"\d+", json.dumps(p, ensure_ascii=False)))
    return all(n in allowed for n in re.findall(r"\d+", text))


def summarize(db, out, chat=llm.chat):
    """(문장, degraded, LLM 호출 수)"""
    p = payload(db, out)
    if not p["bases"] or not config.REVIEW_SUMMARY_LLM:
        return template(p), False, 0
    facts = template(p)
    try:
        text = chat(PROMPT, facts).strip()
    except Exception:
        return facts, True, 0
    return (text, False, 1) if check(text, p, facts) else (facts, True, 1)


SP_LETTER = {"hp": "H", "atk": "A", "def": "B", "spa": "C", "spd": "D", "spe": "S"}


def _name(db, table, key):
    row = db.execute(f"SELECT name_ko FROM {table} WHERE key=?", (key,)).fetchone() if key else None
    return (row and row[0]) or key


def condition_ko(db, cond):
    """{"nature", "sp", "ability", "item_group"} → "고집 · A32 B32 · 특성 멀티스케일" (+ 위협 후보면 상대 도구 묶음)."""
    sp = " ".join(f"{SP_LETTER[s]}{cond['sp'][s]}" for s in SP_LETTER if cond["sp"].get(s)) or "SP 무투자"
    parts = [_name(db, "nature", cond["nature"]), sp]
    if cond["ability"]:
        parts.append("특성 " + _name(db, "ability", cond["ability"]))
    if cond["item_group"]:
        parts.append(_ko(db, {"key": cond["item_group"], "label": "도구 없음·영향 없는 도구"}))
    return " · ".join(parts)


def _calc_label(db, r):
    sp = " ".join(f"{SP_LETTER[s]}{r['sp'][s]}" for s in SP_LETTER if r["sp"].get(s))
    parts = [sp, _name(db, "nature", r["nature"])]
    if r["abilities"]:
        parts.append("특성 " + "·".join(_name(db, "ability", a) for a in r["abilities"]))
    parts.append(_name(db, "item", r["item"]) if r["item"] else "도구 없음")
    return " · ".join(parts)


def _share(x):
    """채용률 문구. 반올림해 0%가 되면 "안 쓴다"로 읽혀서 1% 미만으로 쓴다(디자인 W5)."""
    return "1% 미만" if x * 100 < 0.5 else f"{round(x * 100)}%"


def public_calc(db, out):
    """계산표 → 화면용. 난수 비율(k/16)과 데미지 범위는 계산 사실이라 %로도 보여 준다(원인 확률은 여전히 숨김, C-O1)."""
    calc, speed = out["calc"], out.get("kind") in ("outsped", "slower")
    season = None
    if out["bases"].get("pokedb"):
        m = re.search(r"M-\d+", out["bases"]["pokedb"]["source"]["label"])
        season = m and m.group()

    def row(r):
        u = r["usage"]
        usage = [f"pokedb {season or ''} 이 포켓몬 {_name(db, 'item', r['item'])} 채용 {_share(u['pokedb_item'])}".replace("  ", " ")] if r["item"] and u["pokedb_item"] else []
        if r["item"] and u["smogon_item"]:
            usage.append(f"Smogon {_name(db, 'item', r['item'])} 채용 {_share(u['smogon_item'])}")
        if u["smogon_ability"]:
            usage.append(f"Smogon {'·'.join(_name(db, 'ability', a) for a in r['abilities'])} 채용 {_share(u['smogon_ability'])}")
        base = {"label": _calc_label(db, r), "in_champions": r["in_champions"], "same_items": [_name(db, "item", i) for i in r["same_items"]], "usage": usage}
        if speed:
            return dict(base, k=None, speed={"opp": r["value"][0], "me": r["value"][1]})
        return dict(base, k=r["k"], pct=math.floor(r["k"] * 1000 / 16 + 0.5) / 10, damage=r["value"])  # 1/16 = 6.3%(반올림, 계산기 관례)
    return {"rows": [row(r) for r in calc["rows"]], "more": calc["more"], "near": [row(r) for r in calc["near"]],
            "assumed": calc["assumed"], "my_build": _calc_label(db, dict(calc["my_build"], abilities=[calc["my_build"]["ability"]] if calc["my_build"]["ability"] else None))}


def public_causes(db, out):
    """화면에 보낼 원인: 확률 숫자를 빼고 순위만(CEO-T5, C-O1). 순서는 내부 비중 순 그대로. 성립 조건은 한글로."""
    return {name: dict({k: v for k, v in b.items() if k != "causes"},
                       causes=[{"key": x["key"], "label": _ko(db, x), "rank": i + 1, "rolls": x["rolls"], "rolls_k": x["rolls_k"],
                                "conditions": [condition_ko(db, cnd) for cnd in x["conditions_raw"]]}
                               for i, x in enumerate(b["causes"])])
            for name, b in out["bases"].items()}


# --- 결론 한 문장 headline (디자인 E1, docs/designs/HANDOFF-design-to-engineering.md "E1 문장 규칙") ---
def display_name(name):
    """DB의 "망나뇽 (Mega Dragonite)" → "메가망나뇽"(별칭과 같은 표기). 다른 폼 표기("킬가르도 (실드폼)")는 그대로."""
    m = re.fullmatch(r"(.+?) \(Mega [^)]*?( [XYZ])?\)", name or "")
    return f"메가{m.group(1)}{(m.group(2) or '').strip()}" if m else name


def josa(word, with_final, without):
    """받침이 있으면 with_final("이"·"은"·"이면"), 없으면 without. 한글이 아니면 without."""
    ch = ord(word[-1]) if word else 0
    return with_final if 0xAC00 <= ch <= 0xD7A3 and (ch - 0xAC00) % 28 else without


def _poke(db, form_key):
    row = db.execute("SELECT name_ko FROM pokemon WHERE form_key=?", (form_key,)).fetchone()
    return display_name(row[0]) if row else form_key


def _short(db, r):
    """줄의 짧은 이름: 성격 + (결과를 가르는 특성) + 도구. 도구가 없으면 None 자리를 비운다."""
    parts = [_name(db, "nature", r["nature"])]
    if r["abilities"]:
        parts.append("·".join(_name(db, "ability", a) for a in r["abilities"]))
    if r["item"]:
        parts.append(_name(db, "item", r["item"]))
    return " ".join(parts)


def headline(db, out, req):
    """계산표 첫 줄(챔피언스 도구 우선 정렬)로 결론 한 문장. 숫자는 k뿐, %·괄호 없음. calc가 없으면 summary 첫 문장(부르는 쪽).
    반환 (문장, 결론이 가리키는 calc.rows 번호 또는 None). 화면은 그 줄의 띠에만 청록을 칠한다(디자인 W3)."""
    calc, kind = out.get("calc"), out.get("kind")
    if not calc:
        return None, None
    rows = calc["rows"]
    if not rows:
        return "상대가 흔한 빌드라면 계산상 이 결과가 나오기 어려워요", None
    top = rows[0]
    if kind in ("outsped", "slower"):  # 스피드: 도구 없이도 성립하면 그 사실이 더 강한 답이다
        top = next((r for r in rows if not r["item"]), top)
    if not top["in_champions"]:
        return "지금 챔피언스에 있는 도구로는 이 결과가 나오기 어려워요", None
    short = _short(db, top)
    cond = f"상대가 {short}{josa(short, '이면', '면')}" if top["item"] else f"상대가 도구 없이 {short}{josa(short, '이면', '면')}"
    me, opp = _poke(db, req["my_form_key"]), _poke(db, req["opp_form_key"])
    row = rows.index(top)
    if kind == "ko":
        if any(not r["in_champions"] and r["k"] > top["k"] for r in rows):
            return f"챔피언스에 있는 도구로는 16번 중 {top['k']}번만 한 방이에요", row
        return (f"{cond} 확정 1타예요" if top["k"] == 16 else f"{cond} 16번 중 {top['k']}번 한 방이에요"), row
    if kind == "survived":
        return f"{cond} 16번 중 {top['k']}번 이 HP로 버텨요", row
    if kind == "outsped":
        if not top["item"]:
            return f"상대 {opp}{josa(opp, '은', '는')} 도구 없이도 내 {me}보다 빨라요", row
        item = _name(db, "item", top["item"])
        return f"상대 {opp}{josa(opp, '이', '가')} {item}{josa(item, '이면', '면')} 내 {me}보다 빨라요", row
    return f"{cond} 내 {me}보다 느려요", row  # slower: 내가 먼저 움직였다(디자인 제안 문장)


def answer(db, out, req, text, degraded):
    """SSE answer 본문(review_id 제외). 서버와 응답 예시(docs/designs/samples)가 같은 함수를 쓴다."""
    head, row = headline(db, out, req)
    calc = public_calc(db, out) if out.get("calc") else None
    if calc is not None:
        calc["headline_row"] = row
    return {"headline": head or re.split(r"(?<=[.!?요다])\s", text, maxsplit=1)[0], "summary": text, "calc": calc,
            "bases": public_causes(db, out), "differs": out["differs"], "diff_reason": out.get("diff_reason"),
            "unsupported": out["unsupported"], "assumptions": out["assumptions"], "reference_only": out["reference_only"],
            "degraded": degraded}
