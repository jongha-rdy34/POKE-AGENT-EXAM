"""LLM·임베딩 연결 확인: .venv/Scripts/python -m prep.llm_check  (키·base_url은 .env에서 config가 읽는다)"""
import config
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

if not config.OPENAI_API_KEY:
    raise SystemExit("OPENAI_API_KEY가 .env에 비어 있습니다.")

kw = {"api_key": config.OPENAI_API_KEY, "base_url": config.OPENAI_BASE_URL}
print("chat :", ChatOpenAI(model=config.CHAT_MODEL, **kw).invoke("한 단어로 인사해줘").content)
print("embed:", len(OpenAIEmbeddings(model=config.EMBED_MODEL, **kw).embed_query("한카리아스")), "차원")
