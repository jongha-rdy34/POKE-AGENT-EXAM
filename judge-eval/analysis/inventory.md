# Phase 1 인벤토리

작성: 2026-11-27, 클라우드 컨테이너(Linux, Python 3.13.18, Node 22.23.5).
표기: **[사실]** 파일·문서에서 확인 · **[측정]** 이 환경에서 실행해 얻은 값 · **[해석]** 판단이 들어간 내용.
앱 코드는 고치지 않았다. 수치는 `scripts/inventory.py` → `analysis/inventory_metrics.json`에서 다시 만들 수 있다.

## 1. 대상

| | A | B |
|---|---|---|
| 경로 | `POKE_RAG(한턴복기)/` (→ `judge-eval/apps/A`) | `Poke-Agent-claude/` (→ `judge-eval/apps/B`) |
| 서비스 [사실] | 졌던 한 턴을 자연어로 적으면 데미지·스피드를 계산해 "왜 졌나·상대가 뭘 들었나"를 답하는 복기 코치 | 내 6마리·상대 6마리를 보고 선출 3마리와 기술을 메타 통계·종족값·상성으로 계산해 제안하는 Agent |
| 스택 [사실] | FastAPI + 순수 HTML/JS, SQLite(`data/processed/pokedex.sqlite`) 스냅숏 | FastAPI + LangGraph + 순수 HTML/CSS/JS, 외부 API 실시간 조회 + 파일 캐시 |
| LLM 사용처 [사실] | 자연어 → 입력 칸 추출(`/api/feature/review/extract`). 계산과 결론은 코드. 요약 LLM은 기본 꺼짐 | 요청 분석(`analyze`)과 응답 문장화(`respond`). 계산은 코드 |
| LLM 설정 [사실] | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, 기본 `gpt-4o-mini` | `GMS_API_KEY`, `GMS_BASE_URL`(OpenAI 호환), 기본 `gpt-4.1-mini` |

## 2. 실행 명령과 포트

| | A | B |
|---|---|---|
| 설치 | `pip install -r requirements.txt` | `pip install -r backend/requirements.txt` |
| 서버 | `INVITE_TOKENS=eval:<값> python -m uvicorn server.app:app --port 8101 --no-access-log` (앱 루트에서) | `python -m uvicorn app.main:app --port 8102` (`backend/`에서) |
| 접속 | `http://127.0.0.1:8101/?t=<값>` → 쿠키 발급 후 사용. 토큰 없으면 API 403 | `http://127.0.0.1:8102/` (인증 없음) |

평가용 가상환경은 저장소 밖(`/home/user/venvs/A`, `/home/user/venvs/B`)에 두었다. 초대 토큰은 파일 대신 환경변수로 넘겨 앱 폴더에 `.env`를 만들지 않았다.

## 3. 기능 목록 (화면·기능 단위) [사실: 코드와 화면 요소에서 정리]

### A
1. 초대 링크 접속(토큰 → 쿠키), 사용 한도(토큰당 하루 복기 50·읽기 100, 서버 LLM 400)
2. 한 턴 자연어 입력 + 예시 버튼("어떤 한 턴이 납득 안 되나요?")
3. 문장 읽기(LLM) → "이렇게 이해했어요" 확인 화면: 내/상대 포켓몬, 기술, 공격 측 바꾸기, 결과(한 방에 쓰러짐·버팀·먼저 움직임 등)
4. LLM 실패 시 칸 직접 채우기로 전환
5. "더 정확하게 적기"(접힘): 내 성격·도구·SP, 상대 SP, 맞기 전 HP
6. 복기 계산(SSE): 16단계 난수 데미지, 스피드 비교, 상대 도구·배분·위협 후보별 원인 순위, pokedb·Smogon 기준이 다르면 둘 다 표시
7. 결과 피드백("그 턴이 진짜 패인이었나요?"), 새 턴 복기, 기록 삭제 요청
8. 포켓몬·기술 검색 API(`/api/pokemon`, `/api/moves`)

### B
1. 게임 버전(포켓몬 챔피언스 / 스칼렛·바이올렛)과 배틀 방식(싱글 6→3 / 더블 6→4) 토글
2. 팀 입력 2가지: 대화로 입력 / 직접 선택(이름 검색, 스프라이트)
3. 선출 추천(Agent): 상대 예상 세트(Smogon 사용률), 상성·스피드·결정력 계산, 선출 조합과 기술 제안, 재계획
4. 실전 세트 조회, 대면 판단(1:1)
5. 메가진화 선택·대안
6. 계획 관리: 선출 계획 저장·조회·수정·삭제(날짜·시작·종료·메모)
7. 실행 로그: 세션별 Agent 단계·Tool 호출 이력 조회·삭제
8. Tool 직접 호출 API(`/api/tools`), Swagger(`/docs`)

## 4. 메타데이터

| 항목 | A | B | 비고 |
|---|---|---|---|
| 커밋 수·첫/마지막 커밋 시각 | **확인 불가** | **확인 불가** | [사실] 이 비교 저장소에는 두 앱이 원본 기록 없이 들어와 있다(커밋 3개, 모두 2026-11-27 "first commit"). A는 원래 커밋 0개 상태로 옮겼다는 기록이 있다(`docs/HANDOFF-machine-migration.md`). B 원본(`jongha-rdy34/Poke-Agent`) 기록 조회는 이 세션 권한 밖이라 하지 못했다 |
| 코드 파일 수 [측정] | 37 | 50 | `.py .js .html .css`, `data/ docs/ .agents/` 제외 |
| 코드 라인 [측정] | 4,800 (py 3,942 · js 473 · html 385) | 6,495 (py 5,429 · js 607 · html 119 · css 340) | 빈 줄·주석 포함 |
| 테스트 코드 라인 [측정] | 855 | 846 | |
| 문서(md) 라인 [측정] | 4,803 | 911 | A는 설계·리뷰·인계 문서 포함 |
| Python 의존성(고정 버전) [사실] | 17 | 18 | requirements 기준. 프런트 외부 의존: A는 Pretendard 폰트 CDN 1개, B는 없음(스프라이트 이미지는 GitHub raw) |
| 빌드 [사실] | 해당 없음 | 해당 없음 | 프런트에 번들러·package.json 없음 |
| lint 설정 [사실] | 없음 | 없음 | |
| lint 참고값 [측정] | 12건 | 4건 | `ruff 0.17.6 --isolated --select E,F --ignore E501`. 설정이 없어 같은 최소 규칙을 양쪽에 똑같이 적용한 참고값 |
| 테스트 [측정] | **86개 통과** (`unittest`, 3.7초) | **90개 통과** (`pytest`, 2.5초) | 둘 다 오프라인. 문서상 기대값(A 86개)과 같다. A는 sqlite 연결 미종료 `ResourceWarning`이 출력되지만 실패는 아니다 |

## 5. 이 환경에서 실행되지 않는 부분 (고치지 않고 기록)

| 무엇 | A | B |
|---|---|---|
| 서버 기동 | 됨 | 됨 (`/health`: `llm_key: false`) |
| 핵심 기능 | **복기 계산은 됨** (로컬 SQLite만 사용). **문장 읽기는 안 됨**: OpenAI 키 없음 + `api.openai.com` 차단 | **선출 추천 안 됨**: ① LLM 키 없음(`INVALID_KEY`) ② `pokeapi.co`, `www.smogon.com`, `play.pokemonshowdown.com` 모두 프록시 403 (`UPSTREAM_ERROR`). 한국어 이름 검색만 로컬 데이터로 됨 |
| 확인된 네트워크 [측정] | 허용: `pypi.org`, `api.anthropic.com`, `generativelanguage.googleapis.com` / 차단: `api.openai.com`, `pokeapi.co`, `www.smogon.com`, `play.pokemonshowdown.com`, `gms.ssafy.io` | |

## 6. 비교 조건에 영향을 주는 관찰 [해석]

- **데이터 시점이 다르다.** A는 빌드된 SQLite 스냅숏(Smogon 2026-09, pokedb M-6까지)을 쓰고, B는 실행 시점의 외부 API를 부른다. 같은 대전 상황이라도 상대 예상 세트가 다를 수 있다. B는 첫 수집 후 `backend/.cache`를 고정해 재실행 때 같은 데이터를 쓰게 할 것을 제안한다.
- **LLM 의존 위치가 다르다.** A는 LLM이 실패해도 칸 직접 입력으로 핵심 계산을 쓸 수 있고, B는 `/api/chat` 전체가 LLM 키를 요구한다. 시나리오 S2는 두 앱 모두 LLM을 켠 상태로 맞춰야 공정하다.
- **익명화 대상 흔적.** A의 코드 주석에 설계·리뷰 절차 번호(`eng #3 R1`, `CEO C3-1`, `D25`, `DESIGN.md` 등)가 다수 있다(예: `prep/review.py` 13곳). A 루트에는 `CLAUDE.md`, `DESIGN.md`, `skills-lock.json`, `.agents/`, `prep/.agents/`가 있다. B 주석에는 과정 요구사항 번호(`F3001` 등)와 `SSAFY GMS`가 있다. Phase 4 패킷에서 양쪽 모두 같은 규칙으로 지운다.
- Python 버전: 원 작업은 3.12(A 문서 기준), 이 환경은 3.13. 테스트 결과에는 차이가 없었다.
