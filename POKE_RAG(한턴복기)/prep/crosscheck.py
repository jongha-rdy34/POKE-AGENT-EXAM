"""champions-data(Serebii·Showdown 기반, 2026-04-16)와 PokeAPI의 챔피언스 데이터를 교차검증한다.
  .venv/Scripts/python -m prep.crosscheck
출력: data/processed/crosscheck.json(기계용), data/processed/crosscheck_report.md(사람용)
"""
import json
import re

from config import DATA_DIR

RAW, OUT = DATA_DIR / "raw", DATA_DIR / "processed"
STAT_KEYS = (("hp", "hp"), ("atk", "attack"), ("def", "defense"), ("spa", "special-attack"), ("spd", "special-defense"), ("spe", "speed"))


def jload(p):
    return json.loads(p.read_text(encoding="utf-8"))


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def tokens(s):
    return set(re.findall(r"[a-z0-9]+", s.lower())) - {"base", "form", "forme", "mode", "breed", "cloak", "size"}


def main():
    cd = RAW / "champions_data"
    pokemon = {p.stem: jload(p) for p in (RAW / "pokeapi" / "pokemon").glob("*.json")}
    by_dex = {}
    for k, p in pokemon.items():
        by_dex.setdefault(jload(RAW / "pokeapi" / "species" / f"{p['species']}.json")["id"], []).append(k)

    # 1) 포켓몬: (도감번호, 종족값) 일치로 짝짓기
    res = {"pokemon": {"matched": 0, "stat_diff": [], "unmatched": [], "ambiguous": []}}
    match = {}  # champions-data 이름 → PokeAPI form_key
    for e, st in zip(jload(cd / "pokemon" / "roster.json"), jload(cd / "pokemon" / "base-stats.json")):
        assert e["name"] == st["name"]
        cand = by_dex.get(e["dexNumber"], [])
        want = tuple(st[a] for a, _ in STAT_KEYS)
        same = [k for k in cand if tuple(pokemon[k]["stats"][b] for _, b in STAT_KEYS) == want]
        if len(same) > 1:  # 종족값이 같은 폼(로토무·켄타로스 등)은 이름 토큰으로 가린다
            tk = tokens(e["name"]) - {"mega", "alolan", "galarian", "hisuian", "paldean"} | ({"mega"} & tokens(e["name"]))
            narrowed = [k for k in same if tk <= tokens(k) | {"alolan", "galarian", "hisuian", "paldean"}]
            same = narrowed or same
        defaults = [k for k in same if pokemon[k]["is_default"]]  # 종 기본 폼(gmax·totem 등 파생 폼보다 우선). aegislash-shield처럼 키≠종 이름인 경우도 포함
        if len(same) > 1 and len(defaults) == 1 and tokens(e["name"]) <= tokens(defaults[0]) | {"base"}:
            same = defaults
        if len(same) == 1:
            match[e["name"]] = same[0]
            res["pokemon"]["matched"] += 1
        elif len(same) > 1:
            res["pokemon"]["ambiguous"].append({"name": e["name"], "candidates": same})
        else:  # 종족값이 다르거나 폼이 없다 → 이름 토큰이 가장 많이 겹치는 폼과 종족값 차이를 기록
            best = max(cand, key=lambda k: len(tokens(e["name"]) & tokens(k)), default=None)
            if best and tokens(best) >= tokens(e["name"]) - {"base", "alolan", "galarian", "hisuian", "paldean"}:
                diff = {a: [st[a], pokemon[best]["stats"][b]] for a, b in STAT_KEYS if st[a] != pokemon[best]["stats"][b]}
                res["pokemon"]["stat_diff"].append({"name": e["name"], "form_key": best, "diff(cd,api)": diff})
            else:
                res["pokemon"]["unmatched"].append({"name": e["name"], "dex": e["dexNumber"], "api_candidates": cand})

    # 2) 기술: 영문 이름 정규화로 대응. champions-data에서 inChampions=true만 대상
    api_moves = {norm(m["names"]["en"]): m for m in (jload(p) for p in (RAW / "pokeapi" / "move").glob("*.json"))}
    cd_moves = {norm(m["name"]): m for m in jload(cd / "moves" / "moves.json")}
    in_champ = {k: m for k, m in cd_moves.items() if m["inChampions"]}
    api_learn = {mv for p in pokemon.values() for mv in p["champions_moves"]}
    api_learn_n = {norm(api_m["names"]["en"]) for api_m in api_moves.values() if api_m["name"] in api_learn}
    diffs = []
    for k, m in in_champ.items():
        a = api_moves.get(k)
        if a is None:
            continue
        # 변화기의 위력은 champions-data가 0, PokeAPI가 null이다 → 같은 값으로 본다
        cdv = {**m, "power": m.get("power") or None, "accuracy": m.get("accuracy") or None, "type": m["type"].lower()}
        av = {**a, "power": a["power"] or None, "accuracy": a["accuracy"] or None}
        d = {f: [cdv.get(f), av[f]] for f in ("power", "accuracy", "pp", "priority", "type") if cdv.get(f) != av[f]}
        if d:
            diffs.append({"move": m["name"], "diff(cd,api)": d})
    res["moves"] = {
        "cd_in_champions": len(in_champ), "api_champions_learnable": len(api_learn_n),
        "only_cd": sorted(in_champ[k]["name"] for k in in_champ if k not in api_learn_n),
        "only_api": sorted(api_moves[k]["names"]["en"] for k in api_learn_n if k not in in_champ),
        "cd_missing_in_api_data": sorted(in_champ[k]["name"] for k in in_champ if k not in api_moves),
        "field_diffs": diffs,
        "field_diff_counts": {f: sum(f in x["diff(cd,api)"] for x in diffs) for f in ("power", "accuracy", "pp", "priority", "type")},
    }

    # 3) 습득기: 짝지어진 폼별 차이 (PokeAPI 습득기가 빈 폼은 champions-data로 보충 후보)
    ls = jload(cd / "learnsets" / "learnsets.json")
    key2en = {m["name"]: k for k, m in api_moves.items()}  # 기술 키 → 정규화 영문명 (습득기에만 있고 기술 파일이 없으면 키를 정규화)
    empty_api, learn_diff = [], []
    for name, key in match.items():
        cdset = {norm(m["name"]) for m in ls.get(name, {}).get("moves", [])}
        apiset = {key2en.get(x, norm(x)) for x in pokemon[key]["champions_moves"]}
        if not apiset:
            empty_api.append({"form_key": key, "cd_name": name, "cd_move_count": len(cdset)})
        elif cdset != apiset:
            learn_diff.append({"form_key": key, "only_cd": sorted(cdset - apiset), "only_api": sorted(apiset - cdset)})
    # cd 습득기는 Psychic·Grassy Terrain이 통째로 빠져 있다(Alakazam 등). 그 한 가지만 다른 폼을 따로 센다
    cd_gap = {"psychic", "grassyterrain"}
    cat = {"cd_gap_only": [x for x in learn_diff if not x["only_cd"] and set(x["only_api"]) <= cd_gap],
           "cd_superset": [x for x in learn_diff if x["only_cd"] and not x["only_api"]],
           "api_superset": [x for x in learn_diff if x["only_api"] and not x["only_cd"] and not set(x["only_api"]) <= cd_gap],
           "both_differ": [x for x in learn_diff if x["only_cd"] and x["only_api"]]}
    res["cd_name_to_form_keys"] = {n: [k] for n, k in match.items()} | {x["name"]: x["candidates"] for x in res["pokemon"]["ambiguous"]}
    res["learnsets"] = {"api_empty_fillable_from_cd": empty_api, "differs": learn_diff, "categories": {k: len(v) for k, v in cat.items()},
                        "category_forms": {k: [x["form_key"] for x in v] for k, v in cat.items()}}

    # 4) 두 출처 모두 습득기가 없는 종: PokeAPI 챔피언스 도감 종 중 champions-data에 없고 PokeAPI 습득기도 빈 기본 폼
    cd_dex = {e["dexNumber"] for e in jload(cd / "pokemon" / "roster.json")}
    seen = {int(m["id"][:4]) for f in (RAW / "pokedb").glob("*.json") for t in jload(f)["teams"] for m in t["team"] if m["id"]}
    dex = [e["pokemon_species"]["name"] for e in jload(RAW / "pokeapi" / "pokedex_champions.json")["pokemon_entries"]]
    default_form = {p["species"]: p for p in pokemon.values() if p["is_default"]}  # 종 이름 → 기본 폼 (maushold-family-of-four 등)
    gap = []
    for sp in dex:
        sid = jload(RAW / "pokeapi" / "species" / f"{sp}.json")["id"]
        if sid not in cd_dex and sp in default_form and not default_form[sp]["champions_moves"]:
            gap.append({"species": sp, "dex_no": sid, "seen_in_pokedb": sid in seen})
    res["no_learnset_anywhere"] = gap
    res["api_dex_species_not_in_cd"] = sum(1 for sp in dex if jload(RAW / "pokeapi" / "species" / f"{sp}.json")["id"] not in cd_dex)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "crosscheck.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "crosscheck_report.md").write_text(report(res), encoding="utf-8")
    print(report(res)[:3000])


def report(r):
    p, m, l = r["pokemon"], r["moves"], r["learnsets"]
    L = ["# champions-data ↔ PokeAPI 교차검증 보고", "",
         "- champions-data: v1.1.0 (2026-04-16, Serebii·Showdown 기반). PokeAPI: 2026-10-21 수집", "",
         "## 1. 포켓몬 종족값", f"- 짝지어진 폼 {p['matched']}개 (도감번호+종족값 일치)",
         f"- 종족값 차이 {len(p['stat_diff'])}건, 짝 없음 {len(p['unmatched'])}건, 모호 {len(p['ambiguous'])}건", ""]
    L += [f"- 차이: `{x['name']}` ↔ `{x['form_key']}` {x['diff(cd,api)']}" for x in p["stat_diff"]]
    L += [f"- 짝 없음: `{x['name']}` (dex {x['dex']}) PokeAPI 후보 {x['api_candidates']}" for x in p["unmatched"]]
    L += [f"- 모호: `{x['name']}` 후보 {x['candidates']}" for x in p["ambiguous"]]
    L += ["", "## 2. 기술", f"- champions-data 챔피언스 기술 {m['cd_in_champions']}개, PokeAPI 챔피언스 습득 기술 {m['api_champions_learnable']}개",
          f"- champions-data에만 있음 {len(m['only_cd'])}개: {m['only_cd']}", f"- PokeAPI에만 있음 {len(m['only_api'])}개: {m['only_api']}",
          f"- champions-data 기술 중 PokeAPI 기술 데이터에 이름이 없음: {m['cd_missing_in_api_data']}",
          f"- 위력·명중·PP·우선도·타입 차이 {len(m['field_diffs'])}개 기술, 필드별 {m['field_diff_counts']}", ""]
    L += ["- **데이터 우선순위(사용자 지정): PokeAPI·pokedb가 항상 우선, champions-data는 구버전(2026-04)이라 PokeAPI에 값이 없을 때만 보충한다.** 아래 차이는 모두 PokeAPI 값을 채택한다.",
          "- PP는 거의 전부 다르다(예: PokeAPI 10 / champions-data 12, 15/16, 5/8). PokeAPI 값을 쓰되, 위키 `/Champions 기술`에서 챔피언스 PP가 본가와 다른 사례가 확인된 바 있어 PokeAPI PP가 본가 값일 위험이 있다(agent.md 10절 미결 사항).",
          "- 위력·명중이 다른 기술(champions-data 쪽이 구버전이므로 PokeAPI 값 채택, 참고용 목록):"]
    L += [f"  - `{x['move']}` {x['diff(cd,api)']}" for x in m["field_diffs"] if set(x["diff(cd,api)"]) - {"pp"}]
    L += ["", "## 3. 습득기", f"- PokeAPI 습득기가 비어 champions-data로 보충 가능한 폼 {len(l['api_empty_fillable_from_cd'])}개",
          *[f"  - `{x['form_key']}` (cd `{x['cd_name']}` {x['cd_move_count']}기)" for x in l["api_empty_fillable_from_cd"]],
          f"- 두 출처 습득기가 다른 폼 {len(l['differs'])}개: {l['categories']}",
          "  - `cd_gap_only`: champions-data에 Psychic/Grassy Terrain이 빠진 것뿐", "  - `cd_superset`: champions-data에만 있는 기술이 있음(구버전이라 채택하지 않음)",
          "- 결론: 습득기는 **PokeAPI만** 쓴다. PokeAPI 습득기가 비어 있는 폼에 한해서만 champions-data로 보충하고 출처를 `cd`로 표시한다.", ""]
    L += [f"  - `{x['form_key']}` cd만 {x['only_cd']} / api만 {x['only_api']}" for x in l["differs"] if x["form_key"] in set(l["category_forms"]["api_superset"] + l["category_forms"]["both_differ"])]
    g = r["no_learnset_anywhere"]
    L += ["", "## 4. 두 출처 모두 습득기가 없는 종",
          f"- PokeAPI 챔피언스 도감 종 중 champions-data(2026-04 판)에 없는 종 {r['api_dex_species_not_in_cd']}개 — 게임 업데이트로 추가된 포켓몬으로 추정",
          f"- 그중 PokeAPI 습득기도 빈 종 {len(g)}개 (pokedb에 실제 등장: {sum(x['seen_in_pokedb'] for x in g)}개): "
          + ", ".join(f"{x['species']}{'*' if x['seen_in_pokedb'] else ''}" for x in g) + "  (*=pokedb 등장)",
          "- 이 종들의 습득기는 현재 데이터로는 알 수 없다. 후속: Bulbapedia 포켓몬 문서 선수집(2단계)에서 보충하거나, 습득기 없음을 답변에 명시."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
