"""PokeAPI(챔피언스 범위) + pokedb 오픈데이터를 data/raw/ 아래에 JSON으로 선수집한다.

재실행하면 이미 받은 파일은 건너뛴다(캐시). 요청 간격 0.15초 이상, 실패 시 백오프 재시도.
  .venv/Scripts/python -m prep.collect  # 전체 (config.py가 .env를 읽으므로 venv의 python으로 실행)
  .venv/Scripts/python -m prep.collect pokedb    # pokedb만
  .venv/Scripts/python -m prep.collect pokeapi   # PokeAPI만
  .venv/Scripts/python -m prep.collect champions # champions-data(GitHub)만
"""
import http.client
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from config import REQUEST_INTERVAL, ROOT, USER_AGENT

DATA = ROOT / "data" / "raw"


UA = USER_AGENT
DELAY = REQUEST_INTERVAL
API = "https://pokeapi.co/api/v2"
POKEDB = "https://champs.pokedb.tokyo/opendata"
# CC BY 4.0, 최신 커밋(2026-04-16 v1.1.0)으로 고정해 재현 가능하게 한다
CHAMPIONS_DATA = "https://raw.githubusercontent.com/otterlyclueless/pokemon-champions-data/cb874a3040174314f67642f382143cc8a401122a"
CHAMPIONS_FILES = [
    "LICENSE", "README.md", "abilities/abilities.json", "items/items.json", "learnsets/learnsets.json",
    "mechanics/sp-system.md", "mechanics/stat-formula.md", "meta/version.json", "moves/moves.json",
    "natures/natures.json", "pokemon/base-stats.json", "pokemon/roster.json", "type-chart/effectiveness.json",
]


def get(url):
    for attempt in range(5):
        try:
            time.sleep(DELAY)
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:  # 읽기 중 타임아웃·연결 끊김·IncompleteRead 포함
            err = e
        time.sleep(2 ** attempt)
    raise RuntimeError(f"{url}: {err}")


def cached(path, url, trim=lambda d: d):
    """path가 있으면 읽고, 없으면 받아서 trim 후 저장. 404면 None."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    raw = get(url)
    if raw is None:
        return None
    data = trim(json.loads(raw))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def names(d):  # 제공되는 모든 언어 이름 {lang: name}
    return {n["language"]["name"]: n["name"] for n in d.get("names", [])}


def trim_pokemon(d):
    return {
        "id": d["id"], "name": d["name"], "species": d["species"]["name"], "is_default": d["is_default"],
        "types": [t["type"]["name"] for t in d["types"]],
        "stats": {s["stat"]["name"]: s["base_stat"] for s in d["stats"]},
        "abilities": [{"name": a["ability"]["name"], "hidden": a["is_hidden"]} for a in d["abilities"]],
        "height": d["height"], "weight": d["weight"],
        # 챔피언스에서 배우는 기술만
        "champions_moves": sorted(m["move"]["name"] for m in d["moves"]
                                  if any(v["version_group"]["name"] == "champions" for v in m["version_group_details"])),
    }


def trim_species(d):
    return {
        "id": d["id"], "name": d["name"], "names": names(d),
        "genus": {g["language"]["name"]: g["genus"] for g in d["genera"]},
        # 같은 언어 항목이 여러 개면 마지막(최신 버전)이 남는다
        "flavor": {f["language"]["name"]: " ".join(f["flavor_text"].split())
                   for f in d["flavor_text_entries"] if f["language"]["name"] in ("ko", "en")},
        "varieties": [{"name": v["pokemon"]["name"], "is_default": v["is_default"]} for v in d["varieties"]],
        "evolution_chain": d["evolution_chain"]["url"].rstrip("/").split("/")[-1],
    }


def trim_form(d):
    return {"name": d["name"], "form_name": d["form_name"], "names": {n["language"]["name"]: n["name"] for n in d["names"]},
            "form_names": {n["language"]["name"]: n["name"] for n in d["form_names"]}, "is_mega": d["is_mega"]}


def trim_move(d):
    return {
        "name": d["name"], "names": names(d), "type": d["type"]["name"], "category": d["damage_class"]["name"],
        "power": d["power"], "accuracy": d["accuracy"], "pp": d["pp"], "priority": d["priority"],
        "target": d["target"]["name"],
        "effect": {e["language"]["name"]: e["short_effect"] for e in d["effect_entries"] if e["language"]["name"] == "en"},
        "effect_chance": d["effect_chance"],
        "flavor": {f["language"]["name"]: f["flavor_text"].replace("\n", " ")
                   for f in d["flavor_text_entries"] if f["language"]["name"] in ("ko", "en")},
    }


def trim_ability(d):
    return {
        "name": d["name"], "names": names(d),
        "effect": {e["language"]["name"]: e["short_effect"] for e in d["effect_entries"] if e["language"]["name"] == "en"},
        "flavor": {f["language"]["name"]: f["flavor_text"].replace("\n", " ")
                   for f in d["flavor_text_entries"] if f["language"]["name"] in ("ko", "en")},
    }


def trim_item(d):
    return {
        "name": d["name"], "names": names(d), "category": (d.get("category") or {}).get("name"), "cost": d.get("cost"),
        "attributes": [a["name"] for a in d["attributes"]],
        "effect": {e["language"]["name"]: e["short_effect"] for e in d["effect_entries"]},
        "flavor": {f["language"]["name"]: " ".join(f["text"].split()) for f in d["flavor_text_entries"]
                   if f["language"]["name"] in ("ko", "ja", "en")},
    }


def trim_nature(d):
    return {"name": d["name"], "names": names(d),
            "plus": (d["increased_stat"] or {}).get("name"), "minus": (d["decreased_stat"] or {}).get("name")}


def trim_type(d):
    r = d["damage_relations"]
    return {"name": d["name"], "names": names(d),
            "double_to": [t["name"] for t in r["double_damage_to"]],
            "half_to": [t["name"] for t in r["half_damage_to"]],
            "zero_to": [t["name"] for t in r["no_damage_to"]]}


def pokeapi():
    out = DATA / "pokeapi"
    dex = cached(out / "pokedex_champions.json", f"{API}/pokedex/champions")
    species_names = [e["pokemon_species"]["name"] for e in dex["pokemon_entries"]]
    print(f"champions 도감 {len(species_names)}종")

    # 종(species)은 전 범위: Bulbapedia 검색 시 다국어 이름 번역용
    every = cached(out / "species_list.json", f"{API}/pokemon-species?limit=5000")["results"]
    for i, e in enumerate(every, 1):
        cached(out / "species" / f"{e['name']}.json", e["url"], trim_species)
        if i % 100 == 0:
            print(f"  species {i}/{len(every)}")

    # 포켓몬·폼(종족값·습득기)은 챔피언스 도감만
    moves, abilities = set(), set()
    for sp in species_names:
        s = cached(out / "species" / f"{sp}.json", f"{API}/pokemon-species/{sp}", trim_species)
        for v in s["varieties"]:
            p = cached(out / "pokemon" / f"{v['name']}.json", f"{API}/pokemon/{v['name']}", trim_pokemon)
            if p is None:
                continue
            cached(out / "form" / f"{v['name']}.json", f"{API}/pokemon-form/{v['name']}", trim_form)
            moves.update(p["champions_moves"])
            abilities.update(a["name"] for a in p["abilities"])

    for kind, keys, trim in (("move", moves, trim_move), ("ability", abilities, trim_ability)):
        for k in sorted(keys):
            cached(out / kind / f"{k}.json", f"{API}/{kind}/{k}", trim)
        print(f"{kind} {len(keys)}개")

    items = cached(out / "item_list.json", f"{API}/item?limit=5000")["results"]
    for i, e in enumerate(items, 1):
        cached(out / "item" / f"{e['name']}.json", e["url"], trim_item)
        if i % 200 == 0:
            print(f"  item {i}/{len(items)}")
    print(f"item {len(items)}개")

    for kind, trim in (("nature", trim_nature), ("type", trim_type)):
        listing = cached(out / f"{kind}_list.json", f"{API}/{kind}?limit=100")
        for e in listing["results"]:
            if kind == "type" and e["name"] in ("unknown", "shadow", "stellar"):
                continue
            cached(out / kind / f"{e['name']}.json", e["url"], trim)
        print(f"{kind} 완료")


def champions_data():
    out = DATA / "champions_data"
    for f in CHAMPIONS_FILES:
        if not (out / f).exists():
            url = f"{CHAMPIONS_DATA}/{f}"
            raw = get(url)
            if raw is None:
                raise RuntimeError(f"champions-data 파일 없음(404): {url}")
            (out / f).parent.mkdir(parents=True, exist_ok=True)
            (out / f).write_bytes(raw)
            print(f"champions_data {f}")


def pokedb():
    out = DATA / "pokedb"
    out.mkdir(parents=True, exist_ok=True)
    for season in range(1, 100):
        found = False
        for rule in ("single", "double"):
            name = f"s{season}_{rule}_ranked_teams.json"
            if cached(out / name, f"{POKEDB}/{name}") is not None:
                found = True
                print(f"pokedb {name}")
        if not found:  # 시즌 번호는 연속이므로 첫 빈 시즌에서 종료
            break


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "pokedb"):
        pokedb()
    if which in ("all", "champions"):
        champions_data()
    if which in ("all", "pokeapi"):
        pokeapi()
