"""자연어 한 줄 → 복기 입력 칸 (CEO C1-1, eng #3 R2). LLM은 원문 속 이름·누가 쳤는지·결과만 읽고, 키·SP·검증은 코드가 한다.
실패 4유형(깨진 JSON·빈 응답·거절·LLM 호출 실패)은 type="fail"로 돌려 화면이 직접 입력 칸을 연다. 지어낸 이름은 빈 칸이 된다.
"""
import json
import re
import threading
import time
import uuid

import config
from prep import review as rv
from server import llm
from server.summary import josa

PROMPT = """너는 포켓몬 챔피언스 싱글 배틀 복기 입력을 읽는 도구다. 사용자 문장 하나를 읽고 JSON 하나만 출력한다. 설명·코드블록 금지.
{"type": "review" | "rule" | "fail",
 "my": 내 포켓몬 이름, "opp": 상대 포켓몬 이름, "move": 기술 이름  (모두 문장에 적힌 글자 그대로. "메가 갑주무사"처럼 메가도 그대로. 없으면 null)
 "actor": "me"(내가 상대를 공격) | "opp"(상대가 나를 공격) | null,
 "result": "ko"(쓰러짐·한 방·녹음) | "survived"(버팀·못 잡음·피가 남음·0딜) | "outsped"(상대가 먼저 움직임) | "slower"(내가 먼저 움직였는데 문제) | null,
 "hp_band": 맞은 쪽 남은 HP "75+" | "50-75" | "25-50" | "<25" | null  (반피=절반 전후, 딸피=<25, 0딜=75+),
 "flags": ["crit","weather","stat_stage","tera","trick_room","burn","reflect","light_screen","tailwind","terrain"] 중 문장에 나온 것}
type: 특정 한 턴의 결과를 묻는 문장이면 review, 규칙·계산 방식 일반 질문이면 rule, 배틀과 무관하거나 읽을 수 없으면 fail.
"내"·"상대"가 안 적혀 있으면 질문한 사람 쪽을 my로 본다. 확실하지 않은 칸은 null로 둔다. SP·노력치 숫자는 읽지 않는다(코드가 읽는다).
이름이 줄임말·별명("메한카Z", "한카")이거나 앞에 SP·성격이 붙어 있어도("CS 조심 메한카Z") 그대로 옮긴다. 모르는 이름이어도 fail로 하지 않는다.
예) "빠르모트가 그렇게 빠르지 않는데 왜 내 CS 조심 메한카Z가 죽은거지"
→ {"type": "review", "my": "CS 조심 메한카Z", "opp": "빠르모트", "move": null, "actor": "opp", "result": "ko", "hp_band": null, "flags": []}
예) "급소는 왜 벽을 무시해?" → {"type": "rule"}
"""

KINDS = {"ko", "survived", "outsped", "slower"}
SPEED = {"outsped", "slower"}


def default_llm(text):
    """키가 없거나 호출이 실패하면 예외 → type=fail(llm_unavailable)."""
    return llm.chat(PROMPT, text)


def _parse(raw):
    """LLM 응답 → dict, 실패 이유. 코드블록·앞뒤 말은 걷어 낸다."""
    if not raw or not raw.strip():
        return None, "empty"
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None, "broken_json" if "{" in raw else "refusal"  # 여는 괄호만 있으면 잘린 JSON, 아예 없으면 거절·잡담
    try:
        out = json.loads(m.group())
    except json.JSONDecodeError:
        return None, "broken_json"
    return (out, None) if isinstance(out, dict) else (None, "broken_json")


def natures_ko(db):
    """한글 성격 이름(고집·조심 …) → 키."""
    return dict(db.execute("SELECT alias, target_key FROM alias WHERE kind='nature' AND alias GLOB '*[가-힣]*'").fetchall())


def _alias(db, kind, name):
    row = db.execute("SELECT target_key FROM alias WHERE kind=? AND alias=?", (kind, name)).fetchone()
    return row and row[0]


def resolve(db, kind, name):
    """원문 이름 → 키. 별칭 사전(alias)만 쓴다. 띄어쓰기, 앞에 붙은 SP·성격("CS 조심 메한카Z")은 무시하고,
    "메가"·"메" 줄임("메한카Z", "메가 한카")은 그 종의 메가 폼(뒤의 X·Y·Z 포함)으로 찾는다. 못 찾으면 None."""
    if not isinstance(name, str) or not name.strip():
        return None
    tries = [name.strip(), re.sub(r"\s+", "", name)]
    if kind == "pokemon":
        bare = rv.SP_ALIAS.sub("", rv.SP_PAIR.sub("", name.upper()))
        for n in sorted(natures_ko(db), key=len, reverse=True):
            bare = bare.replace(n, "")
        tries.append(re.sub(r"\s+", "", bare))
    for n in tries:
        k = _alias(db, kind, n)
        if k:
            return k
    if kind == "pokemon":
        m = re.fullmatch(r"메가?(.+?)([XYZ])?", tries[-1])
        species_form = m and _alias(db, "pokemon", m.group(1))
        if species_form:
            want = "-mega" + (f"-{m.group(2).lower()}" if m.group(2) else "")
            row = db.execute("SELECT form_key FROM pokemon WHERE is_mega=1 AND in_champions=1 AND form_key LIKE ? AND species=(SELECT species FROM pokemon WHERE form_key=?)",
                             ("%" + want, species_form)).fetchone()
            return row and row[0]
    return None


def move_in_text(db, text):
    """LLM이 기술을 빠뜨렸을 때: 원문에 들어 있는 가장 긴 한글 기술 이름. 확인 화면에서 보이므로 틀려도 고칠 수 있다."""
    best = None
    for alias, key in db.execute("SELECT alias, target_key FROM alias WHERE kind='move' AND length(alias) >= 2 AND alias GLOB '*[가-힣]*'"):
        if alias in text and (best is None or len(alias) > len(best[0])):
            best = (alias, key)
    return best


def learns(db, form_key, move_key):
    """폼이 기술을 배우는가. 메가·폼은 learnset이 비어 있을 수 있어 같은 종 기본 폼도 본다."""
    q = "SELECT 1 FROM learnset WHERE move_key=? AND form_key IN (?, (SELECT form_key FROM pokemon WHERE is_default=1 AND species=(SELECT species FROM pokemon WHERE form_key=?)))"
    return db.execute(q, (move_key, form_key, form_key)).fetchone() is not None


def _attach_sp(text, names, mentions, key="sp"):
    """SP 표기(또는 성격)를 가장 가까운 포켓몬 언급에 붙인다. names: {"my": "한카", "opp": ...}(원문 그대로). 반환 {"my": 값, "opp": 값}, 못 붙인 수."""
    spans = {side: [(m.start(), m.end()) for m in re.finditer(re.escape(n), text)] for side, n in names.items() if n}
    out, lost = {}, 0
    for x in mentions:
        best = None
        for side, ss in spans.items():
            for s, e in ss:
                d = s - x["end"] if s >= x["end"] else x["start"] - e if x["start"] >= e else 0
                if best is None or d < best[0]:
                    best = (d, side)
        if best is None or best[1] in out:
            lost += 1  # 이름을 못 찾았거나 한 포켓몬에 두 번 붙는 경우: 확인 화면에서 직접 고친다
            continue
        out[best[1]] = x[key]
    return out, lost


def extract(db, text, llm=default_llm):
    """반환 {"type", "fields"(review() 요청 형식, 찾은 것만), "missing"[칸 이름], "ask"[확인 화면에서 꼭 물을 칸], "notes"[문장], "reason"?}."""
    text = (text or "").strip()
    if not text:
        return {"type": "fail", "reason": "empty_input", "fields": {}, "missing": [], "ask": [], "notes": []}
    for attempt in range(2):  # 같은 문장에도 GMS 응답이 흔들린다(친구 사례: 3번 중 1번 fail). 실패면 한 번만 다시 묻는다
        try:
            raw = llm(text)
        except Exception:  # 키 없음·만료·네트워크: 계산은 직접 입력으로 계속된다(D16)
            return {"type": "fail", "reason": "llm_unavailable", "fields": {}, "missing": [], "ask": [], "notes": [], "llm_calls": attempt + 1}
        got, why = _parse(raw)
        if got is not None and got.get("type") in ("review", "rule"):
            break
    calls = attempt + 1
    if got is None:
        return {"type": "fail", "reason": why, "fields": {}, "missing": [], "ask": [], "notes": [], "llm_calls": calls}
    typ = got.get("type") if got.get("type") in ("review", "rule", "fail") else "fail"
    if typ != "review":
        return {"type": typ, "reason": None if typ == "rule" else "refusal", "fields": {}, "missing": [], "ask": [], "notes": [], "llm_calls": calls}

    fields, notes, ask = {}, [], []  # ask: 확인 화면에서 꼭 다시 물을 칸
    for side, key in (("my", "my_form_key"), ("opp", "opp_form_key")):
        k = resolve(db, "pokemon", got.get(side))
        if k:
            fields[key] = k
        elif got.get(side):
            notes.append(f"'{got[side]}'{josa(got[side], '을', '를')} 포켓몬 이름으로 찾지 못했어요")
    mk = resolve(db, "move", got.get("move"))
    if not mk:
        found = move_in_text(db, text)
        if found:
            mk = found[1]
            ask.append("move_key")
            notes.append(f"문장에서 기술 '{found[0]}'{josa(found[0], '을', '를')} 찾았어요. 맞는지 확인해 주세요")
        elif got.get("move"):
            notes.append(f"'{got['move']}'{josa(got['move'], '을', '를')} 기술 이름으로 찾지 못했어요")
    if mk:
        fields["move_key"] = mk
    result = got.get("result") if got.get("result") in KINDS else None
    if result == "ko" and got.get("hp_band") in rv.HP_BANDS:  # "7할 남음"인데 ko: 남은 HP가 있으면 버팀으로 본다
        result = "survived"
        ask.append("actual")
        notes.append("남은 HP가 있다고 해서 버틴 것으로 봤어요. 맞는지 확인해 주세요")
    if result:
        fields["actual"] = {"kind": result}
        if result == "survived" and got.get("hp_band") in rv.HP_BANDS:
            fields["actual"]["hp_band"] = got["hp_band"]
    if got.get("actor") in ("me", "opp"):
        fields["actor"] = got["actor"]
    flags = [f for f in (got.get("flags") or []) if f in rv.FLAG_NAMES]
    if flags:
        fields["flags"] = flags

    # 공격 측 검증: 그 기술을 공격 측이 배우지 않고 반대쪽이 배우면 바꾼다. 미러면 learnset으로 가릴 수 없어 확인에서 묻는다
    me, opp = fields.get("my_form_key"), fields.get("opp_form_key")
    if me and opp and mk and "actor" not in fields and result in SPEED and me != opp:
        side = "me" if learns(db, me, mk) else "opp" if learns(db, opp, mk) else None  # 스피드 결과: 기술 쓴 쪽을 learnset으로 채운다
        if side:
            fields["actor"] = side
            ask.append("actor")
            notes.append("기술을 배우는 쪽을 기술을 쓴 포켓몬으로 정했어요. 맞는지 확인해 주세요")
    if me and opp and me == opp:  # 확인 칩에 이유가 보이도록 notes에도 쓴다(디자인 A1)
        ask.append("actor")
        notes.append("같은 포켓몬끼리라 누가 공격했는지 확인해 주세요")
    elif me and opp and mk and fields.get("actor") and (not result or result not in SPEED):
        atk, dfn = (me, opp) if fields["actor"] == "me" else (opp, me)
        if not learns(db, atk, mk) and learns(db, dfn, mk):
            fields["actor"] = "opp" if fields["actor"] == "me" else "me"
            ask.append("actor")
            notes.append("기술을 배우는 쪽을 공격한 포켓몬으로 정했어요. 맞는지 확인해 주세요")

    # SP는 코드만 읽는다(D22). 가장 가까운 이름에 붙인다
    sp, lost = _attach_sp(text, {"my": got.get("my"), "opp": got.get("opp")}, rv.sp_mentions(text, db))
    if "my" in sp:
        fields["my_build"] = {"sp": sp["my"]}
    if "opp" in sp:
        fields["opp_sp"] = sp["opp"]
    if lost:
        notes.append("SP 표기 일부를 어느 포켓몬 것인지 정하지 못했어요")
    # 성격도 코드가 읽는다(LLM 프롬프트는 숫자·성격을 읽지 않는다). 내 포켓몬 것만 빌드에 넣고, 상대 성격은 계산표 후보를 좁히지 않는다
    nat = [{"start": m.start(), "end": m.end(), "nature": key} for name, key in natures_ko(db).items() for m in re.finditer(re.escape(name), text)]
    nature, _ = _attach_sp(text, {"my": got.get("my"), "opp": got.get("opp")}, nat, "nature")
    if "my" in nature:
        fields.setdefault("my_build", {})["nature"] = nature["my"]

    missing = [k for k in ("my_form_key", "opp_form_key", "actor", "move_key", "actual") if k not in fields]
    return {"type": "review", "fields": fields, "missing": missing, "ask": ask, "notes": notes, "llm_calls": calls}


class Extractions:
    """추출 결과를 extraction_id로 잠시 보관한다. 확인 화면에서 고쳤는지 비교하는 데만 쓴다(R8). 서버 재시작이면 사라진다."""

    def __init__(self, ttl=config.EXTRACTION_TTL, limit=500):
        self.ttl, self.limit, self._d, self._lock = ttl, limit, {}, threading.Lock()

    def put(self, text, result):
        eid = uuid.uuid4().hex
        with self._lock:
            now = time.time()
            self._d = {k: v for k, v in self._d.items() if now - v[0] < self.ttl}
            if len(self._d) >= self.limit:
                self._d.pop(min(self._d, key=lambda k: self._d[k][0]))
            self._d[eid] = (now, text, result)
        return eid

    def get(self, eid):
        with self._lock:
            v = self._d.get(eid)
        return None if v is None or time.time() - v[0] >= self.ttl else {"text": v[1], "result": v[2]}


def corrected(extracted_fields, confirmed):
    """확인 화면에서 바뀐 칸 이름(C8-1 "추출 수정 여부")."""
    keys = set(extracted_fields) | {k for k in confirmed if k in ("my_form_key", "opp_form_key", "actor", "move_key", "actual", "flags", "my_build", "opp_sp")}
    return sorted(k for k in keys if (extracted_fields.get(k) or None) != (confirmed.get(k) or None))  # 빈 목록 = 없음
