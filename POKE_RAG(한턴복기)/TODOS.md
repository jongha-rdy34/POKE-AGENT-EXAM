# TODOS

## 운영: 오늘 할 일 (2026-10-23, /office-hours 포트폴리오 전환)

설계: `docs/designs/portfolio-ops.md`. 순서는 위에서 아래로.

### O1 저장소 백업 — 오늘, PC 반납 전
- **What:** 첫 커밋을 만들고 비공개 GitHub 원격 저장소에 푸시한다. `.gitignore`에 있는 `data/raw/pokedb/`, `chroma_db/`, `data/logs/`는 별도 압축본으로 옮긴다. `.env`는 커밋하지 않고 메신저로도 보내지 않는다.
- **Why:** 커밋이 0개라 PC를 반납하면 전부 사라진다.
- **Context:** `docs/HANDOFF-machine-migration.md` 맨 위 ★ 절(GitHub 방식). 커밋은 사용자가 직접 한다.
- **상태 (2026-10-23):** 백업 압축본 `Desktop\AIpjt-backup-20261023.zip` 완료. 첫 커밋과 GitHub 푸시는 사용자가 할 차례다.

### O2 LLM 키 교체 — GMS 키 만료(2026-10-23)
- **What:** platform.openai.com에서 유료 API 키를 받는다(ChatGPT Plus는 API를 포함하지 않는다). `.env`의 `OPENAI_API_KEY`를 바꾸고 `OPENAI_BASE_URL`을 비운다. 그다음 임베딩 호환을 확인한다(HANDOFF-machine-migration 3번).
- **Why:** 키가 끊기면 자연어 입력과 요약이 멈춘다(계산표는 D16으로 남는다).
- **Context:** 2026-10-23 15:1x KST에는 `gpt-4o-mini` 호출이 성공했다.

### O3 친구 3명 테스트 판정 (C-O6)
- **What:** `data/logs/reviews.jsonl`의 friend1~3 기록과 `docs/friend-test-kit.md` 답변으로 계속·수정·중단을 판정한다.
- **Context:** 2026-10-23에 Pinggy 터널(60분 제한)로 링크를 보냈다. `.env`의 `INVITE_TOKENS`에 friend1~3이 있다.
- **상태 (2026-10-23):** 1차 테스트 완료, 사용자 피드백 작성 완료 → `docs/HANDOFF-friend-test-1.md`(F1~F12). 판정은 테스트 뒤 질문 A~E 답을 받으면 내린다.

### O4 클라우드 배포 + 퍼널 + 개선 일지 (설계 B)
- **What:** Dockerfile, 영구 디스크가 있는 VM, GitHub Actions(테스트 → 배포), HTTPS, `visit` 이벤트와 퍼널 집계, `/changelog`.
- **Depends on:** O1, O2. VM 업체·비용 한도·도메인은 사용자가 정한다(설계 Open Questions 1·2).

## ~~앱 전체 DESIGN.md 만들기 (/design-consultation)~~ — 완료 2026-10-23

루트 `DESIGN.md`(spec 형식 검사 통과). taste-skill 검수 0 FAIL·0 WARN. 남은 일: 프로토타입 `docs/designs/prototype/review-tab.html`을 DESIGN.md 색 배치(청록 = 1순위 데이터, 주 버튼 검정)에 맞추기.

### (기록) 원래 항목

- **What:** 복기 탭 최소 토큰(`docs/designs/loss-review-coach.design-review.md` DR11)을 앱 전체 DESIGN.md로 옮기고, 채팅·조건 탐색 탭까지 넓힌다. 실제 색값도 정한다.
- **Why:** 탭이 늘어나면 토큰이 탭마다 갈라진다. 지금은 색값이 정해져 있지 않다.
- **Pros:** 탭끼리 일관성이 생기고, 색값이 확정되고, 다음 디자인 리뷰가 DESIGN.md 기준으로 채점된다.
- **Cons:** 별도 세션이 필요하다(human: ~반나절 / CC: ~30분).
- **Context:** 2026-10-22 /plan-design-review에서 DESIGN.md 대신 탭 단위 최소 토큰을 택했다(DR11 A). Pass 5가 7/10에 머문 이유다.
- **Depends on / blocked by:** 4단계 화면 골격(`web/`) 이후가 적기.

## 최소 복기 이후로 미룬 범위 (CEO 리뷰 2026-10-22, SCOPE REDUCTION)

모두 `docs/designs/loss-review-coach.ceo-review.md` 0G 표의 결정이다. 공통으로 **친구 3명 테스트(The Assignment) 결과를 보고 순서를 정한다**. 이 테스트에서 "확인 불가"가 가장 많이 나온 항목을 먼저 한다.

### S1 특수 계산 기술 분기 (U6·R9)
- **What:** 바디프레스·속임수·사이코쇼크·연속기·고정 데미지·무게 의존·HP 비례 기술의 예외 계산.
- **Why:** 일반 공식으로 계산하면 틀린다. 지금은 "확인 불가: v1 미지원 기술"로 보류한다.
- **Pros:** 커뮤니티 사례 A4(해수스파우팅) 같은 턴에 답할 수 있다. **Cons:** 기술별 Showdown 대조 테스트가 필요하다(human ~1일 / CC ~40분).
- **Depends on:** `damage_rolls` 완료.

### S2 체크박스 계산 확장 (D28)
- **What:** 화상(물리 0.5)·리플렉터·빛의장막(0.5, 급소 시 무시)의 **계산**.
- **Why:** 감지 칸은 남긴다(CEO D17 A, Codex O2). 체크박스는 10개(급소·날씨·능력 변화·테라·트릭룸·화상·리플렉터·빛의장막·순풍·필드)이고, 자연어에 언급되면 추출이 미리 체크한다. 체크되면 "확인 불가·참고용"으로 표시한다. 미룬 것은 계산뿐이다.
- **Pros:** 흔한 보정 두 개의 확률 숫자가 나온다. **Cons:** 입력 칸이 늘어난다. 디자인 DR16(`speed_field`)과 D28(`tailwind`·`terrain`)의 이름도 맞춰야 한다.

### S3 상대 기술 선택 입력 + 우선도 비교·재계산 (D29)
- **What:** 상대 기술을 입력받아 우선도를 비교하고, 선공기 질문에 답하면 다시 계산한다.
- **Why:** 지금은 "상대가 우선도 0 기술을 썼다는 가정" 표시와 U7 문구만 있다.
- **Context:** 자연어 입력(C0)에서 "신속"을 언급하면 같은 입력으로 쓸 수 있다.

### S4 회복 열매 보조 문구 (D27, 사용자 지정 문구)
- **What:** 후보에 자뭉·오랭열매가 있으면 다시 계산해서, 결과가 달라질 때만 "자뭉열매 포함 시 확정 3타까지 늘어납니다"를 붙인다.
- **Why:** 여러 타(확정 n타) 질문에서 의미가 있다. 한 방 복기에는 영향이 적다.

### S6 조건 탐색(F2011)·결정력 계산기·시즌 메타 리포트 별도 화면 (agent.md 7절)
- **What:** 화면 2개와 `/api/search`, `/api/feature/calc`·`meta` 화면을 만든다.
- **Why:** 제출 의무가 사라져(CEO C1) 미뤘다. 복기는 내부에서 계산기·메타 통계를 재사용한다.
- **Context:** 나중에 SSAFY 제출이 다시 필요해지면 F2011이 필수다.

### S7 첫 화면 배틀 영상·채팅 칸 배경
- **What:** `docs/designs/HANDOFF-design-implementation.md` 지시 2 그대로.
- **Depends on:** 영상 준비, IP 검토(전제 4).
