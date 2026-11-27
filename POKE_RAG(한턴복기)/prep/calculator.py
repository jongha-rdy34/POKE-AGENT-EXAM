"""실수치·결정력·내구 계산기. 공식과 출처는 data/docs/stat_damage_formulas.md (S1~S4)를 따른다.
LLM은 계산하지 않고 이 모듈이 계산한다(agent.md 6절).
"""
import re
import sqlite3
from fractions import Fraction

from config import DB_PATH
SP_PER_STAT, SP_TOTAL = 32, 66  # S1
STATS = ("hp", "atk", "def", "spa", "spd", "spe")
API_STAT = {"attack": "atk", "defense": "def", "special-attack": "spa", "special-defense": "spd", "speed": "spe"}
STAB = Fraction(3, 2)  # S3: 자속 1.5 (적응력 2, 테라스탈 상호작용은 미지원)
# 도구 보정은 PokeAPI 도구 효과 문구(data/raw/pokeapi/item)의 수치를 따른다. 챔피언스 등장 여부와 무관하다(agent.md 1.3절).
# 4096분율이 확인된 것(Bulbapedia Damage 문서 S3의 other 표)은 그 값을 쓴다. 나머지는 PokeAPI의 퍼센트를 그대로 분수로 쓴다.
STAT_ITEMS = {"choice-band": ("atk", Fraction(3, 2)), "choice-specs": ("spa", Fraction(3, 2))}  # 공격 실수치 ×1.5 (PokeAPI "by 50%")
POWER_ITEMS = {"muscle-band": ("physical", Fraction(11, 10)), "wise-glasses": ("special", Fraction(11, 10))}  # 해당 분류 기술 ×1.1 ("10%")
FINAL_ITEMS = {"life-orb": Fraction(5324, 4096), "expert-belt": Fraction(4915, 4096)}  # PokeAPI 30%·20%, 정확한 값은 S3. 달인의띠는 효과 굉장 시만
SPECIES_ITEMS = {"light-ball": ({"pikachu"}, ("atk", "spa")), "thick-club": ({"cubone", "marowak"}, ("atk",)),
                 "deep-sea-tooth": ({"clamperl"}, ("spa",))}  # 전용 도구: 해당 스탯 ×2 (PokeAPI "Doubles")
TYPE_BOOST = re.compile(r"(\w+)-[Tt]ype moves.*?(\d+)% more damage")  # 목탄·플레이트·향로 등 PokeAPI 문구에서 타입과 %를 읽는다


def item_multiplier(db, item_key, form_key, move_type, category, stat, super_effective=False):
    """공격 측 도구의 결정력 배율과 설명. 조건이 맞지 않으면 1배(적용 안 됨). 계산식이 없는 도구는 오류."""
    if item_key in STAT_ITEMS:
        st, m = STAT_ITEMS[item_key]
        return (m, "공격 실수치 보정") if st == stat else (Fraction(1), f"{item_key}: 이 기술({category})에는 적용되지 않음")
    if item_key in POWER_ITEMS:
        cat, m = POWER_ITEMS[item_key]
        return (m, "위력 보정") if cat == category else (Fraction(1), f"{item_key}: 이 기술({category})에는 적용되지 않음")
    if item_key in FINAL_ITEMS:
        if item_key == "expert-belt" and not super_effective:
            return Fraction(1), "expert-belt: 효과가 굉장한 경우에만 적용(super_effective=True 필요)"
        return FINAL_ITEMS[item_key], "데미지 보정"
    if item_key in SPECIES_ITEMS:
        species, stats = SPECIES_ITEMS[item_key]
        sp = _one(db, "SELECT species FROM pokemon WHERE form_key=?", (form_key,))[0]
        return (Fraction(2), "전용 도구 ×2") if sp in species and stat in stats else (Fraction(1), f"{item_key}: 이 포켓몬·스탯에는 적용되지 않음")
    row = _one(db, "SELECT effect_en FROM item WHERE key=?", (item_key,))
    if row is None:
        raise ValueError(f"알 수 없는 도구: {item_key}")
    m = TYPE_BOOST.search(row[0] or "")
    if m:  # 타입 강화 도구: 기술 타입이 같을 때만
        boost = 1 + Fraction(int(m.group(2)), 100)
        return (boost, f"{m.group(1)}타입 기술 강화") if m.group(1).lower() == move_type else (Fraction(1), f"{item_key}: {m.group(1)}타입 기술에만 적용")
    raise ValueError(f"계산식이 없는 도구: {item_key} (PokeAPI 효과: {row[0]})")


def check_sp(sp):
    """SP 입력 검증: 스탯당 0~32, 합계 66 이하 (S1)."""
    unknown = set(sp) - set(STATS)
    if unknown:
        raise ValueError(f"알 수 없는 스탯: {sorted(unknown)}")
    if any(not isinstance(v, int) or not 0 <= v <= SP_PER_STAT for v in sp.values()):
        raise ValueError(f"SP는 스탯당 0~{SP_PER_STAT} 정수여야 합니다: {sp}")
    if sum(sp.values()) > SP_TOTAL:
        raise ValueError(f"SP 합계는 {SP_TOTAL} 이하여야 합니다: {sum(sp.values())}")


def hp_stat(base, sp):
    """HP = 종족값 + SP + 75 (S1·S2·S4)"""
    return base + sp + 75


def other_stat(base, sp, nature_pct=100):
    """그 외 = floor((종족값 + SP + 20) × 보정). 보정은 정수 %(110/100/90)로 받아 부동소수 오차를 피한다."""
    return (base + sp + 20) * nature_pct // 100


def decisive_power(attack, power, stab=False, mods=()):
    """결정력 = 공격 실수치 × 위력 × 자속 × 보정들. 비교용 지표라 소수는 내린다."""
    m = STAB if stab else Fraction(1)
    for x in mods:
        m *= Fraction(x)
    return int(attack * power * m)


def bulk(hp, defense):
    """내구 = HP 실수치 × 방어(또는 특수방어) 실수치"""
    return hp * defense


def nature_pct(db, nature_key, stat):
    """성격 키와 스탯('atk' 등) → 110/100/90"""
    row = _one(db, "SELECT plus, minus FROM nature WHERE key=?", (nature_key,))
    if row is None:
        raise ValueError(f"알 수 없는 성격: {nature_key}")
    plus, minus = (API_STAT.get(x) for x in row)
    return 110 if stat == plus else 90 if stat == minus else 100


def actual_stats(db, form_key, sp, nature_key="hardy"):
    """폼의 여섯 실수치. sp는 {'atk': 32, ...}(없는 스탯은 0)."""
    check_sp(sp)
    row = _one(db, "SELECT hp, atk, def, spa, spd, spe FROM pokemon WHERE form_key=?", (form_key,))
    if row is None:
        raise ValueError(f"알 수 없는 폼: {form_key}")
    base = dict(zip(STATS, row))
    return {s: hp_stat(base[s], sp.get(s, 0)) if s == "hp" else other_stat(base[s], sp.get(s, 0), nature_pct(db, nature_key, s))
            for s in STATS}


def attack_decisive_power(db, form_key, move_key, sp, nature_key="hardy", item_key=None, super_effective=False):
    """공격 기술의 결정력. 물리는 atk, 특수는 spa를 쓰고 기술 타입이 자기 타입이면 자속을 건다.
    반환: 값과 계산 근거(답변의 '계산 근거' 블록용)."""
    mv = _one(db, "SELECT type, category, power FROM move WHERE move_key=?", (move_key,))
    if mv is None:
        raise ValueError(f"알 수 없는 기술: {move_key}")
    mtype, category, power = mv
    if category not in ("physical", "special") or not power:
        raise ValueError(f"위력이 있는 공격 기술이 아닙니다: {move_key} ({category}, power={power})")
    stat = "atk" if category == "physical" else "spa"
    types = _one(db, "SELECT type1, type2 FROM pokemon WHERE form_key=?", (form_key,))
    if types is None:
        raise ValueError(f"알 수 없는 폼: {form_key}")
    stab = mtype in types
    a = actual_stats(db, form_key, sp, nature_key)[stat]
    mult, note = item_multiplier(db, item_key, form_key, mtype, category, stat, super_effective) if item_key else (Fraction(1), None)
    value = decisive_power(a, power, stab, [mult])
    return {"value": value, "stat": stat, "attack": a, "power": power, "stab": stab, "item": item_key, "item_multiplier": str(mult),
            "item_note": note, "nature": nature_key,
            "formula": f"{a} × {power}" + (" × 1.5(자속)" if stab else "") + (f" × {mult}({item_key})" if mult != 1 else "")}


# --- 데미지 범위 (stat_damage_formulas.md 4-1절, 싱글·레벨 50). 날씨·급소·화상·특성·랭크는 아직 미지원(설계 D28·U5는 복기 단계에서 추가).
ROLLS = range(85, 101)  # 난수 16개
DEF_STAT_ITEMS = {"assault-vest": ("spd", Fraction(3, 2))}  # PokeAPI "Special Defense to 1.5×"
RESIST_BERRY = re.compile(r"super-effective (\w+)-type attack to halve")  # 반감 열매 PokeAPI 문구
RECOVERY_BERRIES = {"sitrus-berry", "oran-berry"}  # D27: 기본 계산 제외, 보조 문구만
ATTACK_UNSUPPORTED = {"metronome", "loaded-dice", "punching-glove", "adamant-orb", "lustrous-orb", "griseous-orb"}
DEFENSE_UNSUPPORTED = {"eviolite", "figy-berry", "wiki-berry", "mago-berry", "aguav-berry", "iapapa-berry"}  # 수치 미확인(무화과열매류는 PokeAPI 문구가 구세대로 보임)
# 일반 공식에 넣으면 틀리는 기술(U6). 이 함수는 거절하고, 복기 단계에서 기술별 분기로 처리한다.
SPECIAL_FORMULA_MOVES = {"body-press", "foul-play", "psyshock", "psystrike", "secret-sword", "seismic-toss", "night-shade",
                         "low-kick", "grass-knot", "heavy-slam", "heat-crash", "water-spout", "eruption", "dragon-energy",
                         "last-respects", "weather-ball", "super-fang", "final-gambit", "endeavor"}
MULTI_HIT = re.compile(r"[Hh]its (?:2-5|two to five|\d) times|[Hh]its twice|[Hh]its three times")


def poke_round(x):
    """가장 가까운 정수로 반올림, 0.5는 내림 (S3 'rounding down at 0.5')."""
    x = Fraction(x)
    n = x.numerator // x.denominator
    return n + 1 if x - n > Fraction(1, 2) else n


def type_effectiveness(db, move_type, def_types):
    m = Fraction(1)
    for t in def_types:
        if t:
            m *= Fraction(_one(db, "SELECT mult FROM type_chart WHERE atk_type=? AND def_type=?", (move_type, t))[0])
    return m


def _is_mega_stone(db, item_key):
    row = _one(db, "SELECT is_mega_stone FROM item WHERE key=?", (item_key,))
    return bool(row and row[0])


def item_kind(db, item_key, role):
    """도구 3분류(U1·U2): 'affects' 이 타격·스피드에 보정 있음 / 'neutral' 영향 없음(=1.0) / 'unsupported' 영향 가능하나 계산식 없음
    / 'recovery' 회복 열매(D27, 기본 계산 제외·보조 문구용) / 'none' 도구 없음. role은 'attack' 또는 'defense'."""
    if not item_key:
        return "none"
    if role == "attack":
        if item_key in ATTACK_UNSUPPORTED:
            return "unsupported"
        if item_key == "choice-scarf" or item_key in STAT_ITEMS or item_key in POWER_ITEMS or item_key in FINAL_ITEMS or item_key in SPECIES_ITEMS:
            return "affects"
        row = _one(db, "SELECT effect_en FROM item WHERE key=?", (item_key,))
        if row is None:
            raise ValueError(f"알 수 없는 도구: {item_key}")
        return "affects" if TYPE_BOOST.search(row[0] or "") else "neutral"
    if role != "defense":
        raise ValueError(f"role은 attack/defense: {role}")
    if item_key in DEFENSE_UNSUPPORTED:
        return "unsupported"
    if item_key in RECOVERY_BERRIES:
        return "recovery"
    if item_key in DEF_STAT_ITEMS or item_key in ("focus-sash", "air-balloon", "choice-scarf"):
        return "affects"
    row = _one(db, "SELECT effect_en FROM item WHERE key=?", (item_key,))
    if row is None:
        raise ValueError(f"알 수 없는 도구: {item_key}")
    return "affects" if RESIST_BERRY.search(row[0] or "") else "neutral"


# 계산하는 특성(U5 + 부유 면역). 위협은 특성이 아니라 공격 랭크 −1(atk_stage)로 받는다(D19·D21).
ATTACK_STAT_ABILITIES = {"huge-power", "pure-power"}  # PokeAPI "Doubles Attack"
# 철주먹 대상(Bulbapedia "punching move", 9세대). DB에 기술 플래그가 없어 목록으로 둔다
PUNCH_MOVES = {"bullet-punch", "comet-punch", "dizzy-punch", "double-iron-bash", "drain-punch", "dynamic-punch", "fire-punch", "focus-punch",
               "hammer-arm", "headlong-rush", "ice-hammer", "ice-punch", "jet-punch", "mach-punch", "mega-punch", "meteor-mash", "plasma-fists",
               "power-up-punch", "rage-fist", "shadow-punch", "sky-uppercut", "surging-strikes", "thunder-punch", "wicked-blow"}
SUPPORTED_ABILITIES = ATTACK_STAT_ABILITIES | {"adaptability", "technician", "multiscale", "levitate", "iron-fist"}


def _build(b):
    """빌드 객체 {form_key, sp, nature, item, ability, atk_stage, full_hp}의 기본값."""
    return {"sp": {}, "nature": "hardy", "item": None, "ability": None, "atk_stage": 0, "full_hp": True, **b}


def stage_stat(stat, stage):
    """랭크 보정: +n은 ×(2+n)/2, −n은 ×2/(2+n), 내림 (Stat modifier 문서)."""
    return stat * (2 + stage) // 2 if stage >= 0 else stat * 2 // (2 - stage)


def speed(db, build):
    """스피드 실수치. 구애스카프는 ×1.5 (PokeAPI 'Increases Speed by 50%')."""
    b = _build(build)
    s = actual_stats(db, b["form_key"], b["sp"], b["nature"])["spe"]
    return poke_round(s * Fraction(3, 2)) if b["item"] == "choice-scarf" else s


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

    # 공격 측: 랭크 → 특성·도구 순(Showdown과 같은 순서). 도구 단계는 기존 상수 표로 구분하고 값은 item_multiplier(PokeAPI 문구)를 쓴다(D14·D17·U3)
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


class CachedConnection(sqlite3.Connection):
    """읽기 전용 조회 결과를 연결 수명 동안 기억한다(eng #3 R4: 복기 한 번에 같은 성격·종족값을 10만 번 넘게 읽었다).
    DB를 고치는 연결(build_db)에는 쓰지 않는다."""

    def one(self, sql, args):
        cache = self.__dict__.setdefault("_cache", {})
        if (sql, args) not in cache:
            cache[sql, args] = self.execute(sql, args).fetchone()
        return cache[sql, args]


def _one(db, sql, args):
    return db.one(sql, args) if isinstance(db, CachedConnection) else db.execute(sql, args).fetchone()


def connect():
    return sqlite3.connect(DB_PATH, factory=CachedConnection)
