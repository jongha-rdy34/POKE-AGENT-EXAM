## Start here (처음 보는 agent)

포켓몬 챔피언스 랭크배틀 뉴비를 위한 "한 턴 복기 코치"다. FastAPI(`server/`) + 순수 HTML/JS(`web/`), 데미지 계산(`prep/calculator.py`)과 시즌 통계로 "왜 졌지 → 상대가 뭘 들었지 → 어떻게 이기지"에 답한다. 비상업 포트폴리오 프로젝트다(수익화 없음).

읽는 순서:
1. `docs/HANDOFF-machine-migration.md` 맨 위 ★ 절: 환경 복구(GitHub + 백업 압축본), 설치할 스킬
2. `docs/HANDOFF-friend-test-1.md`: 1차 친구 테스트 피드백 → 다음 작업 우선순위(F1~F12)
3. `TODOS.md` 맨 위 "운영" 절(O1~O4)과 미룬 범위(S1~S7)
4. `docs/designs/portfolio-ops.md`: 배포·사용자 추적 설계(승인됨)
5. `docs/designs/loss-review-coach.md`: 제품 설계. 맨 위 배너(개정 v1.4 계산 우선)부터 읽는다. 뒤쪽 Eng Review의 D·R 번호 결정과 `loss-review-coach.ceo-review.md`의 C 번호 결정은 다시 논의하지 않는다
6. `agent.md` 1.1~1.3(스택·데이터 우선순위), 2(출처·이용 조건), 9~10(체크리스트·위험)
7. `docs/agent-memory/`: 이전 agent의 메모리 사본(사용자 선호·결정 배경)

실행:
- 테스트: `.venv/Scripts/python -m unittest discover -s tests -t .` (2026-10-23 기준 86개 통과)
- 서버: `.venv/Scripts/python -m uvicorn server.app:app --port 8000 --no-access-log` → `http://127.0.0.1:8000/?t=<비밀값>` (`.env`의 `INVITE_TOKENS=이름표:비밀값`)

지켜야 할 사용자 지시:
- **커밋은 사용자가 직접 한다.** agent는 커밋·푸시하지 않는다.
- 데이터 우선순위는 PokeAPI > pokedb(도구·채용률) > Smogon(성격·SP·특성 보충)이고, champions-data는 빈칸 보충 전용이다. 시즌은 pokedb M-6까지이고, 그 뒤는 Smogon(시뮬레이터) 기준이다. 두 기준이 크게 다르면 둘 다 보이고 Smogon은 시뮬레이터 데이터라고 밝힌다.
- pokedb는 오픈데이터 파일만 쓴다(페이지 크롤링 금지). Bulbapedia 요청은 5초 간격을 둔다.
- 계산은 시중 계산기(스마트누오·Showdown)와 같은 결과를 내야 한다. 친구 사례 기대값은 테스트로 고정돼 있다.
- `data/logs/`(친구 테스트 원문)는 커밋하지 않고 공유하지 않는다(친구 동의 범위).

## Design System
Read DESIGN.md before visual or UI work: it defines the fonts, colors, spacing, and
aesthetic direction. Ask the user before departing from it. When reviewing or QA-ing
UI, flag code that doesn't match DESIGN.md.
