"""Smogon 월간 사용 통계(Pokémon Showdown 래더)를 받아 smogon_usage 테이블로 넣는다(agent.md 1.3절 4: 성격·SP 배분·특성 보충 전용).
  .venv/Scripts/python -m prep.smogon      # 다운로드만(이미 있으면 건너뜀)
build_db가 load_into(db)를 호출해 테이블을 만든다. 출처: https://www.smogon.com/stats/ (월 1회 공개, 공식 API 없음)
"""
import json
import re
import urllib.request

import config

RAW = config.DATA_DIR / "raw" / "smogon"


def raw_path(month=None, fmt=None, cutoff=None):
    month, fmt, cutoff = month or config.SMOGON_MONTH, fmt or config.SMOGON_FORMAT, cutoff or config.SMOGON_CUTOFF
    return RAW / f"{month}_{fmt}-{cutoff}.json", f"https://www.smogon.com/stats/{month}/chaos/{fmt}-{cutoff}.json"


def download():
    path, url = raw_path()
    if path.exists():
        return path
    RAW.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT}), timeout=60) as r:
        path.write_bytes(r.read())
    return path


def form_key(db, name, keys):
    """Showdown 이름 → PokeAPI form_key. 규칙: 소문자·하이픈, 종 이름만 있으면 기본 폼, -F/-M → -female/-male, 팔데아 켄타로스 → -breed."""
    k = name.lower().replace(" ", "-").replace(".", "").replace("'", "").replace(":", "")
    if k in keys:
        return k
    parts = k.split("-")
    parts = ["female" if p == "f" else "male" if p == "m" else p for p in parts]
    for cand in ("-".join(parts), "-".join(parts) + "-breed"):
        if cand in keys:
            return cand
    row = db.execute("SELECT form_key FROM pokemon WHERE species=? AND is_default=1", (k,)).fetchone()
    return row[0] if row else None


# Showdown 도구·특성 ID → PokeAPI 키. 기본 규칙은 PokeAPI 키에서 영숫자 외 문자를 뺀 값과 일치(choice-scarf → choicescarf, 충돌 0건 확인).
ID_EXCEPTIONS = {"nothing": "", "leek": "stick", "": ""}  # 도구 없음 / 대파(PokeAPI 옛 키) / 빈 기술 칸


def showdown_id(key):
    return re.sub(r"[^a-z0-9]", "", key.lower())


def key_index(db, table, col="key"):
    return {showdown_id(k): k for (k,) in db.execute(f"SELECT {col} FROM {table}")}


def to_pokeapi(pairs, index):
    """[(Showdown ID, 가중치)] → ([(PokeAPI 키, 가중치)], 대응 못 한 ID 목록). 같은 키로 모이면 가중치를 합친다."""
    out, missing = {}, []
    for sid, w in pairs:
        k = ID_EXCEPTIONS.get(sid, index.get(sid))
        if k is None:
            missing.append(sid)
            k = f"showdown:{sid}"  # 버리지 않고 표시해 둔다
        out[k] = out.get(k, 0) + w
    return sorted(out.items(), key=lambda x: -x[1]), missing


def load_into(db):
    """smogon_usage 테이블을 다시 만든다. 도구·특성·기술은 PokeAPI 키로 바꿔 저장한다(대응 실패는 'showdown:<id>'로 남김).
    반환: (넣은 행 수, 대응 못 한 이름 목록 — 포켓몬명 또는 'item:'/'ability:'/'move:' 접두사). 원본이 없으면 (0, [])."""
    path, url = raw_path()
    db.execute("DROP TABLE IF EXISTS smogon_usage")
    db.execute("CREATE TABLE smogon_usage(month, format, cutoff INT, form_key, showdown_name, raw_count INT, usage REAL, "
               "abilities, items, spreads, moves, teammates, source_url)")
    if not path.exists():
        return 0, []
    d = json.loads(path.read_text(encoding="utf-8"))
    keys = {r[0] for r in db.execute("SELECT form_key FROM pokemon")}
    items_idx, abil_idx, move_idx = key_index(db, "item"), key_index(db, "ability"), key_index(db, "move", "move_key")
    top = lambda m: json.dumps(sorted(m.items(), key=lambda x: -x[1]), ensure_ascii=False)  # 가중치 큰 순
    rows, unmapped = [], []
    for name, v in d["data"].items():
        fk = form_key(db, name, keys)
        if fk is None:
            unmapped.append(name)
            continue
        items, miss_i = to_pokeapi(v.get("Items", {}).items(), items_idx)
        abilities, miss_a = to_pokeapi(v.get("Abilities", {}).items(), abil_idx)
        moves, miss_m = to_pokeapi(v.get("Moves", {}).items(), move_idx)
        unmapped += [f"item:{x}" for x in miss_i] + [f"ability:{x}" for x in miss_a] + [f"move:{x}" for x in miss_m]
        rows.append((config.SMOGON_MONTH, config.SMOGON_FORMAT, config.SMOGON_CUTOFF, fk, name, v.get("Raw count", 0), v.get("usage", 0),
                     json.dumps(abilities, ensure_ascii=False), json.dumps(items, ensure_ascii=False), top(v.get("Spreads", {})),
                     json.dumps(moves, ensure_ascii=False), top(v.get("Teammates", {})), url))
    db.executemany("INSERT INTO smogon_usage VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows), unmapped


if __name__ == "__main__":
    print("저장:", download())
