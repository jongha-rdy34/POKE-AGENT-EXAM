### 계산 핵심

`app/domain/stats.py` · `_nature_mult` (3줄)
```python
def _nature_mult(stat: str, nature: str | None) -> int:
    plus, minus, _ = NATURES.get(nature or "", (None, None, None))
    return 110 if stat == plus else 90 if stat == minus else 100
```

`app/domain/stats.py` · `calc_stat` (12줄)
```python
def calc_stat(stat: str, base: int, points: int, nature: str | None, system: str) -> int:
    """system: 'sp'(챔피언스) 또는 'ev'(본가)."""
    if system == "sp":
        if stat == "hp":
            return base + points + 75
        raw = base + points + 20
    else:
        core = (2 * base + 31 + points // 4) * LEVEL // 100
        if stat == "hp":
            return core + LEVEL + 10
        raw = core + 5
    return raw * _nature_mult(stat, nature) // 100
```

`app/domain/damage.py` · `_modify` (4줄)
```python
def _modify(value: int, mult: float) -> int:
    """Showdown battle.modify: 4096 기준 고정소수점, 0.5 내림 반올림."""
    modifier = int(mult * 4096)
    return (value * modifier + 2048 - 1) // 4096
```

`app/domain/damage.py` · `_chain` (6줄)
```python
def _chain(mods: list[float]) -> int:
    """Showdown chainModify: 여러 배율을 4096 고정소수점으로 곱한다."""
    m = 4096
    for x in mods:
        m = (m * int(round(x * 4096)) + 2048) >> 12
    return m
```

`app/domain/damage.py` · `_apply` (2줄)
```python
def _apply(value: int, chain: int) -> int:
    return (value * chain + 2048 - 1) // 4096
```

`app/domain/damage.py` · `damage_rolls` (26줄)
```python
def damage_rolls(power: int, attack: int, defense: int, stab: bool, effectiveness: float,
                 spread: bool = False, stab_mult: float = 1.5, final_mods: list[float] | None = None) -> list[int]:
    """한 번 맞혔을 때의 16가지 데미지. power/attack/defense는 특성 보정을 마친 값."""
    if effectiveness == 0 or power <= 0:
        return [0] * 16
    final = _chain(final_mods) if final_mods else 4096
    base = (((2 * LEVEL // 5 + 2) * power * attack) // defense) // 50
    base += 2
    if spread:
        base = _modify(base, 0.75)
    out = []
    for r in ROLLS:
        d = base * (100 - r) // 100
        if stab:
            d = _modify(d, stab_mult)
        e = effectiveness
        while e >= 2:
            d *= 2
            e /= 2
        while 0 < e <= 0.5:
            d //= 2
            e *= 2
        if final != 4096:
            d = _apply(d, final)
        out.append(max(d, 1))
    return out
```

`app/domain/damage.py` · `calc_move` (46줄)
```python
def calc_move(move: dict, attacker: dict, defender: dict, effectiveness: float, doubles: bool = False,
              type_chart: dict | None = None) -> dict | None:
    """move: Showdown 기술 정보, attacker/defender: {stats, types, ability?}. 위력이 가변(0)이면 None.
    type_chart: 방어측 상성표(특성 무효 포함). -스킨으로 타입이 바뀌면 이 표로 상성을 다시 본다."""
    power = move.get("base_power") or 0
    if power <= 0 or move.get("category") == "Status":
        return None
    physical = move["category"] == "Physical"
    atk_ab, def_ab = attacker.get("ability"), defender.get("ability")
    move_type = AB.effective_type(atk_ab, move)
    if move_type != move["type"] and type_chart:
        effectiveness = type_chart.get(move_type, 1)
    atk_stat = move.get("override_offensive_stat") or ("atk" if physical else "spa")
    def_stat = move.get("override_defensive_stat") or ("def" if physical else "spd")
    src = defender if move.get("override_offensive_pokemon") == "target" else attacker
    attack, defense = src["stats"][atk_stat], defender["stats"][def_stat]
    bp_mods, atk_mods, stab_mult, notes = AB.attacker_mods(atk_ab, move, move_type, physical)
    df_mods, final_mods, dnotes = AB.defender_mods(def_ab, move, move_type, def_stat == "def", effectiveness)
    notes += dnotes
    if bp_mods:
        power = max(1, _apply(power, _chain(bp_mods)))
    if atk_mods and src is attacker:
        attack = _apply(attack, _chain(atk_mods))
    if df_mods:
        defense = _apply(defense, _chain(df_mods))
    stab = move_type in attacker["types"]
    spread = doubles and move.get("target") in SPREAD_TARGETS
    kw = {"stab_mult": stab_mult, "final_mods": final_mods}

    hits = move.get("multihit")
    if move.get("id") in ("tripleaxel", "triplekick"):
        step = power
        per_hit = [damage_rolls(step * (i + 1), attack, defense, stab, effectiveness, spread, **kw) for i in range(3)]
        dist, hits_label = move_distribution(per_hit), "3회"
    elif isinstance(hits, list):
        rolls = damage_rolls(power, attack, defense, stab, effectiveness, spread, **kw)
        dist, hits_label = move_distribution([rolls], VARIABLE_HITS), f"{hits[0]}~{hits[1]}회"
    elif isinstance(hits, int) and hits > 1:
        rolls = damage_rolls(power, attack, defense, stab, effectiveness, spread, **kw)
        dist, hits_label = move_distribution([rolls] * hits), f"{hits}회"
    else:
        dist, hits_label = _dist(damage_rolls(power, attack, defense, stab, effectiveness, spread, **kw)), None
    out = ko_summary(dist, defender["stats"]["hp"])
    out.update({"hits": hits_label, "stab": stab, "spread": spread, "move_type": move_type,
                "attack_stat": atk_stat, "defense_stat": def_stat, "ability_notes": notes})
    return out
```

### 요청 처리 흐름

`app/api/routes.py` · `chat` (5줄)
```python
@chat_router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> dict:
    """메인 Agent 실행. 답변과 함께 실행 단계·Tool 호출 이력(events)을 돌려준다."""
    return await run_in_threadpool(run_agent, req.message, req.session_id, req.name_choices, req.game, req.battle,
                                  req.my_team, req.opp_team, req.mega_choice)
```

`app/agent/graph.py` · `judge_node` (39줄)
```python
@node("judge")
def judge_node(state: AgentState, em: Emitter) -> dict:
    ctx, intent, round_ = state["ctx"], state["intent"], state["round"]
    if ctx["unresolved"]:
        em.emit("decision", "judge", decision="ask", unresolved=[u["input"] for u in ctx["unresolved"]])
        return {"status": "ask", "_summary": "이름 확인 필요"}
    if ctx.get("mega_ask"):
        return {"status": "ask", "missing": ["mega"], "_summary": "메가진화 선택 필요"}

    fatal = [f for f in ctx["failures"] if f["code"] in FATAL_CODES]
    if intent == "plan_selection":
        result = J.judge_selection(ctx, state["conditions"], round_)
    elif intent == "matchup_advice":
        result = J.judge_matchup(ctx, state["conditions"])
    else:
        result = J.judge_lookup(ctx)

    if result.get("satisfied"):
        return {"result": result, "status": "ok", "_summary": "조건 충족"}
    if intent == "plan_selection" and not result.get("selected") and not fatal:
        # 규칙상 고를 수 있는 조합 자체가 없음 (메가 1마리 제한, 제외 조건 등) → 재계획해도 같다
        em.emit("decision", "judge", decision="infeasible", reason=result.get("reason"))
        return {"result": result, "status": "infeasible", "_summary": "선출 조합 없음"}
    if fatal and not ctx["charts"]:
        # 외부 서버 오류는 다시 해도 결과가 같다 → 재계획하지 않고 안내
        em.emit("decision", "judge", decision="no_replan", reason="외부 데이터 오류", codes=[f["code"] for f in fatal])
        return {"result": result, "status": "error",
                "error": {"code": fatal[0]["code"], "message": fatal[0]["message"]}, "_summary": "외부 오류"}
    if intent == "plan_selection" and round_ < config.MAX_REPLAN and result.get("selected"):
        nxt = round_ + 1
        rp = {"round": nxt, "reason": f"잡지 못한 상대: {', '.join(result.get('uncovered', []))}",
              "criteria": REPLAN_CRITERIA[nxt]}
        em.emit("replan", "judge", **rp)
        return {"result": result, "status": "replan", "round": nxt, "replans": state["replans"] + [rp],
                "_summary": f"재계획 {nxt}회차"}
    status = "limit" if intent == "plan_selection" and round_ >= config.MAX_REPLAN else "ok"
    if status == "limit":
        em.emit("decision", "judge", decision="stop", reason=f"재계획 상한 {config.MAX_REPLAN}회 도달")
    return {"result": result, "status": status, "_summary": status}
```

`app/agent/graph.py` · `run_agent` (60줄)
```python
def run_agent(message: str, session_id: str | None = None, name_choices: dict[str, str] | None = None,
              game: str | None = None, battle: str | None = None,
              my_team: list[str] | None = None, opp_team: list[str] | None = None,
              mega_choice: dict | None = None) -> dict:
    session_id = session_id or "s-" + uuid.uuid4().hex[:10]
    em = Emitter(session_id)
    mem = memory.get(session_id)
    prev = mem["conditions"]
    ruleset = rulesets.resolve(game or prev.get("game"), battle or prev.get("battle"))
    em.emit("run_start", None, message=message, game=ruleset["game"], battle=ruleset["battle"],
            format=ruleset["format"])
    if prev.get("game") and (prev.get("game"), prev.get("battle")) != (ruleset["game"], ruleset["battle"]):
        em.emit("decision", None, decision="ruleset_changed", to=f"{ruleset['game_label']} {ruleset['battle_label']}")
    if name_choices:
        memory.add_aliases(session_id, name_choices)
        em.emit("decision", None, decision="name_choice", choices=name_choices)
    t0 = time.perf_counter()
    try:
        final = GRAPH.invoke({"session_id": session_id, "message": message, "memory": memory.get(session_id),
                              "ruleset": ruleset, "teams": {"my": my_team or [], "opp": opp_team or []},
                              "mega_choice": mega_choice or {}},
                             config={"configurable": {"emitter": em}, "recursion_limit": 40})
    except Exception as e:  # noqa: BLE001 - 어떤 경우에도 서비스는 응답한다
        em.emit("error", None, code=ErrorCode.INTERNAL_ERROR, message=type(e).__name__)
        final = {"status": "error", "answer": "처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
                 "error": {"code": ErrorCode.INTERNAL_ERROR, "message": "내부 오류"}}
    total = round((time.perf_counter() - t0) * 1000)
    ctx = final.get("ctx") or {}
    cards = _pokemon_cards(ctx)
    em.emit("run_end", None, status=final.get("status"), total_ms=total, tool_calls=ctx.get("calls", 0),
            replans=len(final.get("replans") or []))
    return {
        "session_id": session_id,
        "run_id": em.run_id,
        "status": final.get("status"),
        "intent": final.get("intent"),
        "intent_reason": final.get("intent_reason"),
        "answer": final.get("answer", ""),
        "plan_draft": final.get("plan_draft"),
        "saved": final.get("saved"),
        "replans": final.get("replans") or [],
        "result": final.get("result"),
        "error": final.get("error"),
        "conditions": final.get("conditions"),
        "opp_profile": (final.get("result") or {}).get("opp_profile"),
        "pokemon_cards": cards,
        "move_plan": (final.get("result") or {}).get("move_plan"),
        "mega": ctx.get("mega"),  # 내 메가스톤 후보·보유, 상대 메가 예상 (화면 토글용)
        "mega_evolve": (final.get("result") or {}).get("mega_evolve"),
        "mega_alternatives": (final.get("result") or {}).get("mega_alternatives") or [],
        "rule_notes": (final.get("result") or {}).get("rule_notes") or [],
        "ruleset": ruleset,
        "defense_advice": (final.get("result") or {}).get("defense_advice"),
        "clarify": [  # 화면에서 고를 수 있는 이름 후보 (status=ask일 때)
            {"input": u["input"], "reason": u.get("reason"), "candidates": u.get("candidates") or []}
            for u in ctx.get("unresolved", [])
        ] if final.get("status") == "ask" else [],
        "events": em.events,
        "total_ms": total,
    }
```

### 입력 검증·오류 처리

`app/tools/common.py` · `ErrorCode` (10줄)
```python
class ErrorCode:
    BAD_ARGUMENT = "BAD_ARGUMENT"      # 입력이 규격과 다름 (빈 값, 형식 틀림)
    INVALID_KEY = "INVALID_KEY"        # 키가 없거나 틀림 (LLM 등 키가 필요한 API)
    NOT_FOUND = "NOT_FOUND"            # 찾는 대상이 없음 (없는 포켓몬/기술/포맷)
    NO_DATA = "NO_DATA"                # 조회는 됐지만 판단에 필요한 값이 비어 있음
    AMBIGUOUS = "AMBIGUOUS"            # 이름이 여러 대상에 걸림 → 사용자에게 되물어야 함
    UPSTREAM_ERROR = "UPSTREAM_ERROR"  # 외부 API가 정상 응답하지 않음 (5xx, 연결 실패)
    TIMEOUT = "TIMEOUT"                # 외부 API 응답 시간 초과
    UNKNOWN_TOOL = "UNKNOWN_TOOL"      # 등록되지 않은 Tool 이름
    INTERNAL_ERROR = "INTERNAL_ERROR"  # 예상하지 못한 내부 오류
```

`app/tools/common.py` · `ok` (2줄)
```python
def ok(data: Any) -> dict:
    return {"ok": True, "data": data}
```

`app/tools/common.py` · `fail` (2줄)
```python
def fail(code: str, message: str) -> dict:
    return {"ok": False, "error": {"code": code, "message": message}}
```

`app/tools/common.py` · `ToolError` (7줄)
```python
class ToolError(Exception):
    """Tool 내부에서 실패 응답으로 바꿀 오류. safe_tool이 fail(...)로 변환한다."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
```

`app/tools/common.py` · `safe_tool` (13줄)
```python
def safe_tool(func: Callable[..., dict]) -> Callable[..., dict]:
    """어떤 예외도 밖으로 나가지 않도록 감싼다."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> dict:
        try:
            return func(*args, **kwargs)
        except ToolError as e:
            return fail(e.code, e.message)
        except Exception as e:  # noqa: BLE001 - 마지막 방어선
            return fail(ErrorCode.INTERNAL_ERROR, f"{type(e).__name__}: 내부 처리 중 오류가 발생했습니다.")

    return wrapper
```

`app/tools/common.py` · `http_get` (45줄)
```python
def http_get(url: str, *, ttl: int = 0, as_text: bool = False) -> Any:
    """GET 후 JSON(또는 텍스트)을 반환. ttl>0이면 디스크에 캐시한다.

    실패는 ToolError(NOT_FOUND / TIMEOUT / UPSTREAM_ERROR)로 올린다.
    PokeAPI 공정 이용 정책(로컬 캐시 권장)과 Smogon 대용량 파일 재다운로드 방지를 위해 캐시를 둔다.
    """
    key = hashlib.sha1(url.encode()).hexdigest()
    cached = _mem_get(key)
    if cached is not None:
        return cached

    path = config.CACHE_DIR / f"{key}.{'txt' if as_text else 'json'}"
    if ttl > 0 and path.exists() and time.time() - path.stat().st_mtime < ttl:
        raw = path.read_text(encoding="utf-8")
        value = raw if as_text else json.loads(raw)
        _mem_put(key, value)
        return value

    try:
        r = _session.get(url, timeout=config.HTTP_TIMEOUT)
    except requests.Timeout:
        raise ToolError(ErrorCode.TIMEOUT, "외부 데이터 서버 응답이 지연되고 있습니다.")
    except requests.RequestException:
        raise ToolError(ErrorCode.UPSTREAM_ERROR, "외부 데이터 서버에 연결하지 못했습니다.")

    if r.status_code == 404:
        raise ToolError(ErrorCode.NOT_FOUND, "요청한 대상이 외부 데이터에 없습니다.")
    if r.status_code in (401, 403):
        raise ToolError(ErrorCode.INVALID_KEY, "외부 API 인증에 실패했습니다.")
    if r.status_code >= 400:
        raise ToolError(ErrorCode.UPSTREAM_ERROR, f"외부 데이터 서버가 오류를 반환했습니다 (HTTP {r.status_code}).")

    if as_text:
        value: Any = r.text
    else:
        try:
            value = r.json()
        except ValueError:
            raise ToolError(ErrorCode.UPSTREAM_ERROR, "외부 데이터 응답 형식이 올바르지 않습니다.")

    if ttl > 0:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(r.text, encoding="utf-8")
    _mem_put(key, value)
    return value
```

`app/agent/llm.py` · `classify_llm_error` (12줄)
```python
def classify_llm_error(e: Exception) -> LLMUnavailable:
    """LLM 호출 예외를 사용자에게 보여줄 수 있는 코드로 바꾼다 (원문은 노출하지 않음)."""
    if isinstance(e, LLMUnavailable):
        return e
    text = f"{type(e).__name__} {e}".lower()
    if "401" in text or "403" in text or "authentication" in text or "api key" in text:
        return LLMUnavailable(ErrorCode.INVALID_KEY, "LLM API 키가 올바르지 않습니다. LLM_API_KEY를 확인하세요.")
    if "timeout" in text:
        return LLMUnavailable(ErrorCode.TIMEOUT, "LLM 응답이 지연되고 있습니다. 잠시 후 다시 시도하세요.")
    if "404" in text or "model" in text and "not" in text:
        return LLMUnavailable(ErrorCode.UPSTREAM_ERROR, "LLM 접속 주소나 모델 이름을 확인하세요 (LLM_BASE_URL, LLM_MODEL).")
    return LLMUnavailable(ErrorCode.UPSTREAM_ERROR, "LLM 서버가 정상 응답하지 않았습니다.")
```
