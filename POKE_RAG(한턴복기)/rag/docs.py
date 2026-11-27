"""pokemon_docs 색인 공용 함수 (F2005). 청크 ID = form_key:doc_id:seq 라 같은 문서를 다시 넣으면 덮어쓴다."""
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config
from rag.store import collection

META_KEYS = ("title", "url", "doc_id", "dex_no", "form_key", "related_name", "query", "collected_at", "source_type")


def index_document(text, prefix="", **meta):
    """meta는 META_KEYS 전부를 받는다(없으면 빈 값). prefix는 각 청크 앞에 붙인다(제목 등). 청크 수를 돌려준다."""
    meta = {k: meta.get(k, "" if k != "dex_no" else 0) for k in META_KEYS}
    chunks = RecursiveCharacterTextSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP).split_text(text)
    chunks = [prefix + c for c in chunks]
    ids = [f"{meta['form_key']}:{meta['doc_id']}:{i}" for i in range(len(chunks))]
    col = collection("pokemon_docs")
    col._collection.delete(where={"$and": [{"form_key": meta["form_key"]}, {"doc_id": meta["doc_id"]}]})  # 문서가 줄어도 낡은 청크가 남지 않게
    col.add_texts(chunks, metadatas=[{**meta, "seq": i} for i in range(len(chunks))], ids=ids)
    return len(chunks)
