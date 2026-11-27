"""선수집한 Bulbapedia 문서(data/raw/bulbapedia)를 pokemon_docs에 색인한다. 청크 ID = form_key:doc_id:seq (재실행 시 덮어쓰기).
  .venv/Scripts/python -m rag.index_bulbapedia
form_key는 종의 기본 폼으로 건다. 메가 등 다른 폼 서술은 같은 문서에 들어 있으므로 종 단위로 검색된다.
"""
import json
import sqlite3

from config import DATA_DIR, DB_PATH
from rag.docs import index_document
from rag.store import collection


def main():
    db = sqlite3.connect(DB_PATH)
    n_docs = n_chunks = 0
    skipped = []
    for f in sorted((DATA_DIR / "raw" / "bulbapedia").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        row = db.execute("SELECT form_key, dex_no FROM pokemon WHERE species=? AND is_default=1", (d["species"],)).fetchone()
        if d["missing"] or row is None:
            skipped.append(d["species"])
            continue
        n_chunks += index_document(d["text"], prefix=f"[{d['title']}] ", title=d["title"] + " - Bulbapedia", url=d["url"], doc_id=f"bulbapedia-{d['species']}",
                                   dex_no=row[1], form_key=row[0], related_name=d["title"], collected_at=d["collected_at"], source_type="bulbapedia")
        n_docs += 1
    print(f"문서 {n_docs}개 → {n_chunks}청크, 건너뜀 {skipped}")
    print("pokemon_docs 컬렉션 건수", collection("pokemon_docs")._collection.count())


if __name__ == "__main__":
    main()
