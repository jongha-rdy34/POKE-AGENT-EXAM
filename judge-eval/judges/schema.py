"""판정 응답 스키마 검사. API 판정과 수동(ChatGPT) 판정이 같은 함수를 쓴다."""
import json
import re

ITEMS = ("accuracy", "purpose_fit", "usability", "ui", "code")
PAIR_ITEMS = ITEMS + ("overall",)


def parse(text):
    """응답 문자열 → dict. 앞뒤 코드 블록 표시만 걷어 내고, 그 밖의 수정은 하지 않는다."""
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    return json.loads(s)


def validate(obj, mode):
    """문제 목록을 돌려준다. 빈 목록이면 통과."""
    errs = []
    if not isinstance(obj, dict):
        return ["not an object"]
    if obj.get("mode") != mode:
        errs.append(f"mode != {mode}")
    r = obj.get("rationale")
    if not (isinstance(r, list) and len(r) == 3 and all(isinstance(x, str) and x.strip() for x in r)):
        errs.append("rationale must be 3 non-empty strings")
    if mode == "absolute":
        sc = obj.get("scores")
        if not isinstance(sc, dict):
            errs.append("scores missing")
        else:
            for k in ITEMS:
                v = sc.get(k)
                if not (isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 5):
                    errs.append(f"scores.{k} must be int 1..5")
    else:
        if obj.get("order") not in ("XY", "YX"):
            errs.append("order must be XY|YX")
        pw = obj.get("pairwise")
        if not isinstance(pw, dict):
            errs.append("pairwise missing")
        else:
            for k in PAIR_ITEMS:
                if pw.get(k) not in ("X", "Y", "tie"):
                    errs.append(f"pairwise.{k} must be X|Y|tie")
    return errs
