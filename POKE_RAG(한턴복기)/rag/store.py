"""Chroma 컬렉션 접근. 임베딩·키·경로는 config에서만 읽는다."""
from functools import cache

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

import config


def embeddings():
    # GMS 등 OpenAI 호환 서버에는 토큰화하지 않은 원문 문자열을 그대로 보낸다
    return OpenAIEmbeddings(model=config.EMBED_MODEL, api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL,
                            check_embedding_ctx_length=False)


@cache  # 컬렉션마다 Chroma 클라이언트·임베딩 객체를 한 번만 만든다
def collection(name):
    return Chroma(collection_name=name, embedding_function=embeddings(), persist_directory=str(config.CHROMA_DIR))
