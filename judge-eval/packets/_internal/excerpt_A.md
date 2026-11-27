### 계산 핵심

`prep/calculator.py` · `check_sp` (9줄)
```python
def check_sp(sp):
    """SP 입력 검증: 스탯당 0~32, 합계 66 이하."""
    unknown = set(sp) - set(STATS)
    if unknown:
        raise ValueError(f"알 수 없는 스탯: {sorted(unknown)}")
    if any(not isinstance(v, int) or not 0 <= v <= SP_PER_STAT for v in sp.values()):
        raise ValueError(f"SP는 스탯당 0~{SP_PER_STAT} 정수여야 합니다: {sp}")
    if sum(sp.values()) > SP_TOTAL:
        raise ValueError(f"SP 합계는 {SP_TOTAL} 이하여야 합니다: {sum(sp.values())}")
```

`prep/calculator.py` · `hp_stat` (3줄)
```python
def hp_stat(base, sp):
    """HP = 종족값 + SP + 75"""
    return base + sp + 75
```

`prep/calculator.py` · `other_stat` (3줄)
```python
def other_stat(base, sp, nature_pct=100):
    """그 외 = floor((종족값 + SP + 20) × 보정). 보정은 정수 %(110/100/90)로 받아 부동소수 오차를 피한다."""
    return (base + sp + 20) * nature_pct // 100
```

`prep/calculator.py` · `poke_round` (5줄)
```python
def poke_round(x):
    """가장 가까운 정수로 반올림, 0.5는 내림 ('rounding down at 0.5')."""
    x = Fraction(x)
    n = x.numerator // x.denominator
    return n + 1 if x - n > Fraction(1, 2) else n
```

`prep/calculator.py` · `type_effectiveness` (6줄)
```python
def type_effectiveness(db, move_type, def_types):
    m = Fraction(1)
    for t in def_types:
        if t:
            m *= Fraction(_one(db, "SELECT mult FROM type_chart WHERE atk_type=? AND def_type=?", (move_type, t))[0])
    return m
```

`prep/calculator.py` · `stage_stat` (3줄)
```python
def stage_stat(stat, stage):
    """랭크 보정: +n은 ×(2+n)/2, −n은 ×2/(2+n), 내림 (Stat modifier 문서)."""
    return stat * (2 + stage) // 2 if stage >= 0 else stat * 2 // (2 - stage)
```

`prep/calculator.py` · `speed` (5줄)
```python
def speed(db, build):
    """스피드 실수치. 구애스카프는 ×1.5 (PokeAPI 'Increases Speed by 50%')."""
    b = _build(build)
    s = actual_stats(db, b["form_key"], b["sp"], b["nature"])["spe"]
    return poke_round(s * Fraction(3, 2)) if b["item"] == "choice-scarf" else s
```

`prep/calculator.py` · `damage_rolls` (62줄)
```python
def damage_rolls(db, attacker, defender, move_key):
    """16개 난수별 데미지(싱글, 급소·날씨·화상 없음). attacker/defender는 {form_key, sp, nature, item, ability}.
    공격 측 atk_stage(공격·특공 랭크, 위협이면 −1), 방어 측 full_hp(멀티스케일용, 기본 True).
    특성은 SUPPORTED_ABILITIES만 계산한다. 반환: {'rolls': [16개], 'hp': 방어 측 최대 HP, 'effectiveness': 상성 배율 문자열}."""
    a, d = _build(attacker), _build(defender)
    mv = _one(db, "SELECT type, category, power, effect_en FROM move WHERE move_key=?", (move_key,))
    if mv is None:
        raise ValueError(f"알 수 없는 기술: {move_key}")
    mtype, category, power, effect = mv
    if category not in ("physical", "special") or not power:
        raise ValueError(f"위력이 있는 공격 기술이 아닙니다: {move_key} ({category}, power={power})")
    if move_key in SPECIAL_FORMULA_MOVES or MULTI_HIT.search(effect or ""):
        raise ValueError(f"일반 데미지 공식으로 계산하지 않는 기술입니다: {move_key}")
    stat, dstat = ("atk", "def") if category == "physical" else ("spa", "spd")
    a_types = _one(db, "SELECT type1, type2 FROM pokemon WHERE form_key=?", (a["form_key"],))
    d_types = _one(db, "SELECT type1, type2 FROM pokemon WHERE form_key=?", (d["form_key"],))
    if a_types is None or d_types is None:
        raise ValueError(f"알 수 없는 폼: {a['form_key'] if a_types is None else d['form_key']}")
    eff = type_effectiveness(db, mtype, d_types)
    d_stats = actual_stats(db, d["form_key"], d["sp"], d["nature"])
    if eff == 0 or (mtype == "ground" and (d["item"] == "air-balloon" or d["ability"] == "levitate")):
        return {"rolls": [0] * len(ROLLS), "hp": d_stats["hp"], "effectiveness": "0"}  # 상성 무효, 풍선·부유+땅 기술

    # 공격 측: 랭크 → 특성·도구 순(Showdown과 같은 순서). 도구 단계는 기존 상수 표로 구분하고 값은 item_multiplier(PokeAPI 문구)를 쓴다
    A, P, other = stage_stat(actual_stats(db, a["form_key"], a["sp"], a["nature"])[stat], a["atk_stage"]), power, Fraction(1)
    if a["ability"] in ATTACK_STAT_ABILITIES and stat == "atk":
        A *= 2
    if a["ability"] == "technician" and power <= 60:
        P = poke_round(P * Fraction(3, 2))  # PokeAPI "60 base power or less to 1.5×"
    if a["ability"] == "iron-fist" and move_key in PUNCH_MOVES:
        P = poke_round(P * Fraction(6, 5))  # PokeAPI "punch-based moves 1.2×" (위력 단계)
    if d["ability"] == "multiscale" and d["full_hp"]:
        other *= Fraction(1, 2)  # PokeAPI "Halves damage taken from full HP"
    stab = (2 if a["ability"] == "adaptability" else STAB) if mtype in a_types else 1  # PokeAPI "1.5× to 2×"
    if a["item"] and item_kind(db, a["item"], "attack") == "affects" and a["item"] != "choice-scarf":
        mult, _ = item_multiplier(db, a["item"], a["form_key"], mtype, category, stat, super_effective=eff > 1)
        if a["item"] in STAT_ITEMS or a["item"] in SPECIES_ITEMS:
            A = poke_round(A * mult)
        elif a["item"] in FINAL_ITEMS:
            other *= mult
        else:  # 힘의머리띠·박식안경·타입 강화 도구: 위력 단계
            P = poke_round(P * mult)
    # 방어 측 도구
    D = d_stats[dstat]
    if d["item"] in DEF_STAT_ITEMS and DEF_STAT_ITEMS[d["item"]][0] == dstat:
        D = poke_round(D * DEF_STAT_ITEMS[d["item"]][1])
    if d["item"] and eff > 1:
        row = _one(db, "SELECT effect_en FROM item WHERE key=?", (d["item"],))
        m = RESIST_BERRY.search((row[0] if row else "") or "")
        if m and m.group(1).lower() == mtype:
            other *= Fraction(1, 2)

    base = 22 * P * A // D // 50 + 2
    rolls = []
    for r in ROLLS:
        x = base * r // 100                      # 난수: 곱한 뒤 내림
        if stab != 1:
            x = poke_round(x * stab)            # 자속(적응력이면 2)
        x = int(x * eff)                         # 상성: 곱한 뒤 내림
        x = poke_round(x * other) if other != 1 else x  # 기타 보정(생명의구슬·달인의띠·반감 열매). 여러 개면 곱을 한 번에 적용(근사)
        rolls.append(max(x, 1))
    return {"rolls": rolls, "hp": d_stats["hp"], "effectiveness": str(eff)}
```

### 요청 처리 흐름

`server/app.py` · `Actual` (3줄)
```python
class Actual(BaseModel):
    kind: Literal["ko", "survived", "outsped", "slower"]
    hp_band: Literal["75+", "50-75", "25-50", "<25"] | None = None
```

`server/app.py` · `Build` (5줄)
```python
class Build(BaseModel):
    sp: dict[str, int] | None = None
    nature: str | None = None
    item: str | None = None
    ability: str | None = None
```

`server/app.py` · `ReviewIn` (12줄)
```python
class ReviewIn(BaseModel):
    session_id: str | None = Field(default=None, max_length=64)
    extraction_id: str | None = Field(default=None, max_length=64)
    my_form_key: str = Field(max_length=64)
    opp_form_key: str = Field(max_length=64)
    actor: Literal["me", "opp"]
    move_key: str = Field(max_length=64)
    actual: Actual
    flags: list[str] = Field(default_factory=list, max_length=10)
    my_build: Build | None = None
    opp_sp: dict[str, int] | None = None
    pre_hit_hp: float | None = Field(default=None, gt=0, le=1)
```

`server/app.py` · `_compute` (4줄)
```python
def _compute(db, req):
    out = rv.review(db, req)
    text, degraded, calls = summary.summarize(db, out, SUMMARY_LLM)
    return out, calls, summary.answer(db, out, req, text, degraded)
```

`server/app.py` · `review_route` (32줄)
```python
@app.post("/api/feature/review")
async def review_route(body: ReviewIn, label: str = Depends(access.require_label)):
    req = body.model_dump(include=set(FIELDS), exclude_none=True)
    if body.my_build:
        req["my_build"] = body.my_build.model_dump(exclude_none=True)
    req["actual"] = body.actual.model_dump(exclude_none=True)
    quota.take(label, "review", llm_calls=1 if config.REVIEW_SUMMARY_LLM else 0)
    saved = extractions.get(body.extraction_id) if body.extraction_id else None
    review_id = uuid.uuid4().hex

    async def stream():
        t0 = time.perf_counter()
        yield _sse("status", {"state": "computing"})
        try:
            async with slots:
                out, calls, answer = await run_in_threadpool(with_db, _compute, req)
        except ValueError as e:  # 알 수 없는 폼·기술, SP 초과 등 입력 오류
            yield _sse("error", {"code": "bad_input", "message": str(e)})
            return
        except Exception:  # 추적 정보는 내보내지 않는다
            yield _sse("error", {"code": "internal", "message": "계산 중 문제가 생겼어요. 잠시 뒤 다시 시도해 주세요"})
            return
        answer["review_id"] = review_id
        yield _sse("answer", answer)
        logs.append({"kind": "review", "label": label, "review_id": review_id, "session_id": body.session_id,
                     "text": saved["text"] if saved else None, "request": req,
                     "corrected": ex.corrected(saved["result"].get("fields", {}), req) if saved else None,
                     "causes": {b: [x["label"] for x in r["causes"]] for b, r in out["bases"].items()},
                     "unsupported": out["unsupported"], "reference_only": out["reference_only"], "differs": out["differs"],
                     "degraded": answer["degraded"], "llm_calls": calls, "latency_ms": round((time.perf_counter() - t0) * 1000)})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})
```

`prep/review.py` · `review` (51줄)
```python
def review(db, req):
    """[service]. 두 기준(pokedb·Smogon)으로 각각 계산하고 차이를 판정한다. LLM 없이 동작한다."""
    for key in ("my_form_key", "opp_form_key", "actor", "move_key", "actual"):
        if key not in req:
            raise ValueError(f"필수 항목 없음: {key}")
    if req["actor"] not in ("me", "opp") or req["actual"].get("kind") not in ("ko", "survived", "outsped", "slower"):
        raise ValueError("actor는 me/opp, actual.kind는 ko/survived/outsped/slower")
    mv = db.execute("SELECT category, priority FROM move WHERE move_key=?", (req["move_key"],)).fetchone()
    if mv is None:
        raise ValueError(f"알 수 없는 기술: {req['move_key']}")
    category, priority = mv
    unsupported, assumptions = [], []
    flags = [f for f in req.get("flags", []) if f in FLAG_NAMES]
    if flags:
        unsupported.append("계산하지 않은 특수 상황: " + ", ".join(FLAG_NAMES[f] for f in flags if f != "trick_room") +
                           (" (트릭룸은 스피드 비교에 반영)" if "trick_room" in flags else ""))
    if req["actual"]["kind"] in ("outsped", "slower"):
        assumptions.append("상대가 우선도 0 기술을 썼다는 가정(상대 기술 입력은 v1 범위 밖)")
        if priority:
            unsupported.append("입력한 기술의 우선도가 0이 아니라 스피드 비교를 하지 않음")
            return {"bases": {}, "differs": False, "unsupported": unsupported, "assumptions": assumptions, "reference_only": True}
    opp_abilities = set(_form_abilities(db, req["opp_form_key"]))
    skipped = sorted(opp_abilities & UNCOMPUTED_ABILITIES - {"intimidate"})
    if skipped:
        ko = lambda k: (db.execute("SELECT name_ko FROM ability WHERE key=?", (k,)).fetchone() or [k])[0]
        unsupported.append("계산하지 않은 상대 특성: " + ", ".join(ko(k) for k in skipped))
    if req["actor"] == "me" and req["actual"]["kind"] == "survived" and "intimidate" in opp_abilities:
        assumptions.append("이 포켓몬도 위협 특성일 수 있음")
    bases, my_builds = {}, {}
    for basis in ("pokedb", "smogon"):
        me, note = my_default_build(db, basis, req, category)
        my_builds[basis] = me
        try:
            bases[basis] = compute_basis(db, basis, req, category, me)
        except ValueError as e:  # 특수 계산 기술 등: 일반 공식 대상이 아님(, v1 미지원)
            move_ko = _ko_name(db, "move", req["move_key"])
            unsupported.append(f"확인 불가: {str(e).replace(req['move_key'], move_ko)}")  # 기술 키 대신 한글 이름
            return {"bases": {}, "differs": False, "unsupported": unsupported, "assumptions": assumptions, "reference_only": True}
        if note:
            bases[basis]["notes"].append(note)
            if bases[basis]["zero_match"]:
                bases[basis]["notes"].append("이 결과는 위 내 빌드 가정과 맞지 않을 수 있어요. 실제 내 빌드를 넣으면 다시 계산합니다")
    diff, why = differs(bases["pokedb"], bases["smogon"])
    calc = calc_table(db, req, category, my_builds["pokedb"])  # 계산을 먼저 보여 준다. 내 빌드는 입력값, 없으면 pokedb 기준 가정
    fields = ("sp", "nature", "item") if req["actual"]["kind"] in ("outsped", "slower") else ("sp", "nature", "item", "ability")
    if diff and any(my_builds["pokedb"][f] != my_builds["smogon"][f] for f in fields):
        why += " (두 기준의 내 빌드 가정이 달라 생긴 차이일 수 있음)"
    if req.get("pre_hit_hp") is None and req["actual"]["kind"] in ("ko", "survived"):
        assumptions.append("맞기 전 HP는 가득 찬 상태로 가정")
    return {"bases": bases, "calc": calc, "kind": req["actual"]["kind"], "actor": req["actor"], "differs": diff, "diff_reason": why, "unsupported": unsupported, "assumptions": assumptions,
            "reference_only": bool(flags)}
```

### 입력 검증·오류 처리

`server/access.py` · `token_middleware` (14줄)
```python
async def token_middleware(request: Request, call_next):
    t = request.query_params.get("t")
    if t is None:
        resp = await call_next(request)
    elif label_of(t):
        resp = RedirectResponse(str(request.url.remove_query_params("t")), status_code=303)
        resp.set_cookie(COOKIE, t, httponly=True, samesite="strict", secure=request.url.scheme == "https", max_age=30 * 86400)
    elif request.url.path.startswith("/api/"):
        resp = JSONResponse(FORBIDDEN, status_code=403)
    else:  # 틀린 초대 링크로 화면을 열면 JSON 대신 t를 뗀 화면으로 보내고, 화면이 API 403을 받아 초대 안내를 띄운다(디자인 E5)
        resp = RedirectResponse(str(request.url.remove_query_params("t")), status_code=303)
        resp.delete_cookie(COOKIE)
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp
```

`server/access.py` · `require_label` (6줄)
```python
def require_label(request: Request):
    """API 의존성: 쿠키의 토큰 → 이름표. 없거나 모르는 토큰이면 403."""
    label = label_of(request.cookies.get(COOKIE))
    if not label:
        raise HTTPException(403, FORBIDDEN)
    return label
```

`server/access.py` · `Quota` (40줄)
```python
class Quota:
    def __init__(self):
        self._lock = threading.Lock()
        self.day, self.used, self.llm = None, Counter(), 0

    def _roll(self):
        today = logs.now().date().isoformat()
        if today != self.day:
            self.day, self.used, self.llm = today, Counter(), 0

    def seed(self, records):
        """오늘 기록으로 다시 센다. 기록 줄: kind(extract/review), label, llm_calls."""
        with self._lock:
            self._roll()
            for r in records:
                if str(r.get("ts", ""))[:10] == self.day and r.get("kind") in LIMITS:
                    self.used[r.get("label"), r["kind"]] += 1
                    self.llm += int(r.get("llm_calls", 0))

    def take(self, label, kind, llm_calls=1):
        """한 번 쓴다. 한도를 넘으면 429(쓰지 않음)."""
        with self._lock:
            self._roll()
            if self.used[label, kind] >= LIMITS[kind]():
                raise HTTPException(429, {"code": "token_limit", "message": "오늘 이용 횟수를 다 썼어요. 내일 다시 이용해 주세요"})
            if self.llm + llm_calls > config.DAILY_LLM_CALLS:
                raise HTTPException(429, {"code": "server_limit", "message": "오늘 서버 사용량이 다 찼어요. 내일 다시 이용해 주세요"})
            self.used[label, kind] += 1
            self.llm += llm_calls

    def add_llm(self, n):
        """이미 쓴 호출을 더한다(막지 않음). 다음 take부터 상한에 걸린다."""
        with self._lock:
            self._roll()
            self.llm += max(0, n)

    def remaining(self, label):
        with self._lock:
            self._roll()
            return {k: max(0, f() - self.used[label, k]) for k, f in LIMITS.items()}
```

`server/extract.py` · `_parse` (12줄)
```python
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
```

`server/extract.py` · `resolve` (24줄)
```python
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
```
