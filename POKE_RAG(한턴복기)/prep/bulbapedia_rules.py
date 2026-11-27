"""평가셋(data/eval/community_cases.jsonl) 태그에 나온 규칙·기술·특성·도구 문서를 Bulbapedia에서 선수집한다(설계 D23·T10).
5초 간격·단일 스레드, 받은 문서는 건너뛴다. 원문 전체를 캐시하고, 색인용으로는 소개 + 효과 절만 따로 저장한다.
  .venv/Scripts/python -m prep.bulbapedia_rules
저장: data/raw/bulbapedia_rules/{slug}.json  (CC BY-NC-SA 2.5, 원문 URL·판 번호 포함)
"""
import json
import re
import urllib.parse
from datetime import date

from config import DATA_DIR
from prep.bulbapedia import fetch

OUT = DATA_DIR / "raw" / "bulbapedia_rules"

# 문서 제목 → 평가셋 태그. 태그가 같은 문서 여러 개를 가리킬 수 있다.
RULE_PAGES = {
    # 기술
    "Fake Out (move)": ["fake_out", "champions_change"], "Wide Guard (move)": ["wide_guard"], "Sucker Punch (move)": ["sucker_punch"],
    "Aqua Jet (move)": ["priority"], "Trick Room (move)": ["trick_room"], "Weather Ball (move)": ["weather_ball"],
    "Last Resort (move)": ["last_resort"], "Electro Shot (move)": ["weather", "cloud_nine"], "Solar Beam (move)": ["weather", "cloud_nine"],
    "Reflect (move)": ["screens"], "Light Screen (move)": ["screens"], "Spore (move)": ["powder_immunity"],
    "Water Spout (move)": ["variable_power"], "Last Respects (move)": ["variable_power"], "Stealth Rock (move)": ["entry_hazard"],
    "Psychic Terrain (move)": ["psychic_terrain", "grounded"],
    # 특성
    "Prankster (Ability)": ["prankster", "dark_immunity"], "Illusion (Ability)": ["illusion"], "Inner Focus (Ability)": ["inner_focus", "intimidate"],
    "Intimidate (Ability)": ["intimidate"], "Levitate (Ability)": ["levitate", "grounded"], "Competitive (Ability)": ["competitive"],
    "Cloud Nine (Ability)": ["cloud_nine"], "Armor Tail (Ability)": ["armor_tail"], "Queenly Majesty (Ability)": ["queenly_majesty"],
    "Mega Sol (Ability)": ["mega_sol", "champions_change"], "Drought (Ability)": ["weather_ability_order"], "Drizzle (Ability)": ["weather_ability_order"],
    "Sand Stream (Ability)": ["weather_ability_order"],
    # 도구
    "Choice Scarf": ["choice_scarf", "speed"], "Iron Ball": ["iron_ball", "trick_room"], "Psychic Seed": ["terrain_seed"],
    # 규칙
    "Priority": ["priority"], "Critical hit": ["crit", "crit_stage"], "Stat modifier": ["stat_stage"], "Weather": ["weather"],
    "Terrain": ["psychic_terrain", "grounded"], "Entry hazard": ["entry_hazard", "ability_timing"], "Burn (status condition)": ["burn"],
    "Same-type attack bonus": ["stab"], "Grounded": ["grounded"], "Double Battle": ["doubles", "spread_move"], "HP": ["hp_rounding"],
    "Dark (type)": ["dark_immunity"], "Grass (type)": ["powder_immunity"],  # "Speed"는 동음이의 안내 페이지라 제외(speed 태그는 Choice Scarf·Priority)
}

# 색인할 절: 소개 + 효과·전투 규칙 절. 규칙·도구 문서는 "In the core series games" 같은 큰 절(CONTAINER) 아래에 내용이 있어 하위 절로 판정한다.
KEEP = re.compile(r"effect|in battle|mechanic|generation ix|onward|champions|description|stat|calculation|overview|stages|battle properties", re.I)
CONTAINER = re.compile(r"in the core series games|in the games", re.I)
DROP = re.compile(r"outside of battle|in other games|spin-off|side series|in the anime|in animation|in the manga|in the tcg|trivia|in other languages|"
                  r"learnset|users|pokémon with|names|see also|external|references|related articles|price|acquisition|distribution|gallery|artwork|"
                  r"sprites|merchandise|bag item|flavor text|visual indicators|overworld|legends|dynamaxing|^pokémon$|pure |half |primary |secondary |"
                  r"exclusive|cram-o-matic|natural gift", re.I)


def effect_sections(extract):
    """소개(첫 절 이전) + KEEP·CONTAINER 절. DROP 절과 그 하위 절은 버린다."""
    parts = re.split(r"^(=+ .+? =+)$", extract, flags=re.M)
    out, keep, drop_below = [parts[0].strip()], False, None
    for i in range(1, len(parts), 2):
        head, body = parts[i], parts[i + 1]
        level, name = len(head) - len(head.lstrip("=")), head.strip("= ")
        if drop_below is not None and level > drop_below:
            continue  # 버린 절의 하위 절
        drop_below = None
        if level == 2:  # 최상위 절에서 유지 여부를 정한다
            keep = bool(CONTAINER.search(name)) or (bool(KEEP.search(name)) and not DROP.search(name))
        elif DROP.search(name):
            drop_below = level
            continue
        if keep and body.strip():
            out.append(f"{head}\n{body.strip()}")
    return "\n\n".join(x for x in out if x)


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    missing = []
    for i, (title, tags) in enumerate(RULE_PAGES.items(), 1):
        f = OUT / f"{slug(title)}.json"
        if f.exists():  # 이미 받은 문서는 원문 캐시로 색인용 본문만 다시 만든다
            rec = json.loads(f.read_text(encoding="utf-8"))
            rec["text"] = effect_sections(rec["full_text"])
            f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            continue
        p = fetch(title)
        full = p.get("extract", "") or ""
        rec = {"query_title": title, "title": p.get("title", title), "tags": tags,
               "url": "https://bulbapedia.bulbagarden.net/wiki/" + urllib.parse.quote(p.get("title", title).replace(" ", "_")),
               "revid": (p.get("revisions") or [{}])[0].get("revid"), "timestamp": (p.get("revisions") or [{}])[0].get("timestamp"),
               "collected_at": date.today().isoformat(), "missing": bool(p.get("missing")) or not full,
               "text": effect_sections(full), "full_text": full}
        f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        if rec["missing"]:
            missing.append(title)
        print(f"{i}/{len(RULE_PAGES)} {title} → {rec['title']} 색인용 {len(rec['text'])}자 / 원문 {len(full)}자{' (문서 없음)' if rec['missing'] else ''}", flush=True)
    print("문서 없음:", missing)


if __name__ == "__main__":
    main()
