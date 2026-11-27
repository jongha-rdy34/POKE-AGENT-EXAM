"""메커니즘 문서를 pokemon_docs에 색인한다(form_key = "_global"). 다시 실행해도 같은 청크 ID를 덮어쓴다.
  .venv/Scripts/python -m rag.index_docs
요약 문서(stat_damage_formulas.md)와 그 근거인 Bulbapedia 원문 3곳(관련 절만)을 각자의 URL로 색인한다.
"""
import re

from config import DATA_DIR
from rag.docs import index_document
from rag.store import collection

DOCS = DATA_DIR / "docs"
BULBA = "https://bulbapedia.bulbagarden.net/wiki"
COLLECTED = "2026-10-21"


def section(text, heading):
    """'## 제목' 또는 '### 제목' 줄부터 같은 레벨 이하의 다음 제목 직전까지."""
    m = re.search(rf"^(#+) {re.escape(heading)}\s*$", text, re.M)
    level = len(m.group(1))
    nxt = re.search(rf"^#{{1,{level}}} ", text[m.end():], re.M)
    return text[m.start(): m.end() + nxt.start()] if nxt else text[m.start():]


def main():
    src = DOCS / "_src"
    jobs = [
        (DOCS / "stat_damage_formulas.md", {
            "title": "능력 포인트(SP)에 따른 실수치·결정력·내구 계산법 (Bulbapedia 기반 정리)", "doc_id": "mechanics-stat-damage",
            "url": f"{BULBA}/Stat_point", "source_type": "bulbapedia"}),
        (src / "Stat_point.txt", {"title": "Stat point - Bulbapedia", "doc_id": "bulbapedia-stat-point", "url": f"{BULBA}/Stat_point",
                                  "source_type": "bulbapedia"}),
        (None, {"title": "Stat (Determination of stats) - Bulbapedia", "doc_id": "bulbapedia-stat-formula", "url": f"{BULBA}/Stat",
                "source_type": "bulbapedia", "from": (src / "Stat.txt", "Determination of stats")}),
        (None, {"title": "Damage (Generation V onward) - Bulbapedia", "doc_id": "bulbapedia-damage-gen5", "url": f"{BULBA}/Damage",
                "source_type": "bulbapedia", "from": (src / "Damage.txt", "Generation V onward")}),
    ]
    total = 0
    for path, meta in jobs:
        sec = meta.pop("from", None)
        text = section(sec[0].read_text(encoding="utf-8"), sec[1]) if sec else path.read_text(encoding="utf-8")
        n = index_document(text, form_key="_global", related_name="stat formulas", collected_at=COLLECTED, **meta)
        total += n
        print(f"{meta['doc_id']:26} {len(text):6}자 → {n}청크")
    print("pokemon_docs 컬렉션 건수", collection("pokemon_docs")._collection.count(), "(이번 실행 청크", total, ")")


if __name__ == "__main__":
    main()
