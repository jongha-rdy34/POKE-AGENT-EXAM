"""포켓몬 챔피언스에서 쓸 수 있는 도구 목록 → champion_item 테이블. 두 출처가 서로 맞는지 대조한다(2026-10-23 사용자 지시).
  .venv/Scripts/python -m prep.champions_items download   # 원본 다시 받기(Bulbapedia 5초 간격). 새 업데이트로 도구가 늘면 실행
  .venv/Scripts/python -m prep.champions_items            # 받아 둔 원본으로 대조·적재만(build_db도 이것을 부른다)
출처:
  1. Bulbapedia "List of items by index number in Pokémon Champions"(출시 판) + "Shop (Champions)" 지닌 도구 절(Ver. 1.2.0 추가분)
  2. Showdown data/mods/champions/items.ts(+ data/items.ts 상속), 형식 [Gen 9 Champions] BSS Reg M-C의 mod
두 출처의 합집합을 적재하고, 한쪽에만 있는 도구는 경고로 알린다(2026-10-23 기준 일반 도구 85종 완전 일치).
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

import config
from prep.smogon import ID_EXCEPTIONS, key_index, showdown_id

RAW = config.DATA_DIR / "raw" / "champions_items"
SHOWDOWN = "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/"
SHOWDOWN_FILES = {"base_items.ts": "data/items.ts", "champions_items.ts": "data/mods/champions/items.ts"}
BULBAPEDIA = {"bulbapedia_index.json": "List of items by index number in Pokémon Champions", "bulbapedia_shop_champions.json": "Shop (Champions)"}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT}), timeout=60) as r:
        return r.read()


def download():
    (RAW / "showdown").mkdir(parents=True, exist_ok=True)
    for name, path in SHOWDOWN_FILES.items():
        (RAW / "showdown" / name).write_bytes(_get(SHOWDOWN + path))
    for name, title in BULBAPEDIA.items():
        time.sleep(config.BULBAPEDIA_INTERVAL)
        q = urllib.parse.urlencode({"action": "parse", "page": title, "prop": "wikitext|revid", "format": "json"})
        (RAW / name).write_bytes(_get(f"https://bulbapedia.bulbagarden.net/w/api.php?{q}"))


def _blocks(text):
    """Showdown items.ts 최상위 항목(탭 1개 들여쓰기) → 본문."""
    return {m.group(1): m.group(2) for m in re.finditer(r"^\t([a-z0-9]+): \{\n(.*?)^\t\},", text, re.M | re.S)}


def _nonstandard(body):
    """isNonstandard 값. 적혀 있지 않으면 ...(상속), null이면 None(사용 가능)."""
    m = re.search(r'isNonstandard: (null|"[^"]+")', body)
    return ... if m is None else (None if m.group(1) == "null" else m.group(1).strip('"'))


def showdown_allowed():
    """Reg M-C에서 쓸 수 있는 도구의 Showdown id → 메가스톤 여부."""
    base = _blocks((RAW / "showdown" / "base_items.ts").read_text(encoding="utf-8"))
    mod = _blocks((RAW / "showdown" / "champions_items.ts").read_text(encoding="utf-8"))
    out = {}
    for k, body in base.items():
        v = _nonstandard(mod[k]) if k in mod else ...
        if v is ...:
            v = _nonstandard(body)
        if v is None or v is ...:
            out[k] = "megaStone" in body
    return out


def bulbapedia_allowed():
    """색인 목록(출시 판) ∪ 상점의 지닌 도구 절. Showdown id → 메가스톤 여부(상점 메가스톤 절·색인 이름으로 판단)."""
    idx = json.loads((RAW / "bulbapedia_index.json").read_text(encoding="utf-8"))["parse"]["wikitext"]["*"]
    shop = json.loads((RAW / "bulbapedia_shop_champions.json").read_text(encoding="utf-8"))["parse"]["wikitext"]["*"]
    held = shop[shop.index("===[[Held item|Held Items]]==="):shop.index("===[[Mega Stone]]s===")]
    mega = shop[shop.index("===[[Mega Stone]]s==="):shop.index("===Clothing===")]
    name = lambda s: showdown_id(re.sub(r"\s*\(item\).*$|\{\{!.*$", "", s.strip()))
    megas = {name(x) for x in re.findall(r"\{\{shopitem\|([^|}]+)", mega)}
    out = {name(x): name(x) in megas for x in re.findall(r"\{\{hexlist\|([^|}]+)", idx)}
    out.update({name(x): False for x in re.findall(r"\{\{shopitem\|([^|}]+)", held)})
    for k in out:  # 색인 목록의 메가스톤("Garchompite")은 상점 절에 없을 수 있다
        out[k] = out[k] or (k.endswith(("ite", "itex", "itey", "itez")) and k not in ("whiteherb",))
    return out


def load_into(db):
    """대조 후 champion_item(key, is_mega, sources)에 적재. 반환: (적재 수, 경고 목록)."""
    db.execute("DROP TABLE IF EXISTS champion_item")
    db.execute("CREATE TABLE champion_item (key TEXT PRIMARY KEY, is_mega INTEGER, sources TEXT)")
    if not (RAW / "showdown" / "champions_items.ts").exists() or not (RAW / "bulbapedia_index.json").exists():
        return 0, ["원본 없음: python -m prep.champions_items download"]
    sd, bp = showdown_allowed(), bulbapedia_allowed()
    warn = []
    held_sd, held_bp = {k for k, m in sd.items() if not m}, {k for k, m in bp.items() if not m}
    if held_sd != held_bp:
        warn.append(f"일반 도구가 출처마다 다름: Showdown에만 {sorted(held_sd - held_bp)}, Bulbapedia에만 {sorted(held_bp - held_sd)}")
    index = key_index(db, "item")
    rows, unmapped = [], []
    for sid in sorted(set(sd) | set(bp)):
        key = ID_EXCEPTIONS.get(sid, index.get(sid))
        if not key:
            unmapped.append(sid)
            continue
        src = "+".join(n for n, s in (("showdown", sd), ("bulbapedia", bp)) if sid in s)
        rows.append((key, int(sd.get(sid, bp.get(sid, False))), src))
    if unmapped:
        warn.append(f"PokeAPI 도구 표에 없는 이름: {unmapped}")
    db.executemany("INSERT OR REPLACE INTO champion_item VALUES (?,?,?)", rows)
    return len(rows), warn


if __name__ == "__main__":
    if "download" in sys.argv:
        download()
    from prep.calculator import DB_PATH
    import sqlite3
    db = sqlite3.connect(DB_PATH)
    n, warn = load_into(db)
    db.commit()
    sys.stdout.reconfigure(encoding="utf-8")
    held = db.execute("SELECT COUNT(*) FROM champion_item WHERE is_mega=0").fetchone()[0]
    print(f"champion_item: {n}종(일반 도구 {held}, 메가스톤 {n - held})", *(f"\n경고: {w}" for w in warn))
