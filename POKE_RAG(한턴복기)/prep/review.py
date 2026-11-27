"""한 턴 복기 계산 (docs/designs/loss-review-coach.md v1.3 + CEO 리뷰 범위). 숫자는 코드가 계산하고 LLM은 문장만 쓴다.
  .venv/Scripts/python -m prep.review '{"my_form_key":"dragonite","opp_form_key":"garchomp","actor":"opp","move_key":"dragon-claw","actual":{"kind":"ko"}}'
요청(dict):
  my_form_key, opp_form_key, actor("opp"=상대가 나를 공격 / "me"=내가 상대를 공격), move_key
  actual: {"kind": "ko"|"survived"|"outsped"|"slower", "hp_band": "75+"|"50-75"|"25-50"|"<25"(survived만)}
  선택: my_build {sp, nature, item, ability}, opp_sp {"atk": 20, ...}, flags [crit, weather, stat_stage, tera, trick_room,
        burn, reflect, light_screen, tailwind, terrain], pre_hit_hp (맞기 전 남은 HP 비율 0~1, 기본 1)
v1 범위 밖(TODOS.md, CEO S1~S4): 특수 계산 기술 분기·화상/벽 계산·상대 기술 입력·회복 열매 보조 문구.
"""
import json
import re
import sys

import config
from prep import calculator as c

STATS = ("hp", "atk", "def", "spa", "spd", "spe")
BOOST_NATURE = {"atk": "adamant", "spa": "modest", "def": "impish", "spd": "careful", "spe": "jolly"}  # 관계 스탯 +, 무관 스탯 −
HP_BANDS = {"75+": (75, 101), "50-75": (50, 75), "25-50": (25, 50), "<25": (0, 25)}  # 남은 HP %, [하한, 상한)
FLAG_NAMES = {"crit": "급소", "weather": "날씨", "stat_stage": "능력 변화", "tera": "테라스탈", "trick_room": "트릭룸", "burn": "화상",
              "reflect": "리플렉터", "light_screen": "빛의장막", "tailwind": "순풍", "terrain": "필드"}
# 데미지·스피드에 영향을 주지만 v1에서 계산하지 않는 특성(U5). 있으면 이름만 unsupported에 적는다.
UNCOMPUTED_ABILITIES = {
    "tough-claws", "sheer-force", "strong-jaw", "sharpness", "mega-launcher", "aerilate", "pixilate", "refrigerate",
    "galvanize", "guts", "hustle", "tinted-lens", "sniper", "analytic", "solar-power", "water-bubble", "steelworker", "transistor",
    "dragons-maw", "thick-fat", "filter", "solid-rock", "prism-armor", "fur-coat", "ice-scales", "fluffy", "heatproof", "water-absorb",
    "volt-absorb", "flash-fire", "sap-sipper", "storm-drain", "lightning-rod", "motor-drive", "earth-eater", "dry-skin", "wonder-guard",
    "sturdy", "supreme-overlord", "protosynthesis", "quark-drive", "speed-boost", "swift-swim", "chlorophyll", "sand-rush",
    "slush-rush", "unburden", "quick-feet", "surge-surfer", "defiant", "competitive", "punk-rock", "rocky-payload", "parental-bond",
    "mega-sol", "orichalcum-pulse", "hadron-engine", "unseen-fist", "multitype", "intimidate"}  # 위협은 D19 경로로만(D21)
SMOGON_LABEL = "Pokémon Showdown(시뮬레이터) 환경에서 수집된 데이터"


def current_season(db):
    """현재 시즌: config.CURRENT_SEASON이 있으면 그 값, 없으면 meta_usage의 최신 시즌(D13). 색인과 복기가 같이 쓴다."""
    if config.CURRENT_SEASON:
        return config.CURRENT_SEASON
    n = db.execute("SELECT MAX(CAST(SUBSTR(season, 3) AS INT)) FROM meta_usage").fetchone()[0]
    if n is None:
        raise ValueError("meta_usage가 비어 있습니다: python -m prep.build_db")
    return f"M-{n}"


# --- 입력 해석 ---
SP_PAIR = re.compile(r"(?<![A-Z])([HABCDS])\s*(\d{1,2})(?!\d)")  # \b는 한글을 글자로 봐서 "A20한카리아스"를 놓친다(eng #3 F6)
SP_ALIAS = re.compile(r"(?<![A-Z0-9])[HABCDS]{2}(?![A-Z0-9])")
LETTERS = {"H": "hp", "A": "atk", "B": "def", "C": "spa", "D": "spd", "S": "spe"}
STAT_LETTER = {v: k for k, v in LETTERS.items()}


def sp_mentions(text, db=None):
    """SP 표기가 적힌 자리마다 {"kind": "pair"|"alias", "start", "end", "sp"}. 공백·쉼표로만 이어진 쌍("H32 B32", "H32B32")은 한 자리로 묶는다.
    추출 단계가 가장 가까운 포켓몬 언급에 붙인다(eng #3 R2). 별칭("AS")은 db가 있을 때만 찾는다."""
    up, out = text.upper(), []
    for m in SP_PAIR.finditer(up):
        stat, n = LETTERS[m.group(1)], int(m.group(2))
        if out and out[-1]["kind"] == "pair" and not up[out[-1]["end"]:m.start()].strip(" ,"):
            out[-1]["sp"][stat] = out[-1]["sp"].get(stat, 0) + n
            out[-1]["end"] = m.end()
        else:
            out.append({"kind": "pair", "start": m.start(), "end": m.end(), "sp": {stat: n}})
    if db is not None:
        for m in SP_ALIAS.finditer(up):
            row = db.execute("SELECT target_key FROM alias WHERE kind='spread' AND alias=?", (m.group(),)).fetchone()
            if row:
                out.append({"kind": "alias", "start": m.start(), "end": m.end(),
                            "sp": {k: int(v) for k, v in (x.split(":") for x in row[0].split(","))}})
    for x in out:
        c.check_sp(x["sp"])
    return sorted(out, key=lambda x: x["start"])


def parse_sp_text(text, db=None):
    """"A20 S32" 같은 SP 표기 또는 별칭("AS")을 {스탯: SP}로(D22, 코드만 해석). 한 포켓몬 분량 입력용: 직접 표기가 있으면 그 합, 없으면 첫 별칭."""
    found = sp_mentions(text, db)
    pairs = [x for x in found if x["kind"] == "pair"]
    if pairs:
        sp = {}
        for x in pairs:
            for k, v in x["sp"].items():
                sp[k] = sp.get(k, 0) + v
        c.check_sp(sp)
        return sp
    return found[0]["sp"] if found else None


# --- 후보 데이터 ---
def _pokedb_items(db, form_key):
    row = db.execute("SELECT top_items FROM meta_usage WHERE form_key=? AND season=? AND rule='single'",
                     (form_key, current_season(db))).fetchone()
    return [(k, float(n)) for k, n in json.loads(row[0])] if row else []


def _smogon_row(db, form_key):
    row = db.execute("SELECT items, abilities, spreads, month FROM smogon_usage WHERE form_key=?", (form_key,)).fetchone()
    return None if row is None else {"items": json.loads(row[0]), "abilities": json.loads(row[1]), "spreads": json.loads(row[2]), "month": row[3]}


def _form_abilities(db, form_key):
    row = db.execute("SELECT ability1, ability2, hidden_ability FROM pokemon WHERE form_key=?", (form_key,)).fetchone()
    if row is None:
        raise ValueError(f"알 수 없는 폼: {form_key}")
    return [a for a in row if a]


def _parse_spread(s):
    """Smogon "Adamant:1/32/0/0/1/32" → ("adamant", {"hp": 1, ...})."""
    nature, nums = s.split(":")
    return nature.lower(), {k: int(v) for k, v in zip(STATS, nums.split("/")) if int(v)}


def _alias_spreads(db):
    targets = {t for (t,) in db.execute("SELECT target_key FROM alias WHERE kind='spread'")}
    uniq = {tuple(sorted(x.split(","))) for x in targets}  # "atk:32,spe:32"와 "spe:32,atk:32"는 같은 배분(15종)
    return [{k: int(v) for k, v in (p.split(":") for p in t)} for t in sorted(uniq)]


def _relevant(actor_is_opp, category, kind):
    """상대 쪽에서 결과를 좌우하는 스탯."""
    if kind in ("outsped", "slower"):
        return ["spe"]
    if actor_is_opp:
        return ["atk" if category == "physical" else "spa"]
    return ["hp", "def" if category == "physical" else "spd"]


def _norm(pairs):
    tot = sum(w for _, w in pairs)
    return [(k, w / tot) for k, w in pairs] if tot else []


def opponent_candidates(db, basis, req, category):
    """[(그룹, 빌드, 가중치)]와 메모. 그룹 = 결과에 영향 있는 도구 키, 영향 없는 도구는 '_neutral'. (c) 미지원 도구는 제외하고 비중을 보고한다."""
    opp, actor_is_opp, kind = req["opp_form_key"], req["actor"] == "opp", req["actual"]["kind"]
    role = "attack" if actor_is_opp else "defense"
    notes, sm = [], _smogon_row(db, opp)
    items = _pokedb_items(db, opp) if basis == "pokedb" else ([(k, w) for k, w in sm["items"]] if sm else [])
    if not items:
        notes.append(f"{'pokedb ' + current_season(db) if basis == 'pokedb' else 'Smogon'}: 이 포켓몬의 사용 통계 없음 — 도구 없음으로 가정")
        items = [("", 1.0)]
    items = _norm(items)
    kept, excluded = [], 0.0
    speed_kind = kind in ("outsped", "slower")
    for k, w in items:
        kd = c.item_kind(db, k, role) if not k.startswith("showdown:") else "unsupported"
        if speed_kind and k != "iron-ball":  # 스피드 결과: 구애스카프만 영향(검은철구는 미지원)
            kd = "affects" if k == "choice-scarf" else "neutral"
        elif k == "choice-scarf":  # 데미지 결과: 스카프는 영향 없음
            kd = "neutral"
        if kd == "unsupported":
            excluded += w
        else:
            kept.append((k if kd == "affects" else "_neutral", k, w))
    # 배분·성격
    if req.get("opp_sp"):
        rel = _relevant(actor_is_opp, category, kind)
        spreads = [((BOOST_NATURE.get(rel[-1], "hardy"), req["opp_sp"]), 0.5), (("hardy", req["opp_sp"]), 0.5)]
    elif basis == "smogon" and sm and sm["spreads"]:
        spreads = _norm([(_parse_spread(s), w) for s, w in sm["spreads"][:config.SMOGON_TOP_SPREADS]])
    else:
        rel = _relevant(actor_is_opp, category, kind)
        nat = [BOOST_NATURE.get(rel[-1], "hardy"), "hardy"]
        spreads = _norm([((n, sp), 1.0) for sp in _alias_spreads(db) for n in nat])
        notes.append("상대 배분은 SP 32/32 별칭 15종 × 성격 2종을 같은 비중으로 가정(중간·무투자 배분은 후보에 없음)")
    # 특성(위협은 D19 경로라 None으로 둔다)
    if basis == "smogon" and sm and sm["abilities"]:
        abilities = _norm([(a, w) for a, w in sm["abilities"]])
    else:
        abilities = _norm([(a, 1.0) for a in _form_abilities(db, opp)])
    cands = []
    for group, item, wi in kept:
        for (nature, sp), ws in spreads:
            for ab, wa in abilities:
                cands.append((group, {"form_key": opp, "sp": sp, "nature": nature, "item": item or None,
                                      "ability": None if ab == "intimidate" else ab}, wi * ws * wa))
    return cands, excluded, notes, abilities


def my_default_build(db, basis, req, category):
    """U9: 내 빌드를 주지 않았으면 그 기준 통계에서 가장 확률이 높은 형태로 가정. 반환: (빌드, 가정 문장)."""
    me, actor_is_me = req["my_form_key"], req["actor"] == "me"
    given = req.get("my_build") or {}
    sm = _smogon_row(db, me) if basis == "smogon" else None
    role = "attack" if actor_is_me else "defense"
    calc_items = lambda pairs: [k for k, _ in pairs if not k.startswith("showdown:") and c.item_kind(db, k, role) != "unsupported"]
    if sm:
        nature, sp = _parse_spread(sm["spreads"][0][0]) if sm["spreads"] else ("hardy", {})
        item = (calc_items(sm["items"]) or [None])[0]
        ability = sm["abilities"][0][0] if sm["abilities"] else _form_abilities(db, me)[0]
        src = f"Smogon {sm['month']} 분포 1위"
    else:
        kind = req["actual"]["kind"]
        rel = ["spe"] if kind in ("outsped", "slower") else (["atk" if category == "physical" else "spa"] if actor_is_me
                                                             else ["hp", "def" if category == "physical" else "spd"])
        sp, nature = {s: 32 for s in rel}, BOOST_NATURE.get(rel[-1], "hardy")
        item = (calc_items(_pokedb_items(db, me)) or [None])[0]
        ability = _form_abilities(db, me)[0]
        src = f"pokedb {current_season(db)} 도구 1위 + 관련 스탯 SP 32·보정 성격"
    build = {"form_key": me, "sp": given.get("sp", sp), "nature": given.get("nature", nature),
             "item": given.get("item", item), "ability": given.get("ability", ability)}
    assumed = [k for k in ("sp", "nature", "item", "ability") if k not in given]
    note = f"내 빌드 가정({src}): " + build_ko(db, build, assumed) if assumed else ""
    return build, note


def _ko_name(db, table, key):
    col = "move_key" if table == "move" else "key"
    row = db.execute(f"SELECT name_ko FROM {table} WHERE {col}=?", (key,)).fetchone() if key else None
    return (row and row[0]) or key


def build_ko(db, build, keys=("sp", "nature", "ability", "item")):
    """빌드 → "H32 B32 · 장난꾸러기 · 특성 모래숨기 · 구애스카프"(화면에 영문 키를 내지 않는다, 디자인 E2)."""
    parts = []
    for k in keys:
        if k == "sp":
            parts.append(" ".join(f"{STAT_LETTER[s]}{build['sp'][s]}" for s in STATS if build["sp"].get(s)) or "SP 무투자")
        elif k == "nature":
            parts.append(_ko_name(db, "nature", build["nature"]))
        elif k == "ability" and build.get("ability"):
            parts.append("특성 " + _ko_name(db, "ability", build["ability"]))
        elif k == "item":
            parts.append(_ko_name(db, "item", build["item"]) if build.get("item") else "도구 없음")
    return " · ".join(parts)


# --- 일치 판정 ---
def match_fraction(db, req, me, opp, stage=0):
    """그 후보로 실제 결과가 나오는 비율(D15): 데미지는 16개 난수 중 결과를 재현하는 수 ÷ 16, 스피드는 1/0(동속 1/2). (비율, k)"""
    kind, actor_is_opp = req["actual"]["kind"], req["actor"] == "opp"
    if kind in ("outsped", "slower"):
        so, sm_ = c.speed(db, opp), c.speed(db, me)
        first = 0.5 if so == sm_ else float(so > sm_)  # 상대가 먼저 움직일 확률
        if "trick_room" in req.get("flags", []):
            first = 1 - first
        f = first if kind == "outsped" else 1 - first
        return f, None
    atk, dfn = (opp, me) if actor_is_opp else (dict(me, atk_stage=stage), opp)
    pre = req.get("pre_hit_hp")
    full = pre is None or pre >= 1
    r = c.damage_rolls(db, atk, dict(dfn, full_hp=full), req["move_key"])
    hp = r["hp"]
    left_before = hp if full else max(1, int(hp * pre))
    sash = full and dfn.get("item") == "focus-sash"
    lefts = [1 if (sash and d >= left_before) else left_before - d for d in r["rolls"]]  # 기합의띠: 풀HP면 1로 버팀
    if kind == "ko":
        k = sum(1 for x in lefts if x <= 0)
    else:
        lo, hi = HP_BANDS[req["actual"].get("hp_band", "75+")]
        k = sum(1 for x in lefts if x > 0 and lo <= x * 100 / hp < hi)
    return k / 16, k


def _uniq(dicts, n=3):
    """겹치지 않는 앞쪽 n개(조건 후보는 수천 개라 n개를 찾으면 멈춘다)."""
    out = []
    for d in dicts:
        if d not in out:
            out.append(d)
            if len(out) == n:
                break
    return out


def _label(group):
    return "이 타격에 영향 없는 도구(도구 없음 포함)" if group == "_neutral" else group


def compute_basis(db, basis, req, category, me):
    cands, excluded, notes, _ = opponent_candidates(db, basis, req, category)
    groups = {}
    for group, build, w in cands:
        f, k = match_fraction(db, req, me, build)
        g = groups.setdefault(group, {"w": 0.0, "wm": 0.0, "conds": []})
        g["w"] += w
        g["wm"] += w * f
        if f > 0:
            g["conds"].append((w * f, build["nature"], build["sp"], build["ability"], k, None))
    # D19: 내가 공격했는데 버텼으면 "공격 −1(위협 등)"
    if req["actor"] == "me" and req["actual"]["kind"] == "survived":
        prior = config.REVIEW_INTIMIDATE_PRIOR
        g = groups.setdefault("_atk_minus1", {"w": 0.0, "wm": 0.0, "conds": []})
        tot = sum(w for _, _, w in cands)
        for group, build, w in cands:
            f, k = match_fraction(db, req, me, build, stage=-1)
            g["w"] += prior * w / tot
            g["wm"] += prior * w / tot * f
            if f > 0:
                g["conds"].append((w * f, build["nature"], build["sp"], build["ability"], k, group))
        for x in (x for key, x in groups.items() if key != "_atk_minus1"):  # 나머지 그룹의 사전 비중 합을 (1 − prior)로 맞춘다
            x["w"] *= (1 - prior) / max(tot, 1e-12)
            x["wm"] *= (1 - prior) / max(tot, 1e-12)
    total_wm = sum(g["wm"] for g in groups.values())
    ratios = {k: g["wm"] / g["w"] for k, g in groups.items() if g["w"] > 0}
    def cause(k, g):
        conds = sorted(g["conds"], key=lambda x: -x[0])  # (가중치×일치 비율) 큰 순. 1번이 대표 조건
        rolls = None
        if req["actual"]["kind"] in ("ko", "survived") and conds:
            rolls = f"가장 그럴듯한 조건에서 16번 중 {conds[0][4]}번"  # D6: 그룹 최댓값은 순위와 거꾸로 보일 수 있다
        return {"key": k, "label": "공격 −1(위협 등, 확정 아님)" if k == "_atk_minus1" else _label(k),
                "prob": g["wm"] / total_wm if total_wm else 0.0, "match_ratio": ratios.get(k, 0.0), "rolls": rolls,
                "rolls_k": conds[0][4] if conds else 0,
                "conditions": list(dict.fromkeys(f"{n} {sp} {f'{_label(gr)}·' if gr else ''}{ab or ''}".strip() for _, n, sp, ab, _, gr in conds))[:3],
                "conditions_raw": _uniq({"nature": n, "sp": sp, "ability": ab, "item_group": gr} for _, n, sp, ab, _, gr in conds)}  # 화면용(한글은 서버가 붙인다)
    causes = sorted((cause(k, g) for k, g in groups.items()), key=lambda x: -x["prob"])
    item_ratios = [ratios[k] for k in ratios if k != "_atk_minus1"]
    undetermined = total_wm > 0 and len(item_ratios) > 1 and max(item_ratios) - min(item_ratios) < config.REVIEW_MIN_SPREAD
    sm = _smogon_row(db, req["opp_form_key"])
    source = {"pokedb": {"label": f"pokedb {current_season(db)} 싱글 상위 구축(실제 게임 랭크배틀)"},
              "smogon": {"label": f"Smogon {sm['month'] if sm else config.SMOGON_MONTH} · {config.SMOGON_FORMAT} · {config.SMOGON_CUTOFF}+",
                         "note": SMOGON_LABEL, "url": "https://www.smogon.com/stats/"}}[basis]
    return {"basis": basis, "source": source, "causes": [x for x in causes if x["prob"] > 0][:3], "zero_match": total_wm == 0,
            "undetermined": undetermined, "excluded_share": round(excluded, 4), "notes": notes}


# --- 계산표: 통계에 없어도 계산상 이 결과가 나오는 상대 빌드 (사용자 지시 2026-10-23, 친구 사례 1) ---
# 시중 계산기(스마트누오 등)처럼 상대의 대표 빌드를 하나씩 계산해 결과가 나오는 줄만 보여 주고, 통계는 각 줄에 붙인다.
CALC_ROWS = 6


def champions_items(db):
    """지금 챔피언스에서 쓸 수 있는 도구(champion_item 표: Bulbapedia·Showdown 대조, prep/champions_items.py).
    구애머리띠·구애안경·돌격조끼 등은 없다. 표가 비어 있으면 오류: 실전 통계 등장 여부로 대신하면 안 쓰는 도구를 "없음"으로 잘못 표시한다."""
    keys = {k for (k,) in db.execute("SELECT key FROM champion_item")}
    if not keys:
        raise RuntimeError("champion_item 표가 비어 있습니다: python -m prep.champions_items download")  # 입력 오류(ValueError)가 아니라 서버 준비 문제
    return keys


def _item_pool(db, role, move_type, category, kind):
    """이 결과에 영향을 줄 수 있는 도구 후보 + 도구 없음(None). 같은 결과를 내는 도구는 계산 뒤에 한 줄로 묶는다."""
    if kind in ("outsped", "slower"):
        return ["choice-scarf", None]
    if role == "attack":
        pool = list(c.STAT_ITEMS) + list(c.FINAL_ITEMS) + list(c.POWER_ITEMS) + list(c.SPECIES_ITEMS)
        pool += [k for k, e in db.execute("SELECT key, effect_en FROM item WHERE effect_en LIKE '%-type moves%'")
                 if (m := c.TYPE_BOOST.search(e or "")) and m.group(1).lower() == move_type]
    else:
        pool = list(c.DEF_STAT_ITEMS) + ["focus-sash"] + (["air-balloon"] if move_type == "ground" else [])
        pool += [k for k, e in db.execute("SELECT key, effect_en FROM item WHERE effect_en LIKE '%to halve%'")
                 if (m := c.RESIST_BERRY.search(e or "")) and m.group(1).lower() == move_type]
    return pool + [None]


def _usage_shares(db, form_key):
    """그 포켓몬의 도구·특성 사용 비중. pokedb는 도구만, Smogon은 도구·특성."""
    pk = dict(_norm(_pokedb_items(db, form_key)))
    sm = _smogon_row(db, form_key)
    return {"pokedb_item": pk, "smogon_item": dict(_norm([tuple(x) for x in sm["items"]])) if sm else {},
            "smogon_ability": dict(_norm([tuple(x) for x in sm["abilities"]])) if sm else {}}


def calc_table(db, req, category, me):
    """상대 빌드 [SP | 성격 | 특성 | 도구]마다 이 결과가 나오는 난수 수. 결과가 나오는 줄을 챔피언스 도구 → 그 포켓몬 도구 사용률 → 난수 수 순으로.
    결과가 나오는 줄이 없으면 가장 가까운 줄(데미지가 가장 큰/작은 쪽)을 near로 준다."""
    opp, kind, actor_is_opp = req["opp_form_key"], req["actual"]["kind"], req["actor"] == "opp"
    mv = db.execute("SELECT type FROM move WHERE move_key=?", (req["move_key"],)).fetchone()
    rel = _relevant(actor_is_opp, category, kind)
    sp = req.get("opp_sp") or {s: 32 for s in rel}
    natures = [BOOST_NATURE.get(rel[-1], "hardy")] + ([] if req.get("opp_sp") else ["hardy"])
    abilities = [a for a in _form_abilities(db, opp) if a != "intimidate"] or [None]
    role = "attack" if actor_is_opp else "defense"
    champ, usage = champions_items(db), _usage_shares(db, opp)
    speed = kind in ("outsped", "slower")
    rows = {}
    for nature in natures:
        for item in _item_pool(db, role, mv[0], category, kind):
            for ability in abilities:
                build = {"form_key": opp, "sp": sp, "nature": nature, "item": item, "ability": ability}
                f, k = match_fraction(db, req, me, build)
                if speed:
                    val = (c.speed(db, build), c.speed(db, me))
                else:
                    atk, dfn = (build, me) if actor_is_opp else (dict(me, atk_stage=0), build)
                    r = c.damage_rolls(db, atk, dict(dfn, full_hp=req.get("pre_hit_hp") is None or req["pre_hit_hp"] >= 1), req["move_key"])
                    val = (r["rolls"][0] * 100 / r["hp"], r["rolls"][-1] * 100 / r["hp"])
                key = (nature, item, round(val[0], 4), round(val[1], 4))  # 같은 결과인 특성은 한 줄로 묶는다
                row = rows.setdefault(key, {"sp": sp, "nature": nature, "item": item, "abilities": [], "k": k, "match": f, "value": val})
                row["abilities"].append(ability)
    # 같은 결과인 도구도 묶는다(녹지않는얼음·고드름플레이트, 도구 없음·영향 없는 도구)
    merged = {}
    for r in rows.values():
        mk = (r["nature"], tuple(r["abilities"]), round(r["value"][0], 4), round(r["value"][1], 4))
        m = merged.setdefault(mk, dict(r, items=[]))
        m["items"].append(r["item"])
    out = []
    for r in merged.values():
        items = sorted((i for i in r["items"] if i), key=lambda i: (i not in champ, -usage["pokedb_item"].get(i, 0)))
        lead = None if None in r["items"] else next((i for i in items if i in champ), items[0])  # 대표: 도구 없음 > 챔피언스 도구 > 사용률
        all_abilities = len(r["abilities"]) == len(abilities)
        out.append({"sp": r["sp"], "nature": r["nature"], "abilities": None if all_abilities else r["abilities"],
                    "item": lead, "same_items": [i for i in items if i != lead and i is not None][:3],
                    "in_champions": lead is None or lead in champ,
                    "k": r["k"], "match": r["match"], "value": [round(v, 1) for v in r["value"]] if not speed else list(r["value"]),
                    "usage": {"pokedb_item": usage["pokedb_item"].get(lead), "smogon_item": usage["smogon_item"].get(lead),
                              "smogon_ability": max((usage["smogon_ability"].get(a, 0) for a in r["abilities"] if a), default=None) if not all_abilities else None}})
    hit = sorted((r for r in out if r["match"] > 0),
                 key=lambda r: (not r["in_champions"], -(r["usage"]["pokedb_item"] or 0), -(r["usage"]["smogon_item"] or 0), -r["match"]))
    near = [] if hit or speed else sorted(out, key=lambda r: -r["value"][1] if kind == "ko" else r["value"][0])[:2]
    return {"rows": hit[:CALC_ROWS], "more": max(0, len(hit) - CALC_ROWS), "near": near, "my_build": {k: me[k] for k in ("sp", "nature", "item", "ability")},
            "assumed": "상대 SP는 입력값" if req.get("opp_sp") else f"상대 SP {' '.join(STAT_LETTER[x] + '32' for x in rel)}, 보정 성격과 무보정 성격을 계산"}


def differs(a, b):
    """D31: 1순위 원인이 다르거나 같은 원인의 확률 차이가 DIFF_REVIEW_PROB 이상이면 True. (판정, 이유)"""
    if a["zero_match"] != b["zero_match"] or a["undetermined"] != b["undetermined"]:
        return True, "한쪽만 일치 0건 또는 도구 구분 불가"
    if not a["causes"] or not b["causes"]:
        return False, ""
    ta, tb = a["causes"][0], b["causes"][0]
    if ta["key"] != tb["key"]:
        return True, f"1순위 원인이 다름: {ta['label']} / {tb['label']}"
    if abs(ta["prob"] - tb["prob"]) >= config.DIFF_REVIEW_PROB:
        return True, f"1순위 원인의 확률 차이 {abs(ta['prob'] - tb['prob']):.0%}"
    return False, ""


def review(db, req):
    """한 턴 복기. 두 기준(pokedb·Smogon)으로 각각 계산하고 차이를 판정한다(D32). LLM 없이 동작한다(D16)."""
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
        except ValueError as e:  # 특수 계산 기술 등: 일반 공식 대상이 아님(S1, v1 미지원)
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


if __name__ == "__main__":
    out = review(c.connect(), json.loads(sys.argv[1]))
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
