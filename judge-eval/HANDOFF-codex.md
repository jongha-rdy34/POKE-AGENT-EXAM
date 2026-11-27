# 인계장: Codex 세션 (독립 검증 담당)

작성 2026-11-27. 작업 지시 원문은 저장소 루트 `poke-judge-orchestration-prompt.md`다. **먼저 읽는다.**
배경: 포켓몬 웹 서비스 두 개(A, B)를 같은 조건에서 비교 평가한다. 두 앱은 모두 Claude로 만들었다. 그래서 **정답(기대값) 계산과 판정 하나는 Claude가 아닌 모델이 독립적으로 맡는다.** 이 세션이 그 역할이다.

## 1. 역할 분담
| 세션 | 맡는 것 | 쓰는 파일(소유) | 브랜치 |
|---|---|---|---|
| Claude | 캡처, 판정 패킷, Gemini·Claude 판정, 집계, 보고서 | `scenarios/ captures/ packets/ judges/ analysis/ run_all.py scripts/` | `claude/judge-eval` |
| **Codex (이 문서)** | ① Phase 3 객관 지표 ② OpenAI 판정 12건 | `objective/`, `judges/raw/openai/` | `codex/objective-openai` |

- 소유하지 않은 파일은 고치지 않는다. 특히 **앱 코드(`POKE_RAG(한턴복기)/`, `Poke-Agent-claude/`)는 절대 고치지 않는다.**
- 집계·보고서는 Claude 세션이 한다. 이 세션은 결과 파일만 만든다.

## 2. 작업 ① Phase 3 객관 지표 (지금 바로 시작 가능)
대상: 스피드와 데미지(결정력) 계산. 산출물:
- `objective/cases.yaml`: 테스트 케이스 10~20개. 케이스마다 입력(공격·방어 포켓몬, 기술, 배분, 성격, 도구, 특성), **기대값**, **기대값의 출처와 버전**(공식 계산식 문서 또는 기존 계산기 이름·버전).
- `objective/run_objective.py`: 각 앱의 계산 함수를 **읽기만 하고 import해서 호출**해 기대값과 비교.
- `objective/results.csv`: `case_id,app,expected,actual,verdict(정확|허용오차내|오답|기능없음),note`. 기능이 없으면 "기능없음"으로 적고 점수에 넣지 않는다.
- `objective/README.md`: 기대값을 어떻게 구했는지, 허용 오차 기준, 실행 방법, 막힌 점.

**기대값은 앱 코드나 앱 테스트를 보고 만들지 않는다.** 앱 코드는 "무엇을 호출할지" 알아내는 데만 읽는다. 기대값은 공개된 공식(Bulbapedia 데미지 공식, 능력치 공식)이나 독립 계산기(`@smogon/calc` npm 등)로 직접 계산한다.

두 앱의 계산 진입점 (확인한 것):
- A `POKE_RAG(한턴복기)/prep/calculator.py`: `actual_stats(db, form_key, sp, nature_key)`, `speed(db, build)`, `damage_rolls(db, attacker, defender, move_key)`(16개 난수, 급소·날씨·화상 없음), `attack_decisive_power(...)`. `db = calculator.connect()`(로컬 SQLite `data/processed/pokedex.sqlite`). 능력치 체계는 **포켓몬 챔피언스의 SP**: HP = 종족값+SP+75, 그 외 = floor((종족값+SP+20)×성격), SP는 스탯당 0~32·합계 66.
- B `Poke-Agent-claude/backend/app/domain/`: `stats.calc_stat(stat, base, points, nature, system)`, `stats.full_stats(...)`, `stats.system_for(fmt)`, `damage.damage_rolls(power, attack, defense, stab, effectiveness, ...)`, `damage.calc_move(move, attacker, defender, effectiveness, ...)`. 종족값은 호출자가 넘긴다(같은 종족값을 양쪽에 쓴다). 포맷 기본값 `gen9championsbssregmc`.
- 확인할 것: `@smogon/calc`가 챔피언스(SP 체계)를 지원하는지. 지원하지 않으면 SP 체계 공식으로 직접 계산하고 그 사실을 출처에 적는다. 가능하면 SP→EV 환산이 같은 결과를 주는 케이스(레벨 50, 개체값 31)도 대조한다.
- 케이스 구성 제안: 스피드 5개(성격·SP·구애스카프·랭크 ±1), 데미지 10개(자속·상성 2배/4배/0.5배/면역, 물리·특수, 도구 1~2종, 다단히트 1개), 경계 3개(SP 합계 초과, 존재하지 않는 기술, 면역).
- 시나리오에 나온 대면을 꼭 넣는다: 포푸니크 인파이트 → 한카리아스, 포푸니크 vs 팬텀 스피드, 한카리아스 vs 포푸니크 스피드(명랑·스피드 SP 32).
- 앱 로딩 시간과 Lighthouse 점수(가능하면)도 여기서 잰다: `objective/perf.csv`. 서버 실행 방법은 `judge-eval/HANDOFF-claude.md` 4절.

## 3. 작업 ② OpenAI 판정 12건 (Claude가 패킷을 만든 뒤, 사용자가 시작을 알려 준다)
- 입력은 `judge-eval/packets/codex/`만 쓴다. **판정할 때는 저장소의 다른 파일(앱 폴더, 인계장, `packets/mapping.secret.json`, 캡처 원본)을 열지 않는다.** 익명화가 깨진다. 가능하면 `packets/codex/`만 복사한 빈 폴더에서 새 Codex 세션(또는 `codex exec`)으로 실행한다.
- 건마다 새 대화로 시작한다: 절대 평가 X·Y 각 3회, 쌍비교 XY·YX 각 3회. 프롬프트 파일은 패킷 폴더 안 `runs.csv`에 적혀 있다.
- 응답 JSON을 고치지 않고 `judges/raw/openai/{run_id}.json`에 저장하고, `judges/raw/openai/log.csv`에 `run_id,시각,모델 이름,재요청 횟수`를 적는다. 형식이 틀리면 같은 대화에서 최대 2회 "출력 형식을 어겼습니다. 지정한 JSON 하나만, 다른 글자 없이 다시 출력하세요."를 보낸다.
- 검사: `python judges/import_manual.py judges/raw/openai` (ChatGPT용과 같은 스크립트).
- 기록할 조건: 실제 모델 이름, temperature 지정 불가 여부, 추론 강도 설정. 판정 중 도구(파일 읽기·웹 검색)를 쓰지 않았는지.

## 4. 환경
```bash
python -m venv ../venvs/A && ../venvs/A/bin/pip install -r "POKE_RAG(한턴복기)/requirements.txt"
python -m venv ../venvs/B && ../venvs/B/bin/pip install -r Poke-Agent-claude/backend/requirements.txt pytest
```
- 객관 지표는 LLM 키 없이 된다(계산 함수 직접 호출). B의 외부 데이터가 필요하면 `CACHE_DIR=judge-eval/apps_cache/B`를 쓴다(2026-11-27 고정본).
- Windows Git Bash면 `bin` → `Scripts`.

## 5. 지킬 것
- 사실·측정·해석을 구분해 적는다. 수치를 추정해서 채우지 않는다. 계산이 안 되면 "막힘"으로 적고 사용자에게 알린다.
- 키는 `judge-eval/.env`에만. 출력·커밋하지 않는다.
- 결과는 "어느 앱이 더 낫다"가 아니라 케이스별 일치 여부만 적는다.
- 끝나면 무엇을 했고 무엇이 막혔는지 짧게 보고하고, `codex/objective-openai` 브랜치에 push한다.
