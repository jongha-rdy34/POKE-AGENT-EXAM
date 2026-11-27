"""챔피언스 도감 종의 Bulbapedia 문서(소개 + Biology)를 선수집한다. 5초 간격·단일 스레드(robots.txt Crawl-delay: 5), 받은 종은 건너뛴다.
  .venv/Scripts/python -m prep.bulbapedia
저장: data/raw/bulbapedia/{species}.json  (CC BY-NC-SA 2.5, 원문 URL·판 번호 포함)
표·습득기는 PokeAPI 구조화 데이터가 담당하므로 서술 부분만 쓴다.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from config import BULBAPEDIA_INTERVAL, DATA_DIR, USER_AGENT

RAW = DATA_DIR / "raw"
OUT = RAW / "bulbapedia"
API = "https://bulbapedia.bulbagarden.net/w/api.php"
UA = USER_AGENT


def fetch(title):
    q = urllib.parse.urlencode({"action": "query", "prop": "extracts|revisions", "explaintext": 1, "exsectionformat": "wiki",
                                "rvprop": "ids|timestamp", "titles": title, "redirects": 1, "format": "json", "formatversion": 2})
    for attempt in range(5):
        try:
            time.sleep(BULBAPEDIA_INTERVAL)
            with urllib.request.urlopen(urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA}), timeout=30) as r:
                return json.loads(r.read())["query"]["pages"][0]
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 ** attempt * 5)
    raise RuntimeError(f"Bulbapedia 요청 실패: {title}")


def narrative(extract):
    """소개 + Biology(Forms·Evolution 포함)만. 'Game data' 이후(위치·도감 문구·표 잔재)는 버린다."""
    return re.split(r"^== Game data ==", extract, maxsplit=1, flags=re.M)[0].strip()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dex = json.loads((RAW / "pokeapi" / "pokedex_champions.json").read_text(encoding="utf-8"))["pokemon_entries"]
    species = [e["pokemon_species"]["name"] for e in dex]
    for i, sp in enumerate(species, 1):
        f = OUT / f"{sp}.json"
        if f.exists():
            continue
        en = json.loads((RAW / "pokeapi" / "species" / f"{sp}.json").read_text(encoding="utf-8"))["names"]["en"]
        p = fetch(f"{en} (Pokémon)")
        text = narrative(p.get("extract", ""))
        rec = {"species": sp, "title": p["title"], "url": "https://bulbapedia.bulbagarden.net/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_")),
               "revid": (p.get("revisions") or [{}])[0].get("revid"), "timestamp": (p.get("revisions") or [{}])[0].get("timestamp"),
               "collected_at": date.today().isoformat(), "missing": bool(p.get("missing")) or not text, "text": text}
        f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{i}/{len(species)} {sp} → {p['title']} {len(text)}자{' (문서 없음)' if rec['missing'] else ''}", flush=True)


if __name__ == "__main__":
    main()
