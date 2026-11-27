# 인계장: /plan-ceo-review (병렬 세션용)

작성 2026-10-22 · 보낸 세션: /office-hours → /plan-eng-review ×2 진행 세션(지금 계산기 구현 중)

## 먼저 읽을 것 (충돌하면 위가 우선)

1. `agent.md` — 프로젝트 전체 계획. 1.3절 데이터 우선순위와 8절 명세 요구사항(F2001–F2016, NF2001–NF2007)이 모든 것에 우선한다.
2. `docs/designs/loss-review-coach.md` — 승인된 설계(본문 v1.2) + 엔지니어링 리뷰 #1·#2 결정 기록(D11~D30, R1~R20). 본문과 결정 기록이 다르면 결정 기록이 우선.
3. `docs/designs/loss-review-coach.design-review.md` — 디자인 리뷰 결과(DR1~DR17).
4. `docs/designs/community-cases.md`, `data/eval/community_cases.jsonl` — 커뮤니티 혼동 사례 51건(평가셋, verified=false).

## 리뷰 대상과 관점

- 대상: `docs/designs/loss-review-coach.md`의 제품 범위와 방향.
- 이 프로젝트는 SSAFY 과제(명세 필수 요구사항 준수)이면서, 사용자는 랭크배틀 뉴비 대상 서비스·광고 수익화 가능성도 보고 있다(설계 문서 Premises 4·5, 유료 구독은 하지 않음, 포켓몬 IP 위험 인지).
- 엔지니어링 리뷰 #2 이후 v1 범위가 크게 늘었다(특성 5종, 방어 도구, 특수 기술 분기, SP 직접 입력, 체크박스 10개, 상대 기술 선택 입력, 회복 열매 보조 문구, 규칙 문서 선수집, 평가 분리). 이 범위가 과제 마감과 뉴비 입력 부담에 맞는지가 핵심 질문이다.

## 실행 방법

- gstack 하위 스킬이 개별 등록돼 있지 않다. 새 세션에서:
  > `~/.claude/skills/gstack/plan-ceo-review/SKILL.md`를 읽고 그대로 실행해. 대상은 docs/designs/loss-review-coach.md. 먼저 docs/designs/HANDOFF-plan-ceo-review.md를 읽어.
- **보고는 별도 파일에 쓴다:** `docs/designs/loss-review-coach.ceo-review.md`. `loss-review-coach.md`·`agent.md`는 다른 세션이 동시에 편집하므로 직접 수정하지 않는다(변경은 보고 파일에 제안으로).
- 코드를 만들지 않는다(리뷰만).

## 이미 진행 중인 것 (CEO 리뷰 결과와 무관하게 남는 기반 작업)

- `prep/build_db.py` 도구 전체 분포 저장(D24), `current_season(db)`(D13), `prep/calculator.py`의 `damage_rolls`·`speed`·`item_kind`(D14·D17). 이 세 가지는 어떤 범위에서도 필요해서 먼저 구현한다.
- 복기 로직(`prep/review.py`)·서버·화면은 CEO 리뷰 결과를 본 뒤 착수한다.

## 알려진 불일치 (참고)

- 디자인 리뷰는 "상대 기술 입력 v1 범위 밖(U7 유지)"이라 적었지만 엔지니어링 리뷰 #2 D29가 상대 기술을 **선택 입력**으로 추가했다. 체크박스 이름도 디자인 리뷰 `speed_field` vs D28 `tailwind`·`terrain`. 서버 계약 단계에서 정리 예정.
- M-7(현재 시즌) 사용률 통계 출처 없음 — agent.md 10절.

## 공유 사항

- **T7 보류 (2026-10-22 사용자 결정):** 현재 진행 중인 시즌 M-7의 데이터를 확보할 방법이 없는 동안 답변의 기준 시즌은 pokedb에서 받을 수 있는 **M-6**이다. T10을 먼저 진행하고, M-7 데이터를 확보할 수 있는지 파악한 뒤 T7(색인 본문에서 시즌 통계 제거, D26)의 진행 여부를 다시 검토한다. 그때까지 `pokemon_meta` 색인 본문과 `current_season(db)`는 M-6을 가리키며, 답변에는 U8 문구("이 정보는 M-6 시즌 통계를 기준으로 검색되었습니다")를 쓴다.
- **통계 출처 결정 (2026-10-22 사용자):** 도구·채용률·동반은 pokedb M-6(실제 게임 상위 구축) 우선, 성격·SP 배분·특성 분포는 Smogon 월간 통계 `gen9championsbssregmc`(Showdown, 레귤레이션 M-C, 1500+)로 보충. 출처·시점 표기 필수. agent.md 1.3절 4·2절 표 참고. championsbattledata는 채택 안 함(개인·교육 한정 조건, 원천 미공개).
- **통계 이중 기준 (2026-10-22 사용자, 설계 v1.3·D31·D32):** Smogon 지난달 데이터를 사실상 최신 시즌으로 간주. 코드가 pokedb M-6 기준과 Smogon 기준으로 각각 계산하고, 차이가 유의미하면(복기: 원인 1순위 도구가 다르거나 확률 20%p 이상, 통계: 1위 도구·특성·성격이 다르거나 채용률 10%p 이상) 답변에 양쪽을 표기하며 Smogon에는 "Pokémon Showdown(시뮬레이터) 환경에서 수집된 데이터"를 명시. LLM 호출은 1회(출처별 근거 블록). 화면에도 두 출처 비교 표시가 필요할 수 있음.
