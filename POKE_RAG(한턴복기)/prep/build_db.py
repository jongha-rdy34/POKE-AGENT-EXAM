"""data/raw + data/processed(id_map, crosscheck) → 구조화 저장소 data/processed/pokedex.sqlite (agent.md 5.1절)
  .venv/Scripts/python -m prep.build_db
우선순위: PokeAPI·pokedb가 항상 우선. champions-data는 PokeAPI 습득기가 빈 폼에만 보충하고 source='cd'로 표시한다.
"""
import json
import os
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict

from config import DATA_DIR, DB_PATH as DB

RAW, OUT = DATA_DIR / "raw", DATA_DIR / "processed"
JA = ("ja", "ja-hrkt")
STATS = {"hp": "hp", "attack": "atk", "defense": "def", "special-attack": "spa", "special-defense": "spd", "speed": "spe"}

SCHEMA = """
CREATE TABLE pokemon(form_key TEXT PRIMARY KEY, dex_no INT, species TEXT, name_ko, name_ja, name_en, type1, type2,
  hp INT, atk INT, def INT, spa INT, spd INT, spe INT, ability1, ability2, hidden_ability, height INT, weight INT,
  is_mega INT, is_default INT, in_champions INT, genus_ko, flavor_ko, evolution_chain);
CREATE TABLE move(move_key TEXT PRIMARY KEY, name_ko, name_ja, name_en, type, category, power INT, accuracy INT, pp INT,
  priority INT, target, effect_chance INT, effect_en, flavor_ko, flavor_en, in_champions INT);
CREATE TABLE learnset(form_key, move_key, source, PRIMARY KEY(form_key, move_key));
CREATE TABLE nature(key TEXT PRIMARY KEY, name_ko, name_ja, name_en, plus, minus);
CREATE TABLE ability(key TEXT PRIMARY KEY, name_ko, name_ja, name_en, effect_en, flavor_ko, flavor_en);
CREATE TABLE item(key TEXT PRIMARY KEY, name_ko, name_ja, name_en, category, cost INT, attributes, effect_en, flavor_ko, flavor_en, is_mega_stone INT);
CREATE TABLE type_chart(atk_type, def_type, mult REAL, PRIMARY KEY(atk_type, def_type));
CREATE TABLE id_map(pokedb_id TEXT PRIMARY KEY, dex_no INT, form_key, name_ja, form_ja);
CREATE TABLE mega_map(item_ja TEXT PRIMARY KEY, item_key, base_form_key, form_key);
CREATE TABLE alias(alias TEXT, kind, target_key, note, PRIMARY KEY(alias, kind, target_key));
CREATE TABLE meta_usage(season, rule, form_key, teams INT, total_teams INT, usage_rate REAL, top_items, top_teammates, top_tera,
  PRIMARY KEY(season, rule, form_key));
"""


def jload(p):
    return json.loads(p.read_text(encoding="utf-8"))


def files(kind):
    return [jload(p) for p in sorted((RAW / "pokeapi" / kind).glob("*.json"))]


def pick(names, *langs):
    return next((names[k] for k in langs if names.get(k)), None)


def label(species_names, form, lang):
    """종 이름 + 폼 표기. 폼 이름에 종 이름이 이미 들어 있으면(메가한카리아스) 그대로 쓴다."""
    base = pick(species_names, *({"ko": ("ko",), "ja": JA, "en": ("en",)}[lang]))
    if not form:
        return base
    names = form["names"].get(lang) or pick(form["form_names"], *({"ko": ("ko",), "ja": JA, "en": ("en",)}[lang]))
    if not names:  # 해당 언어 폼 이름이 PokeAPI에 없으면 영문 폼 이름으로 구분한다(이름을 지어내지 않는다)
        names = form["names"].get("en") or form["form_names"].get("en")
    if not names:
        return base
    return names if base and base in names else f"{base} ({names})"


def main():
    """임시 파일에 끝까지 빌드한 뒤에만 DB를 교체한다. 중간에 실패하면 기존 DB가 그대로 남는다."""
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = DB.with_suffix(".building")
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    try:
        build(db)
    finally:
        db.close()
    os.replace(tmp, DB)  # Windows에서 다른 프로세스가 DB를 열고 있으면 여기서 PermissionError → 기존 DB 유지
    print("교체 완료:", DB)


def build(db):
    db.executescript(SCHEMA)
    idm = jload(OUT / "id_map.json")
    cc = jload(OUT / "crosscheck.json")
    mapped = {v["form_key"] for v in idm["id_map"].values()} | {v["form_key"] for v in idm["mega_map"].values()}

    # --- 습득기 (PokeAPI) + move 이름 사전
    moves = {m["name"]: m for m in files("move")}
    en2key = {re.sub(r"[^a-z0-9]", "", m["names"]["en"].lower()): k for k, m in moves.items()}
    pokes = {p["name"]: p for p in files("pokemon")}
    for k, p in pokes.items():
        db.executemany("INSERT INTO learnset VALUES(?,?,?)", [(k, m, "api") for m in p["champions_moves"]])
    # champions-data는 PokeAPI 습득기가 빈 폼에만 보충
    cd = jload(RAW / "champions_data" / "learnsets" / "learnsets.json")
    filled, skipped = [], Counter()
    for name, keys in cc["cd_name_to_form_keys"].items():
        for k in keys:
            if k in pokes and not pokes[k]["champions_moves"] and name in cd and (pokes[k]["is_default"] or k in mapped):  # totem 등 파생 폼 제외
                for mv in cd[name]["moves"]:
                    mk = en2key.get(re.sub(r"[^a-z0-9]", "", mv["name"].lower()))
                    if mk:
                        db.execute("INSERT OR IGNORE INTO learnset VALUES(?,?,?)", (k, mk, "cd"))
                    else:
                        skipped[k] += 1
                filled.append(k)
    in_champ_moves = {r[0] for r in db.execute("SELECT DISTINCT move_key FROM learnset")}

    # --- pokemon
    species = {s["name"]: s for s in files("species")}
    for k, p in pokes.items():
        sp = species[p["species"]]
        form = (RAW / "pokeapi" / "form" / f"{k}.json")
        form = jload(form) if form.exists() else None
        st = {STATS[a]: v for a, v in p["stats"].items()}
        ab = [a["name"] for a in p["abilities"] if not a["hidden"]]
        hid = next((a["name"] for a in p["abilities"] if a["hidden"]), None)
        in_ch = int(bool(p["champions_moves"]) or k in mapped)
        db.execute("INSERT INTO pokemon VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            k, sp["id"], p["species"], label(sp["names"], form, "ko"), label(sp["names"], form, "ja"), label(sp["names"], form, "en"),
            p["types"][0], p["types"][1] if len(p["types"]) > 1 else None, st["hp"], st["atk"], st["def"], st["spa"], st["spd"], st["spe"],
            ab[0] if ab else None, ab[1] if len(ab) > 1 else None, hid, p["height"], p["weight"], int("-mega" in k), int(p["is_default"]),
            in_ch, sp["genus"].get("ko"), sp["flavor"].get("ko"), sp["evolution_chain"]))

    # --- move / nature / ability / item / type_chart
    for k, m in moves.items():
        n = m["names"]
        db.execute("INSERT INTO move VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            k, n.get("ko"), pick(n, *JA), n.get("en"), m["type"], m["category"], m["power"], m["accuracy"], m["pp"], m["priority"],
            m["target"], m["effect_chance"], m["effect"].get("en"), m["flavor"].get("ko"), m["flavor"].get("en"), int(k in in_champ_moves)))
    for x in files("nature"):
        n = x["names"]
        db.execute("INSERT INTO nature VALUES(?,?,?,?,?,?)", (x["name"], n.get("ko"), pick(n, *JA), n.get("en"), x["plus"], x["minus"]))
    for x in files("ability"):
        n = x["names"]
        db.execute("INSERT INTO ability VALUES(?,?,?,?,?,?,?)", (x["name"], n.get("ko"), pick(n, *JA), n.get("en"), x["effect"].get("en"),
                                                                 x["flavor"].get("ko"), x["flavor"].get("en")))
    for x in files("item"):
        n = x["names"]
        db.execute("INSERT INTO item VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
            x["name"], n.get("ko"), pick(n, *JA), n.get("en"), x["category"], x["cost"], json.dumps(x["attributes"]), x["effect"].get("en"),
            x["flavor"].get("ko"), x["flavor"].get("en"), int(x["category"] == "mega-stones")))
    types = files("type")
    names = [t["name"] for t in types]
    for t in types:
        for d in names:
            mult = 2.0 if d in t["double_to"] else 0.5 if d in t["half_to"] else 0.0 if d in t["zero_to"] else 1.0
            db.execute("INSERT INTO type_chart VALUES(?,?,?)", (t["name"], d, mult))

    # --- id_map / mega_map
    db.executemany("INSERT INTO id_map VALUES(?,?,?,?,?)", [(i, v["dex_no"], v["form_key"], v["name_ja"], v["form_ja"]) for i, v in idm["id_map"].items()])
    db.executemany("INSERT INTO mega_map VALUES(?,?,?,?)", [(i, v["item_key"], v["base_form_key"], v["form_key"]) for i, v in idm["mega_map"].items()])

    # --- meta_usage (pokedb 상위 구축 데이터: 팀 수 대비 채용 팀 비율)
    item_ja, unmapped = {}, Counter()
    for x in files("item"):
        for lang in JA:
            if lang in x["names"]:
                item_ja.setdefault(unicodedata.normalize("NFKC", x["names"][lang]), x["name"])
    for f in sorted((RAW / "pokedb").glob("*.json")):
        d = jload(f)
        rule = "single" if d["rule"] == "シングル" else "double"
        cnt, items, mates, tera = Counter(), defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
        for t in d["teams"]:
            keys = []
            for m in t["team"]:
                if not m["id"]:
                    continue
                if m["id"] not in idm["id_map"]:  # idmap이 매핑하지 못한 ID(새 폼 등)는 건너뛰고 끝에 보고한다
                    unmapped[m["id"]] += 1
                    continue
                key = idm["id_map"][m["id"]]["form_key"]
                mega = idm["mega_map"].get(m["item"])
                if mega and mega["base_form_key"] == key:
                    key = mega["form_key"]
                keys.append(key)
                items[key][item_ja.get(unicodedata.normalize("NFKC", m["item"]), m["item"])] += 1
                if m["terastal"]:
                    tera[key][m["terastal"]] += 1
            for k in set(keys):
                cnt[k] += 1
                mates[k].update(sorted(set(keys) - {k}))  # 정렬해서 넣어야 동률 순위가 실행마다 같다
        total = len(d["teams"])
        for k, c in cnt.items():
            db.execute("INSERT INTO meta_usage VALUES(?,?,?,?,?,?,?,?,?)", (
                d["season"], rule, k, c, total, round(c / total, 4), json.dumps(items[k].most_common(), ensure_ascii=False),  # 도구는 전체 분포(복기 후보, D24)
                json.dumps(mates[k].most_common(5), ensure_ascii=False), json.dumps(tera[k].most_common(3), ensure_ascii=False)))
    db.commit()
    from prep.alias import build as build_alias
    print("alias:", build_alias(db))
    from prep.smogon import load_into as load_smogon  # 성격·SP·특성 보충(agent.md 1.3절 4). 원본이 없으면 빈 테이블
    n_smogon, smogon_unmapped = load_smogon(db)  # build() 아래쪽의 unmapped(pokedb ID 경고)와 이름이 겹치지 않게 한다
    db.commit()
    print("smogon_usage:", n_smogon, "| 대응 못 한 Showdown 이름:", sorted(set(smogon_unmapped)))
    from prep.champions_items import load_into as load_champion_items  # 챔피언스 도구 목록(Bulbapedia·Showdown 대조)
    n_items, item_warn = load_champion_items(db)
    db.commit()
    print("champion_item:", n_items, *(f"| 경고: {w}" for w in item_warn))

    print("cd로 습득기 보충한 폼:", filled, "| 매칭 실패 기술 수:", dict(skipped))
    if unmapped:
        print("경고: id_map에 없어 meta_usage에서 뺀 pokedb ID(등장 횟수):", dict(unmapped), "→ prep.idmap 보정표(id_overrides.json) 확인")
    for t in ("pokemon", "move", "learnset", "nature", "ability", "item", "type_chart", "id_map", "mega_map", "meta_usage"):
        print(f"{t:11}", db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    print("in_champions 포켓몬:", db.execute("SELECT COUNT(*) FROM pokemon WHERE in_champions=1").fetchone()[0])


if __name__ == "__main__":
    main()
