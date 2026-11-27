"""GMS(OpenAI 호환) 채팅 한 번. 키가 없거나 호출이 실패하면 예외를 던지고, 부르는 쪽이 직접 입력·템플릿으로 내려간다(D16)."""
import config


def chat(system, user, timeout=20):
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY 없음")
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model=config.CHAT_MODEL, api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL,
                     temperature=0, timeout=timeout, max_retries=1)
    return llm.invoke([("system", system), ("user", user)]).content
