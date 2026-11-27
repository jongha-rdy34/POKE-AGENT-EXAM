# 인계장: Claude 세션 (진행 담당)

작성 2026-11-27. 이전 세션은 클라우드 컨테이너에서 Phase 1까지 끝냈다. 이 문서만 읽고 이어갈 수 있게 썼다.
작업 지시 원문은 저장소 루트 `poke-judge-orchestration-prompt.md`다. **먼저 읽는다.**

## 1. 역할 분담
| 세션 | 맡는 것 | 쓰는 파일(소유) | 브랜치 |
|---|---|---|---|
| **Claude (이 문서)** | Phase 2 캡처, Phase 4 패킷, Phase 5 판정(Gemini API + Claude 하위 에이전트), Phase 6 집계, Phase 7 설문, `run_all.py` | `scenarios/ captures/ packets/ judges/(raw/openai 제외) analysis/ run_all.py scripts/` | `claude/judge-eval` |
| Codex | Phase 3 객관 지표(기대값을 Claude와 독립적으로 계산), OpenAI 판정 12건 | `objective/`, `judges/raw/openai/` | `codex/objective-openai` |

- 남의 소유 파일은 고치지 않는다. 필요한 변경은 사용자에게 말한다.
- Codex 결과는 사용자가 확인한 뒤 Claude 브랜치로 merge한다. 집계(`analysis/`)는 Claude만 한다.
- 판정 패킷(`packets/`)은 Claude가 만들고 Codex가 읽는다. 패킷을 만들면 사용자에게 알려서 Codex가 시작하게 한다.

## 2. 확정된 결정 (다시 논의하지 않는다)
- 앱: A = `POKE_RAG(한턴복기)/` (skill 사용), B = `Poke-Agent-claude/` (skill 없음). `judge-eval/apps/A`, `apps/B`는 심볼릭 링크다(Windows에서 깨지면 경로를 직접 쓴다).
- **결론은 기술(記述)만.** "skill 효과가 있다/없다" 같은 인과 문장을 쓰지 않는다. 앱 코드는 고치지 않는다.
- 두 앱의 LLM은 **`gemini-3.5-flash`로 통일**, Gemini OpenAI 호환 주소 사용. 앱 코드·앱 `.env` 수정 없이 **환경변수로만** 넘긴다(아래 4절).
- 시나리오 **5개**, `scenarios/scenarios.yaml` v1 (status: approved). 해상도 1440×900, 390×844. 시나리오·해상도마다 캡처 2장 이하.
- 판정 모델 3개:
  - Google: `gemini-3.5-flash` API, temperature 0.2.
  - Claude: **이 세션의 하위 에이전트**(Anthropic API 키 없음). temperature 지정 불가. 실제 모델 이름을 기록한다.
  - OpenAI: Codex 세션이 맡는다(OpenAI API 키는 크레딧 0이라 쓰지 않는다). 대안은 ChatGPT 앱 수동 실행(`judges/manual_chatgpt.md`).
- 반복 3회: 절대 평가 2앱×3모델×3회=18건, 쌍비교 3모델×2순서×3회=18건.
- 프롬프트는 `judges/prompts/{system,absolute,pairwise}.md`. 응답 검사는 `judges/schema.py`(모든 판정 공통). 스키마 위반 시 최대 2회 재요청, 그래도 실패면 실패로 기록.

## 3. 지금까지 한 것 (main 대신 브랜치 `claude/magical-bardeen-8cy2cm`에 있다)
- `analysis/inventory.md`(Phase 1 결과), `analysis/inventory_metrics.json`, `scripts/inventory.py`
  - 테스트: A 86개 통과(unittest), B 90개 통과(pytest). 빌드·lint 설정은 둘 다 없음. ruff E,F 참고값 A 12건, B 4건.
  - 커밋 기록은 측정 불가(두 앱 모두 원본 기록 없이 들어옴).
- `scenarios/scenarios.yaml` v1, 판정 프롬프트, `judges/manual_chatgpt.md`, `judges/import_manual.py`
- `apps_cache/B/`: B가 2026-11-27에 받아 온 외부 데이터(PokeAPI·Smogon·Showdown) 9.4MB. **B 실행 때 `CACHE_DIR`로 이 폴더를 지정해** 데이터 시점을 고정한다.

## 4. 실행 방법
```bash
# 가상환경은 앱 폴더 밖에 둔다 (Windows Git Bash면 bin → Scripts)
python -m venv ../venvs/A && ../venvs/A/bin/pip install -r "POKE_RAG(한턴복기)/requirements.txt"
python -m venv ../venvs/B && ../venvs/B/bin/pip install -r Poke-Agent-claude/backend/requirements.txt pytest
cp judge-eval/.env.example judge-eval/.env   # 사용자가 GEMINI_API_KEY를 채운다
```
A (앱 루트에서, 포트 8101):
```bash
INVITE_TOKENS=$A_INVITE_TOKENS OPENAI_API_KEY=$GEMINI_API_KEY OPENAI_BASE_URL=$GEMINI_OPENAI_BASE CHAT_MODEL=$APP_LLM_MODEL \
  python -m uvicorn server.app:app --port 8101 --no-access-log
# 접속: http://127.0.0.1:8101/?t=<비밀값> → 쿠키 발급 후 / 로 이동. 쿠키 없으면 API 403
```
B (`Poke-Agent-claude/backend`에서, 포트 8102):
```bash
GMS_API_KEY=$GEMINI_API_KEY GMS_BASE_URL=$GEMINI_OPENAI_BASE LLM_MODEL=$APP_LLM_MODEL CACHE_DIR=<절대경로>/judge-eval/apps_cache/B \
  python -m uvicorn app.main:app --port 8102
```
확인된 동작(2026-11-27): A 문장 읽기 약 10초, 추출 정확. B 선출 추천 약 26초. B는 먼저 "메가스톤 든 포켓몬"을 묻는다. 시나리오에서는 **없음**을 고른다(API로는 `mega_choice: {"my_holders": {}, "opp": "none"}`).

**함정**
- `load_dotenv`는 이미 있는 환경변수를 덮지 않는다. 앱 폴더에 `.env`를 만들지 말고 환경변수로만 넘긴다.
- A 폰트는 `cdn.jsdelivr.net`(Pretendard)에서 온다. 막히면 기본 글꼴로 캡처돼 UI 점수가 왜곡된다. 캡처 전에 폰트 로드를 확인한다(`document.fonts.check`).
- B 스프라이트는 `raw.githubusercontent.com`에서 온다.
- Gemini 무료 플랜: `gemini-3.1-pro-preview`는 할당량 0(429), `2.5-*`는 신규 사용자에게 404. 성공 확인은 `3.5-flash`, `3.6-flash`, `3.5-flash-lite`뿐이다. 앱과 판정이 한 키를 쓰므로 분당 한도에 걸리면 호출 간격을 둔다.

## 5. 다음 할 일 (순서대로, 단계마다 사용자에게 짧게 보고)
1. **Phase 2**: `scripts/capture.py`(Playwright). 서버는 캡처 동안만 띄우고 끝나면 내린다. 결과 `captures/{A,B}/{scenario}_{viewport}[_n].png`, 앱 응답 원문도 `captures/{A,B}/{scenario}.json`으로 저장(패킷·객관 지표 근거). 실패한 단계는 고치지 말고 기록.
2. **Phase 4**: `scripts/build_packets.py`. 앱마다 패킷 1개: 목적 1~2문장(같은 형식·중립), 기능 목록, 캡처, 코드 발췌 300줄 상한(양쪽 같은 상한), 객관 지표(Codex 결과가 오면 넣는다).
   - 익명화: 앱 이름, 저장소명, 폴더명, `CLAUDE.md DESIGN.md agent.md TODOS.md skills-lock.json .agents/` 같은 skill·절차 흔적, 코드 주석의 절차 번호(A: `eng #3 R1`, `CEO C3-1`, `D25`, `DR20`, `DESIGN.md`; B: `F3001`류, `SSAFY`, `GMS`), 화면의 서비스 이름(캡처 전에 DOM에서 가리거나 캡처 뒤 가림). 지운 항목은 `packets/anonymization.md`에 목록으로 남긴다.
   - X/Y 배정은 무작위(시드 기록), 배정표는 `packets/mapping.secret.json`(판정 입력에 넣지 않음).
   - ChatGPT·Codex용 묶음(`packets/chatgpt/`, `packets/codex/`)도 만든다: 건마다 프롬프트 텍스트 1개 + 캡처 묶음 PNG.
3. **Phase 5**: `scripts/judge.py`. 판정 전에 예상 호출 수·토큰·비용을 계산해 보고하고, 모델마다 1건 dry run 후 **사용자 확인을 받고** 본 실행.
   - Claude 판정은 하위 에이전트로: 패킷 폴더만 읽으라고 지시하고, 응답을 `schema.py`로 검사해 `judges/raw/claude.jsonl`에 저장. 앱 원본을 읽으면 익명화가 깨진다는 점을 보고서 한계에 쓴다.
   - 원본 응답은 전부 `judges/raw/*.jsonl`.
4. **Phase 6**: `analysis/summary.csv`, `analysis/report.md`(맨 위 5줄 요약, 모든 수치는 summary.csv에서 계산). 평균·표준편차, 승률, 위치 편향, Krippendorff's alpha, 자기 선호(Claude vs 나머지), 객관 지표표, 길이 편향 관찰, 한계.
   - 한계에 반드시: 조건마다 결과물 1개, 교란변수(기능 범위·투입 시간·제작 순서·목적), LLM 선호 ≠ 사람 선호, temperature는 Gemini만 고정, ChatGPT/Codex·Claude 하위 에이전트는 시스템 프롬프트 통제 불가, Gemini 판정이 Gemini 생성 응답을 평가.
5. **Phase 7**: `analysis/human_check.md`(2분 설문).
6. `run_all.py`: `--dry-run`(모델마다 1건 + 비용 추정), `--reuse-captures`. Phase 2~6을 한 번에 재실행.

## 6. 지킬 것
- 사실·측정·해석을 구분해 적는다. 수치를 추정해서 채우지 않는다.
- 키는 `judge-eval/.env`에만. 코드·로그·보고서에 출력하지 않는다.
- A 폴더의 `data/logs/`(친구 테스트 원문)는 읽지도 공유하지도 않는다(지금 저장소에는 없다).
- 커밋은 작업 단위로, 브랜치에만 push. PR은 사용자가 요청할 때만.
