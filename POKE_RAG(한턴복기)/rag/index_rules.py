"""선수집한 Bulbapedia 규칙 문서(data/raw/bulbapedia_rules)를 pokemon_docs에 색인한다(설계 D23·T10).
  .venv/Scripts/python -m rag.index_rules
규칙 문서는 특정 포켓몬이 아니므로 form_key = "_global"(메커니즘 문서와 같은 자리). 청크 ID = _global:doc_id:seq (재실행 시 덮어쓰기).
색인은 소개 + 효과 절(text)만 쓰고, 원문 전체(full_text)는 평가셋 라벨 대조용으로 캐시에만 둔다.
"""
import json

from config import DATA_DIR
from prep.bulbapedia_rules import slug
from rag.docs import index_document
from rag.store import collection


def main():
    n_docs = n_chunks = 0
    skipped = []
    for f in sorted((DATA_DIR / "raw" / "bulbapedia_rules").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d["missing"] or not d["text"]:
            skipped.append(d["query_title"])
            continue
        n_chunks += index_document(d["text"], prefix=f"[{d['title']}] ", title=d["title"] + " - Bulbapedia", url=d["url"],
                                   doc_id=f"bulbapedia-rule-{slug(d['title'])}", dex_no=0, form_key="_global", related_name=d["title"],
                                   query=",".join(d["tags"]), collected_at=d["collected_at"], source_type="bulbapedia")
        n_docs += 1
    print(f"문서 {n_docs}개 → {n_chunks}청크, 건너뜀 {skipped}")
    print("pokemon_docs 컬렉션 건수", collection("pokemon_docs")._collection.count())


if __name__ == "__main__":
    main()
