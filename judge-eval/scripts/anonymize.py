"""판정 입력 익명화 규칙. 판정 모델에게 가는 모든 텍스트(목적·기능 목록·코드 발췌)에 같은 규칙을 쓴다.

redact(text) → (바뀐 텍스트, [(규칙 이름, 원문 조각), ...])
규칙과 이유는 packets/anonymization.md에 그대로 옮긴다(build_rules_doc).
"""
import re

# (이름, 패턴, 바꿀 값, 이유). 순서대로 적용한다.
RULES = [
    ("service_name", r"한 ?턴 복기(?: 코치)?|Poke-?Agent|POKE_RAG|Poke-Agent-claude", "[service]", "서비스·저장소 이름"),
    ("repo_folder", r"한턴복기", "[service]", "저장소 폴더 이름"),
    ("agent_docs", r"(?<![A-Za-z0-9_])(?:CLAUDE|DESIGN|AGENTS?|TODOS|agent)\.md(?![A-Za-z0-9_])|skills-lock\.json|\.agents/", "[doc]",
     "에이전트·skill 작업 문서 이름(제작 방식 흔적)"),
    ("skill_names", r"(?<![A-Za-z0-9_])(?:gstack|ponytail|taste-skill|agent-skills|superpowers|office-hours|plan-(?:ceo|eng|design)-review)(?![A-Za-z0-9_])",
     "[tool]", "skill·플러그인 이름"),
    ("review_refs", r"eng ?#\d+(?: ?[A-Z]+\d+(?:[·,] ?[A-Z]*\d+)*)?|CEO[- ]?[A-Z]*\d+(?:-\d+)?|C-O\d+", "[ref]",
     "설계 리뷰 절차 번호(제작 절차 흔적)"),
    ("course_org", r"SSAFY", "[org]", "교육 과정 이름"),
    ("course_llm_gateway", r"(?<![A-Za-z0-9])GMS(?![A-Za-z0-9])|GMS(?=_)", "LLM", "교육 과정 LLM 게이트웨이 이름(변수명은 GMS_X → LLM_X)"),
    ("requirement_ids", r"(?<![A-Za-z0-9])N?F\d{4}(?![0-9])", "[ref]", "과정 요구사항 번호"),
    # 단독 문서 번호(D25, R1, U5, S1 ...)는 괄호·쉼표 안에서만 지운다. 코드의 변수와 겹치지 않게.
    ("decision_ids", r"(?<=[(\s·,/])(?:DR|D|R|U|W|S|T|O|C)\d{1,2}(?:-\d+)?(?=[)\s·,:/.]|$)", "[ref]",
     "설계 결정·리뷰 항목 번호"),
]
_COMPILED = [(n, re.compile(p), v) for n, p, v, _ in RULES]
_NOQA = re.compile(r"noqa: ?[A-Z]+\d+")
_REF_GROUP = re.compile(r"\s*\((?:\s*\[ref\]\s*[·,]?)+\)")
_REF_LIST = re.compile(r"\s*[·,]\s*\[ref\]")


def redact(text):
    hits = []
    protected = {}

    def keep(m):  # ruff noqa 코드(F401 등)는 그대로 둔다
        k = f"\x00{len(protected)}\x00"
        protected[k] = m.group(0)
        return k

    text = _NOQA.sub(keep, text)
    for name, rx, repl in _COMPILED:
        def sub(m, name=name, repl=repl):
            hits.append((name, m.group(0)))
            return repl
        text = rx.sub(sub, text)
    # [ref] 표시가 남으면 그 개수 자체가 "절차 문서가 많은 쪽"이라는 단서가 된다. 표시 없이 지운다.
    text = _REF_GROUP.sub("", text)          # "([ref]·[ref])" 같은 괄호 묶음 통째로
    text = _REF_LIST.sub("", text)           # "(원문 노출 안 함, [ref])" → "(원문 노출 안 함)"
    text = re.sub(r"\[ref\][:：]?[ \t]*", "", text)  # 남은 단독 표시와 바로 뒤 콜론·공백
    for k, v in protected.items():
        text = text.replace(k, v)
    return text, hits


def build_rules_doc():
    lines = ["| 규칙 | 패턴 | 바꾼 값 | 이유 |", "|---|---|---|---|"]
    lines += [f"| {n} | `{p.replace('|', chr(92) + '|')}` | `{v}` | {why} |" for n, p, v, why in RULES]
    return "\n".join(lines)


if __name__ == "__main__":
    samples = ["# eng #3 R1·R3·R4: 계산은 스레드풀", "(D25, U5) 한 턴 복기 코치", "GMS_API_KEY  # SSAFY GMS F3001",
               "import x  # noqa: F401", "S1 = 3  # 변수는 그대로", "DESIGN.md를 읽는다 (CEO C3-1)"]
    for s in samples:
        print(repr(s), "→", repr(redact(s)[0]))
