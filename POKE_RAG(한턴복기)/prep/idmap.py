"""pokedb ID(DDDD-FF) → dex_no / form_key 매핑을 만들고 전 시즌 데이터로 검증한다. (agent.md 4절)
  .venv/Scripts/python -m prep.idmap
입력: data/raw/pokedb, data/raw/pokeapi, prep/id_overrides.json(보정표)
출력: data/processed/id_map.json, data/processed/id_map_report.md
"""
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from config import DATA_DIR, ROOT
from prep.collect import API, cached, trim_form

RAW = DATA_DIR / "raw"
OUT = DATA_DIR / "processed"
JA = ("ja", "ja-hrkt")


def load(kind, key):
    p = RAW / "pokeapi" / kind / f"{key}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def ja_names(d):
    return {d["names"][k] for k in JA if k in d["names"]}


def read_slots():
    """전 시즌 슬롯 → {pokedb_id: 첫 등장 슬롯}, {(id, 메가스톤 ja명)}"""
    first, stones = {}, set()
    for f in sorted((RAW / "pokedb").glob("*.json")):
        for t in json.loads(f.read_text(encoding="utf-8"))["teams"]:
            for m in t["team"]:
                if m["id"]:
                    first.setdefault(m["id"], m)
                    stones.add((m["id"], m["item"]))
    return first, stones


def main():
    cfg = json.loads((ROOT / "prep" / "id_overrides.json").read_text(encoding="utf-8"))
    overrides, form_ok = cfg["form_key"], cfg["form_ok"]
    types_ja = {n: t["name"] for t in (json.loads(p.read_text(encoding="utf-8")) for p in (RAW / "pokeapi" / "type").glob("*.json"))
                for n in ja_names(t)}
    first, stones = read_slots()
    id_map, problems = {}, []

    for pid, m in sorted(first.items()):
        dex, ff = int(pid[:4]), int(pid[5:])
        sp = next((s for s in (load("species", n) for n in _species_names(dex)) if s and s["id"] == dex), None)
        if sp is None:
            problems.append(f"{pid} {m['pokemon']}: species {dex} 없음")
            continue
        vs = [v["name"] for v in sp["varieties"]]
        key = overrides.get(pid) or (vs[ff] if ff < len(vs) else None)
        if key is None:
            problems.append(f"{pid} {m['pokemon']}: varieties[{ff}] 없음 (보정표 필요)")
            continue
        p = load("pokemon", key)
        if p is None:
            problems.append(f"{pid} {m['pokemon']}: pokemon/{key} 없음")
            continue
        errs = []
        if m["pokemon"] not in ja_names(sp):
            errs.append(f"종 이름 불일치 pokedb={m['pokemon']} api={sorted(ja_names(sp))}")
        if [types_ja.get(m["type1"])] + ([types_ja[m["type2"]]] if m["type2"] else []) != p["types"]:
            errs.append(f"타입 불일치 pokedb={m['type1']}/{m['type2']} api={p['types']}")
        form_ja = ""
        if m["form"] and ff:  # 폼 이름은 pokemon-form 리소스의 ja form_names로 대조 (FF=00은 기본 폼이라 생략)
            f = cached(RAW / "pokeapi" / "form" / f"{key}.json", f"{API}/pokemon-form/{key}", trim_form)
            form_ja = next((f["form_names"][k] for k in JA if k in (f or {}).get("form_names", {})), "")
            # pokedb가 "…のすがた・コンバットしゅ"처럼 더 자세히 쓰는 경우를 허용하고, 사람이 확인한 예외는 form_ok에 둔다
            if not (form_ja and m["form"].startswith(form_ja)) and pid not in form_ok:
                errs.append(f"폼 이름 불일치 pokedb={m['form']} api={form_ja or '없음'}")
        id_map[pid] = {"dex_no": dex, "form_key": key, "name_ja": m["pokemon"], "form_ja": m["form"],
                       "override": pid in overrides, "ok": not errs}
        problems += [f"{pid} {m['pokemon']}({key}): {e}" for e in errs]

    mega_map = _mega_map(stones, id_map, problems)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "id_map.json").write_text(json.dumps({"id_map": id_map, "mega_map": mega_map}, ensure_ascii=False, indent=1), encoding="utf-8")
    report = [f"# id_map 검증 보고", "", f"- pokedb 고유 ID {len(first)}개, 매핑 {len(id_map)}개, 검증 통과 {sum(v['ok'] for v in id_map.values())}개",
              f"- 보정표(form_key) 적용: {sorted(overrides)}, 사람이 확인한 폼 이름 예외(form_ok): {sorted(form_ok)}", f"- 메가스톤 매핑 {len(mega_map)}개", "", "## 문제 목록", ""]
    report += [f"- {p}" for p in problems] or ["- 없음"]
    (OUT / "id_map_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[:5]), "\n문제", len(problems))
    for p in problems:
        print(" -", p)


_SPECIES_BY_ID = {}


def _species_names(dex):
    if not _SPECIES_BY_ID:
        for p in (RAW / "pokeapi" / "species").glob("*.json"):
            _SPECIES_BY_ID.setdefault(json.loads(p.read_text(encoding="utf-8"))["id"], []).append(p.stem)
    return _SPECIES_BY_ID.get(dex, [])


def _mega_map(stones, id_map, problems):
    """메가스톤 도구(PokeAPI category=mega-stones)를 든 슬롯 → 메가 폼. 스톤 접미(-x/-y/-z)와 폼 접미를 맞춘다."""
    by_ja = {}
    for p in (RAW / "pokeapi" / "item").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d["category"] == "mega-stones":
            for n in ja_names(d):  # pokedb는 전각(Ｚ), PokeAPI는 반각(Z)을 섞어 쓰므로 NFKC로 맞춘다
                by_ja[unicodedata.normalize("NFKC", n)] = d["name"]
    out = {}
    for pid, item in sorted(stones):
        if unicodedata.normalize("NFKC", item) not in by_ja or pid not in id_map:
            continue
        key = by_ja[unicodedata.normalize("NFKC", item)]
        suffix = re.search(r"ite(-[xyz])?$", key)
        suffix = suffix.group(1) or "" if suffix else ""
        base = id_map[pid]["form_key"]
        sp = load("pokemon", base)["species"]
        megas = [v["name"] for v in load("species", sp)["varieties"] if "-mega" in v["name"]]
        hit = [v for v in megas if re.search(r"-mega(-[xyz])?$", v) and (re.search(r"-mega(-[xyz])?$", v).group(1) or "") == suffix]
        if len(hit) != 1:
            problems.append(f"{pid} {id_map[pid]['name_ja']} + {item}({key}): pokedb 원본 입력 오류 의심(해당 종의 메가 폼 후보 {megas}). 매핑 제외")
            continue
        out[item] = {"item_key": key, "base_form_key": base, "form_key": hit[0]}
    return out


if __name__ == "__main__":
    main()
