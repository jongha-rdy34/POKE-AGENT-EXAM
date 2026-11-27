# Design Review — 복기 탭 (/plan-design-review, 2026-10-22)

대상: `docs/designs/loss-review-coach.md` v1.1(R8 반영본)의 화면 설계 — 복기 탭, 채팅 이어가기, 진행 상태·오류 표시.
인계: `docs/designs/HANDOFF-plan-design-review.md`. 원본 설계 문서는 엔지니어링 세션이 편집 중이라 **수정하지 않았다.** 아래 "설계 반영 제안"을 근거로 설계 본문을 개정한다.

- DESIGN.md 없음, `web/` 없음, gstack designer 미설치(`DESIGN_NOT_AVAILABLE`) → 목업 없이 텍스트 리뷰.
- 화면 분류: OPERATE(앱 화면). 마케팅 규칙 미적용.
- **2026-10-22 추가 지시:** 자연어 질의 우선(구조화 입력은 선택)과 첫 화면 배틀 영상·채팅 칸 배경은 `docs/designs/HANDOFF-design-implementation.md`에 기록했다. 이 지시가 DR4·DR10의 일부를 바꾼다. 아직 반영하지 않았다.
- 결정 번호 D1~D19는 이 리뷰의 질문 번호다(설계 문서 Eng Review의 D11~D18과 별개). 아래에서는 혼동을 막기 위해 **DR3~DR19**로 적는다.

## 설계 반영 제안 (사용자 승인된 결정)

### 정보 구조

- **DR3 결과 순서 (A):** ① 한 줄 결론(`summary`) + 「참고용」 배지·시즌 안내(U8) 한 줄 → ② 원인 행 최대 3개 → ③ 다음 대전 행동 1개(강조) → ④ 추가 질문 1개(버튼) → U7 선공기 문구(보조 글씨) → ⑤ 가정·미지원·근거 접힘. 서버 응답에 `summary`(결론 문장) 추가.
- **DR4 폼 구조 (A):** 필수 = 대결 줄 한 줄 `[내 포켓몬] ⇄ [상대 포켓몬] → [기술] → [결과]` + 「이 턴 복기하기」. ⇄ 버튼이 공격 측(`actor`)을 바꾸고, 각 포켓몬 옆에 "공격/방어" 글자를 표시. 선택 항목(내 빌드·SP·맞기 전 HP·flags·예상 결과)은 「더 정확하게」 접힘 안에 둔다. 펼치지 않아도 제출할 수 있다.
- **DR5 결과 선택지 (A):** 묶음 두 개, 문구에 포켓몬 이름을 넣는다.
  - 「맞은 결과」: "한카리아스가 한 방에 쓰러졌어요" / "한카리아스가 버텼어요"(이름 = 방어 측). "버텼어요"를 고르면 그 자리에 "맞은 뒤 남은 HP" 구간 칩 4개가 나타난다.
  - 「행동 순서」: "상대 망나뇽이 먼저 움직였어요" / "내가 먼저 움직였어요".
  - 묶음 제목 아래 안내: "가장 납득 안 되는 것 하나". 서버 계약(`actual.kind` 4종)은 바꾸지 않는다.
- **DR6 채팅 위치 (A):** 같은 탭에서 결과 바로 아래 입력창 1개를 둔다.
  - 입력창 위에 현재 턴 요약 "내 한카리아스 ← 지진 ← 상대 망나뇽"을 고정 표시.
  - 추가 질문(`ask`)은 누르면 입력창에 채워지는 버튼.
  - 「조건 고치기」(값 유지, 폼 다시 열기)와 「새 턴 복기」(비움)를 나눠 둔다.
  - 기록은 설계대로 상대 `form_key`에 쌓이고 채팅 탭에서도 보인다.

```
┌ 복기 탭 (최대 720px 한 열) ─────────────────────────┐
│ 어떤 한 턴이 납득 안 되나요?                         │
│ [내 한카리아스 · 방어] ⇄ [상대 망나뇽 · 공격]        │  ← 시각 앵커
│ [기술: 역린 ▾]   [결과: 한카리아스가 한 방에 쓰러졌어요 ▾] │
│ ▸ 더 정확하게 (빌드 · SP · 맞기 전 HP · 특수 상황 · 예상) │
│ [ 이 턴 복기하기 ]                                   │
└──────────────────────────────────────────────────────┘
        ↓ 제출 후 폼은 요약 한 줄로 접힘 (DR12)
┌──────────────────────────────────────────────────────┐
│ 내 한카리아스 ← 역린 ← 상대 망나뇽 · 한 방 [조건 고치기] │
│ ① 상대는 구애머리띠였을 가능성이 가장 커요   [참고용]  │  summary
│   계산 가정: 내 한카리아스 = 구애스카프(1위)·A32 고집,  │  assumption_line (DR9)
│   맞기 전 HP 가득                        [조건 고치기] │
│ ② 이 결과와 맞는 상대 도구 후보                        │
│   구애머리띠  ████████████░░  후보 중 62% · 16번 중 11번 한 방 │
│   생명의구슬  █████░░░░░░░░░  후보 중 25% · 16번 중 4번 한 방  │
│   도구 없음   ██░░░░░░░░░░░░  후보 중 13% · 16번 중 1번 한 방  │
│   상대 도구 중 채용률 18%는 계산할 수 없어 빼고 비교했어요 │
│ ③ 다음 대전: ……(강조)                                 │
│ ④ [상대가 랭크를 올린 상태였나요?]                     │
│   혹시 상대방이 신속/마하펀치와 같은 선공기를… (U7)     │
│ ▸ 가정 · 계산하지 않은 것 · 근거 3개                   │
│ ──────────────────────────────────────────────────── │
│ 내 한카리아스 ← 역린 ← 상대 망나뇽                     │
│ [ 이어서 물어보기…                          ] [보내기] │
└──────────────────────────────────────────────────────┘
```

### 상태 (DR7, A: 전체 상태표 채택)

| 상태 | 사용자가 보는 것 |
|---|---|
| 첫 화면(빈 폼) | "어떤 한 턴이 납득 안 되나요?" + 대결 줄 + 예시 버튼(누르면 폼에 예시를 채움) |
| 포켓몬 목록 로딩 | 선택기 안 "불러오는 중…", 제출 비활성 |
| 포켓몬 목록 실패 | "포켓몬 목록을 못 불러왔어요" [다시 시도] |
| 검색 결과 없음 | "'…'와 맞는 포켓몬이 없어요. 한글 이름으로 찾아보세요" |
| 입력 오류(서버 검증·SP 표기 실패) | 해당 칸 아래 문구(SP는 실패 이유 포함), 첫 오류 칸으로 포커스, 입력 유지 |
| 계산 중(SSE `status`) | 결과 자리에 3단계 줄: 계산 중 → 근거 찾는 중(수집 문서 제목) → 설명 쓰는 중. 버튼 "복기 중…" 비활성 |
| 부분(계산 결과 도착) | 결론·원인 행 즉시 표시, 설명 자리에 "쓰는 중" |
| 성공 | DR3 순서 |
| degraded(D16) | 원인 행 그대로 + 결론 위에 "설명 생성이 안 돼 기본 설명으로 보여 드려요. 계산은 정확해요" [설명 다시 받기] |
| 일치 0건 | 결론 자리에 "지금 계산 범위로는 설명할 후보가 없어요" + 미지원 목록을 펼친 채로 + 추가 질문 |
| 통계 없음 | 비중 대신 성립/불성립 행 + "이번 시즌 통계가 없어 도구별 비중은 계산하지 않았어요" |
| 참고용(flags 체크·미지원 내 도구) | 결론 옆 「참고용」 배지 + 이유 한 줄 |
| 우선도 기술 | 원인 행 대신 "우선도 +1이라 스피드와 관계없이 먼저 나가요" |
| 연결 끊김 | 계산 도착 전이면 "연결이 끊겼어요" [다시 복기](입력 유지). 도착 후면 결과를 유지하고 degraded와 같은 안내 |
| 서버 오류 | 오류 코드 + 안내 문구만(NF2004) [다시 복기] |
| 근거 0건 | 접힘 안 "이 답변에 인용된 근거가 없어요"(F2008) |
| 재제출(공통) | 이전 스트림을 중단한다. 늦게 도착한 이전 응답이 새 결과를 덮지 않는다 |

### 여정·신뢰

- **DR8 원인 표기 (A):** 제목은 "이 결과와 맞는 상대 도구 후보".
  - 행마다 가로 막대 + "후보 중 비중 N%" + "16번 중 k번 한 방"(k/16을 풀어 씀) + 성립 배분 한 줄.
  - 제외 비율이 0보다 크면 "상대 도구 중 채용률 N%는 계산할 수 없어 빼고 비교했어요"를 붙인다. 서버 응답에 `excluded_share` 추가.
  - 도구 비중(막대)과 난수(글자)는 다른 모양으로 보여 준다.
- **DR9 가정 표시 (A):** 결론 바로 아래 "계산 가정" 한 줄(`assumption_line`, 서버가 결과에 가장 큰 영향을 준 가정을 고름) + 「조건 고치기」. 나머지 `assumptions`는 ⑤ 접힘.

| 단계 | 사용자 행동 | 감정 | 받치는 결정 |
|---|---|---|---|
| 1 | 패배 직후 탭을 연다 | 짜증, 의문 | DR7 첫 화면 문구 + 예시 |
| 2 | 대결 줄을 채운다 | "금방 되겠네" | DR4, DR5, DR14 |
| 3 | 기다린다 | 초조 | DR7 3단계 진행 |
| 4 | 결론을 읽는다 | 납득 / 의심 | DR3 ①, DR8, DR9 |
| 5 | 다음 행동을 본다 | "다음엔 이렇게" | DR3 ③ |
| 6 | "어떻게 이겨?"를 묻는다 | 몰입 | DR6, DR15 |

### 화면 언어·토큰

- **DR10 레이아웃 (A):** 시각 앵커는 대결 줄 하나.
  - 결과는 한 열로 두고, 영역 사이는 여백 + 1px 구분선으로 나눈다.
  - 원인은 비교 행(도구명 | 막대 | 16번 중 k번)으로 그린다.
  - **카드·그림자·색 왼쪽 테두리·아이콘·이모지·그라데이션은 쓰지 않는다.**
  - 강조색은 다음 행동 한 곳에만 쓴다.
  - 모션은 상태 전환(진행 단계·결과 등장) 한 곳에만 두고, `prefers-reduced-motion`을 존중한다.
- **DR11 최소 토큰 (A):**
  - 글꼴: Pretendard(OFL, `web/fonts/`에 직접 둠), 숫자는 `font-variant-numeric: tabular-nums`.
  - 글자 크기: 결론 22/30 굵게, 본문 16/26, 보조 14/22.
  - 간격: 4·8·12·16·24·32.
  - 색 변수: `--bg --text --muted --line --accent`(다음 행동·포커스 전용) `--bar --warn`(참고용) `--danger`(오류).
  - 테마: 밝은 테마가 기본이고, `prefers-color-scheme: dark`에서 어두운 테마. 본문 대비 4.5:1 이상.
  - 구체 색값은 구현 때 대비 검사로 확정한다.
  - 선택 색·포커스 링·스크롤바도 이 변수로 칠한다.

### 반응형·접근성

- **DR12 반응형 (A):** 모든 폭에서 최대 720px 한 열. 제출하면 폼이 턴 요약 한 줄(DR6과 같은 줄) + 「조건 고치기」로 접히고 결과가 바로 아래에 온다.
  - 폰(<600px): 대결 줄을 3줄(두 포켓몬+⇄ / 기술 / 결과)로 나눈다.
  - 포켓몬·기술 선택은 전체 화면 검색 시트로 연다.
  - 채팅 입력창은 화면 하단에 고정하고, 키보드가 열리면 키보드 위로 올라간다.
  - 터치 대상은 44px 이상.
- **DR13 접근성 (A):**
  - 레이블: 보이는 `label`을 쓰고 placeholder만으로 대신하지 않는다.
  - 포켓몬·기술 선택기: ARIA combobox(↑↓ Enter Esc).
  - ⇄: `button` + `aria-label` "공격 측 바꾸기, 지금: 상대가 공격".
  - 결과 선택지: `fieldset` + radio. 접힘: `details/summary`.
  - 진행 단계: `aria-live="polite"`로 단계가 바뀔 때만 알린다(스트리밍 글자는 읽지 않음). 완료 때 "복기 결과가 나왔어요"를 한 번 알리고, 포커스는 빼앗지 않는다.
  - 오류: `aria-describedby`로 연결하고 첫 오류 칸으로 포커스.
  - 막대·배지는 글자로도 표시한다(색만으로 구분하지 않음).
  - 포커스 링: `--accent` 2px. 방문한 링크는 다른 색.

### 미해결이던 결정

- **DR14 기술 목록 (A):** `GET /api/moves?form_key=` — 공격 측 포켓몬의 `learnset` 중 `move.category`가 물리/특수인 것만 돌려준다. 응답 `[{move_key, name_ko, type, category, power}]`.
  - 공격 측을 바꾸면 기술 칸을 비운다.
  - 포켓몬을 고르기 전에는 기술 칸을 비활성으로 두고 "공격한 포켓몬을 먼저 골라 주세요"를 표시한다.
  - 목록에 없는 기술은 "목록에 없어요? 전체 기술에서 찾기"(`?q=`)로 찾는다.
  - 데이터는 SQLite에 이미 있다(`learnset(form_key, move_key, source)` 확인함).
- **DR15 턴 구분 (A):** 복기 응답에 `review_id`를 넣는다. 결과 아래 채팅은 `POST /api/chat`에 `review_id`를 실어 그 턴의 입력·답을 맥락으로 쓴다.
  - 채팅 탭 기록에는 복기마다 "복기: 한카리아스 ← 지진" 구분선을 넣는다.
  - 「조건 고치기」로 다시 돌리면 새 `review_id`가 생기고, 이전 결과에는 "이전 조건 기준"을 표시한다.
  - agent.md 1.2 표의 `/api/chat` 요청에 `review_id?` 추가 필요.
- **DR16 flags (A):** 제목은 "있었던 것만 체크(기억 안 나면 비워도 돼요)".
  - 「행동 순서」 결과일 때만 "순풍·트릭룸" 체크가 보인다(flags에 `speed_field` 추가).
  - 비운 항목은 서버가 `assumptions`에 "급소·날씨 등은 없었다고 가정"으로 넣는다. 결과가 빗나가면(일치 0건·낮은 비중) 그 가정을 추가 질문으로 묻는다.
- **DR17 SP 입력 (A):** 「더 정확하게」 안에 "내 한카리아스 SP [A20 S32]"·"상대 망나뇽 SP [  ]" 두 칸과 내 쪽 성격·도구 선택을 둔다.
  - 칸 값은 `my_build.sp`·`opp_build.sp`에 **문자열**로 보내고, 서버가 R8 파서·`check_sp`로 해석한다. 미러전도 칸으로 쪽이 정해진다.
  - 서버가 해석한 값("내 한카리아스: 공격 20, 스피드 32, 나머지 0")은 가정 줄(DR9)에 표시한다.
  - `text`는 채팅 경로 전용. R8의 "이름으로 쪽 결정"은 채팅에만 적용한다.
- **DR18 인용 (A):** 본문에는 작은 링크 "근거 n"만 둔다. 누르면 ⑤를 펼치고 해당 항목으로 이동·포커스한다.
  - 목록 항목: 제목 · 출처 종류 · "M-6 시즌 · 2026-10-21 수집" · 원문 링크(새 탭).
  - 시즌 안내(U8)는 결론 위 한 줄에만 둔다.

### API·계약 변경 요약 (엔지니어링 세션 확인 필요)

| 위치 | 변경 | 근거 |
|---|---|---|
| `POST /api/feature/review` 응답 | `summary`, `assumption_line`, `excluded_share`, `review_id` 추가 | DR3·DR9·DR8·DR15 |
| `POST /api/feature/review` 요청 | `flags`에 `speed_field`. `my_build.sp`·`opp_build.sp`는 "A20 S32" 문자열 | DR16·DR17 |
| `GET /api/moves?form_key=` / `?q=` | 신규 | DR14 |
| `POST /api/chat` 요청 | `review_id?` 추가 | DR15 |

## NOT in scope

- DESIGN.md(앱 전체 디자인 시스템): DR11에서 탭 단위 최소 토큰으로 정함. TODOS.md에 이관(DR19).
- 실제 색값: 구현 때 대비 검사로 확정(DR11).
- 시각 목업: gstack designer 미설치. 구현 후 `/design-review`로 시각 QA.
- 채팅 탭·조건 탐색 탭 화면: 이 리뷰 대상 밖(복기 탭만).
- 더블 배틀·상대 기술 입력: 설계 v1 범위 밖(U7 유지).

## What already exists

- agent.md 1.2의 SSE `status` 이벤트(`collecting/retrieving/generating`)와 인용 객체 형식 → 복기 진행 표시(DR7)와 근거 목록(DR18)에 그대로 쓴다.
- `.agents/skills/design-taste-frontend` 앱 화면 규칙(`references/app-screens.md`) → DR10 규칙과 같은 방향(카드 남용 금지, 조용한 구분선). 구현 때 참고.
- SQLite `learnset`, `move.category`, `move.priority` → DR14 기술 목록과 우선도 상태.
- 화면 코드(`web/`)는 아직 없다.

## Implementation Tasks
Synthesized from this review's findings. 구현 착수는 설계 개정·엔지니어링 재리뷰 이후(설계 D18). 순서는 U11(계산 → 서버 → 화면)을 따른다.

- [ ] **T1 (P1, human: ~2h / CC: ~10min)** — server — 복기 응답·요청 계약 확장(`summary`, `assumption_line`, `excluded_share`, `review_id`, `speed_field`, SP 문자열)
  - Surfaced by: DR3·DR8·DR9·DR15·DR16·DR17
  - Files: prep/review.py, server/ 복기 라우트, tests/test_review.py
  - Verify: `.venv/Scripts/python -m unittest discover -s tests -t .` — 제외 비율 0/양수, 미러전 SP 칸, 빈 flags 가정 문구 사례
- [ ] **T2 (P1, human: ~1h / CC: ~5min)** — server — `GET /api/moves?form_key=` / `?q=`
  - Surfaced by: Pass 7 — DR14
  - Files: server/ 라우트, tests
  - Verify: 한카리아스 form_key로 물리/특수 기술만, 변화기 0건
- [ ] **T3 (P1, human: ~1d / CC: ~40min)** — web — 복기 탭 폼(대결 줄, ⇄, 결과 두 묶음, 「더 정확하게」, 제출 후 요약 줄)
  - Surfaced by: Pass 1 — DR4·DR5·DR12
  - Files: web/index.html, web/style.css, web/app.js
  - Verify: 360px·1280px에서 필수 4칸만으로 제출, 폼이 요약 줄로 접힘
- [ ] **T4 (P1, human: ~1d / CC: ~40min)** — web — 결과 영역(DR3 순서, 비교 행, 가정 줄, 인용 링크) + 상태표 17행
  - Surfaced by: Pass 2·3 — DR3·DR7·DR8·DR9·DR18
  - Files: web/app.js, web/style.css
  - Verify: 서버 응답 고정본(fixture)으로 성공·degraded·일치 0건·통계 없음·우선도·연결 끊김·재제출 화면 확인
- [ ] **T5 (P2, human: ~4h / CC: ~20min)** — web — 결과 아래 채팅 + `review_id` 전달
  - Surfaced by: Pass 1·7 — DR6·DR15
  - Files: web/app.js, server/ chat 라우트
  - Verify: 같은 상대로 두 턴 복기 후 각 결과 아래 질문이 해당 턴 조건으로 답함
- [ ] **T6 (P2, human: ~4h / CC: ~20min)** — web — 접근성(combobox, aria-live, 오류 포커스, 포커스 링)
  - Surfaced by: Pass 6 — DR13
  - Files: web/app.js, web/index.html
  - Verify: 키보드만으로 폼 제출·결과 탐색, NVDA로 진행 단계만 읽힘
- [ ] **T7 (P2, human: ~2h / CC: ~10min)** — web — 토큰(CSS 변수, Pretendard, 크기·간격, 밝음/어두움)
  - Surfaced by: Pass 4·5 — DR10·DR11
  - Files: web/style.css, web/fonts/
  - Verify: 본문 대비 4.5:1(양 테마), 카드·그림자 0개
- [ ] **T8 (P3, human: ~15min / CC: ~2min)** — docs — agent.md 1.2 API 표에 `/api/moves`, `/api/chat`의 `review_id?` 추가
  - Surfaced by: DR14·DR15
  - Files: agent.md
  - Verify: 표에 두 항목 존재

JSONL artifact: skipped — jq not installed (install jq for /autoplan aggregation).

## Design Review Completion Summary (1차, 기록 보존)

```
  +====================================================================+
  |         DESIGN PLAN REVIEW — COMPLETION SUMMARY                    |
  +====================================================================+
  | System Audit         | DESIGN.md 없음, UI 범위 = 복기 탭 1개         |
  | Step 0               | 3/10, 7개 영역 전부(DR1)                      |
  | Pass 1  (Info Arch)  | 3/10 → 8/10 after fixes                      |
  | Pass 2  (States)     | 2/10 → 9/10 after fixes                      |
  | Pass 3  (Journey)    | 4/10 → 9/10 after fixes                      |
  | Pass 4  (AI Slop)    | 4/10 → 8/10 after fixes                      |
  | Pass 5  (Design Sys) | 1/10 → 7/10 after fixes                      |
  | Pass 6  (Responsive) | 1/10 → 9/10 after fixes                      |
  | Pass 7  (Decisions)  | 5 resolved, 0 deferred                       |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (5 items)                            |
  | What already exists  | written                                      |
  | TODOS.md updates     | 1 item proposed, 1 added (DR19)              |
  | Approved Mockups     | 0 generated, 0 approved (designer 미설치)    |
  | Decisions made       | 16 added to plan proposal (DR3~DR18)         |
  | Decisions deferred   | 0                                            |
  | Overall design score | 1/10 → 7/10                                  |
  +====================================================================+
```

- 점수 사유:
  - Pass 1(8): 모바일 첫 화면 범위는 DR12에서 정했다. 실제 화면에서 결론·가정·첫 원인이 한 화면에 들어가는지는 구현 후 확인이 필요하다.
  - Pass 4(8): 글꼴·색을 실제로 적용한 결과물이 아직 없다.
  - Pass 5(7): DESIGN.md가 없고 색값을 정하지 않았다(DR19 TODO).
  - 전체 점수는 가장 낮은 Pass 5를 따라 7/10이다.
- 외부 의견:
  - Codex: 실행은 됐지만 형식 검증 `unverified`(심각도 태그 형식 불일치). 외부 검증 완료로 치지 않는다.
  - Claude 하위 에이전트: 완료. 두 의견이 같이 지적한 항목은 DR3·DR4·DR7·DR8·DR10·DR11·DR14·DR6에 반영했다.

### Unresolved Decisions

없음. DR1~DR19 모두 사용자가 답했다.

## 1차 리뷰 리포트 (기록 보존)

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Outside Review | codex via `/plan-design-review` outside voice | Independent 2nd opinion | 1 | unavailable (codex verdict unverified; native Claude subagent completed) | 10 findings (codex, unverified) + native subagent findings, synthesized into DR3~DR18 |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 3 | issues_open | 24 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | issues_open | score: 1/10 → 7/10, 16 decisions |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **OUTSIDE COVERAGE:** codex, design, unverified (untagged_review); native Claude subagent (in-host) completed — not outside coverage.
- **VERDICT:** NOT CLEARED — eng review required.

# 재리뷰 #2 — CEO 결정 반영 (/plan-design-review, 2026-10-22)

대상: 같은 설계(v1.2) + `loss-review-coach.ceo-review.md`(CEO CLEAR, SCOPE REDUCTION) + `HANDOFF-design-implementation.md`.
**이 재리뷰가 1차 결정을 바꾸는 곳:** DR4(폼 필수 → 자연어 필수), DR8(% 막대 → 순위 + k/16), DR16(체크박스 → DR22), DR3 결론 문구(C-O3). 나머지 DR은 유지한다.

## 새 결정

- **DR20 (A) 첫 화면:** "어떤 한 턴이 납득 안 되나요?" + 자연어 칸 1개 + 예시 문장 + ▸ "아래의 사항을 기록해주시면 더 정확한 답변이 가능합니다 (포켓몬·기술·결과·빌드·특수 상황)" **접힘**. 키 없음·추출 실패면 펼친 채 둔다.
- **DR21 (A) 질문 분기:** 같은 칸에서 C1-1 추출이 "한 턴" / "규칙 질문"을 판단한다.
  - 한 턴이면 확인 단계로 간다.
  - 규칙 질문이면 그 자리에 근거 답변을 채팅 형식으로 낸다(S5 규칙 문서 인용).
  - 잘못 분류됐을 때를 위해 되돌리기를 둔다: 답변 위 "한 턴을 복기하려던 거예요? [복기로 바꾸기]", 확인 단계 "규칙만 궁금해요 [질문으로 바꾸기]".
  - 분류 결과는 C8-1 기록에 남긴다.
- **DR22 (A) 체크박스 10개:** 묶음 3개로 나눈다.
  - 「포켓몬 상태」 급소·화상·능력 변화·테라
  - 「필드」 날씨·필드·리플렉터·빛의장막
  - 「행동 순서」 트릭룸·순풍
  - 맞은 결과면 앞의 두 묶음을 보인다. 행동 순서 결과면 능력 변화 + 「행동 순서」를 보인다.
  - 추출이 숨은 칸을 체크하면 그 칸은 항상 보인다. DR16 문구 "있었던 것만 체크(기억 안 나면 비워도 돼요)"는 유지한다.

## 승인된 결정을 화면에 옮긴 것 (질문 없음)

- **확인 단계(C1-1):** 한 줄 문장 "내 한카리아스 ← 역린 ← 상대 망나뇽 · 한 방에 쓰러짐"을 보여 준다.
  - 각 조각(포켓몬·기술·결과)은 누르면 고칠 수 있는 칩이다. 칩은 DR13 combobox로 편집한다.
  - 추출하지 못한 조각은 빈 칩으로 강조한다.
  - 추출이 체크한 특수 상황 칩도 함께 보인다.
  - 버튼은 [이대로 복기](주)와 [더 정확하게 적기](「더 정확하게」 펼침) 두 개다.
- **원인 행(C-O1, DR8 대체):** 제목 "이 결과와 맞는 상대 도구 후보 · 가능성 높은 순"을 둔다.
  - 행 = 순위 1·2·3 + 도구명 + "16번 중 k번 한 방" + 성립 조건(배분·성격·특성). **% 숫자와 막대는 없다.**
  - "상대 도구 중 채용률 N%는 계산할 수 없어 빼고 비교했어요"는 유지한다. 이건 비중이 아니라 제외 범위 안내다.
  - CEO-T4 적중률이 확인되면 DR8 막대로 되돌린다.
- **결론·다음 행동(C-O3):** 결론은 "이 타격은 상대가 구애머리띠일 때 가장 잘 맞아요", 다음 행동은 "상대가 구애머리띠라면, …"처럼 조건을 붙인다.
- **"진짜 패인이었나"(C-O3·C8-1):** 결과 맨 아래(채팅 위)에 "이 턴이 실제로 진 이유였나요? [예] [아니요] [모르겠어요]" 한 줄을 둔다. 답은 기록만 하고 화면은 바뀌지 않는다.
- **출처 꼬리표 두 개(데이터 결정 2026-10-22):** 가정 줄·근거 목록에 "도구: pokedb M-6 싱글"과 "성격·SP·특성: Smogon 2026-09 · 레귤레이션 M-C · 1500+"를 따로 표기한다. 시즌 안내 문구(U8)는 유지한다.
- **참고용 사유 추가:** 감지 칸 체크(C-O2), 출처 간 위력 차이 13개 기술(C-O5: "출처 간 위력 차이 있음 — PokeAPI 100 / champions-data 120").
- **기록 안내(C8-1):** 첫 화면 자연어 칸 아래 보조 글씨 "복기 내용은 개선을 위해 기록돼요 · [삭제 요청]".
- **토큰(C3-1):** 초대 링크 없이 접속하면 전체 화면 "초대 링크로 접속해 주세요"(403), 상한을 넘으면 결과 자리에 "오늘 복기 횟수를 다 썼어요. 내일 다시 이용해 주세요"(429).

### 상태표 추가분 (DR7에 이어서)

| 상태 | 사용자가 보는 것 |
|---|---|
| 추출 중 | 자연어 칸 아래 "문장을 읽는 중…"(aria-live) |
| 확인 단계 | 위 "확인 단계" 그대로 |
| 추출 실패 / 키 없음 | "문장을 이해하지 못했어요. 아래 칸을 채워 주세요" + 「더 정확하게」 펼침, 원문 유지 |
| 규칙 질문 답변 | 근거 답변 + [복기로 바꾸기] |
| 403 | 전체 화면 초대 안내 |
| 429 | 결과 자리 안내, 입력 유지 |

### 바뀐 화면 흐름

```
[첫 화면: 자연어 한 칸 + ▸더 정확하게(접힘)]
      │ 제출
      ▼
 (추출 중) ──규칙 질문──► [근거 답변 + 복기로 바꾸기] ──► 결과 아래 채팅
      │ 한 턴
      ▼
[이렇게 이해했어요: 칩 문장 + 특수 상황 칩]──이대로 복기──►[진행 3단계]──►[결과: 결론 → 가정 줄(출처 2개) → 원인 순위+k/16 → 조건부 다음 행동 → 추가 질문 → U7 → 접힘 → "진짜 패인?" ]──►[채팅]
      │ 추출 실패·키 없음
      └──►[더 정확하게 펼침, 직접 입력]──제출──►(진행 3단계)
 초대 토큰 없음 → 403 화면 / 상한 초과 → 429 안내
```

## 재평가

| Pass | 재리뷰 전(낡음 반영) | 후 | 사유 |
|---|---|---|---|
| 1 정보 구조 | 5 | 9 | 첫 화면·분기·확인 단계 결정(DR20·21). 1점은 실제 화면에서 확인 필요 |
| 2 상태 | 7 | 9 | 상태 6개 추가 |
| 3 여정 | 8 | 9 | C-O1·C-O3 반영 |
| 4 화면 언어 | 8 | 8 | 막대 제거로 단순해짐. 실제 글꼴·색 적용물 없음 |
| 5 디자인 시스템 | 7 | 7 | DESIGN.md 없음(TODOS) |
| 6 반응형·접근성 | 9 | 9 | 칩 편집은 DR13 combobox 규칙 적용 |
| 7 미결 | — | 1 resolved(DR22), 0 deferred | |

Overall: 5/10 → 7/10 (가장 낮은 Pass 5).

**Stale Diagram Audit:**
- 1차의 폼 중심 와이어프레임과 % 막대 행은 위 "바뀐 화면 흐름"으로 대체한다.
- 프로토타입 `prototype/review-tab.html`은 아직 1차 기준이다(자연어 없음, % 표시). 갱신은 DT4에서 한다.

## Implementation Tasks (재리뷰 #2 추가)

- [ ] **DT1 (P1, human: ~4h / CC: ~20min)** — web — 첫 화면 자연어 칸 + 「더 정확하게」 접힘·자동 펼침 + 기록 안내 줄 (DR20, C8-1)
  - Files: web/index.html, web/app.js
  - Verify: 자연어만으로 제출, 키 없음 시 자동 펼침
- [ ] **DT2 (P1, human: ~4h / CC: ~20min)** — web — 확인 단계 칩 문장 + 규칙 질문 분기·되돌리기 (C1-1, DR21)
  - Files: web/app.js
  - Verify: 고정 응답 3종(한 턴·규칙·실패)으로 각 화면
- [ ] **DT3 (P2, human: ~2h / CC: ~10min)** — web — 원인 순위 행(% 없음), 조건부 문구, "진짜 패인?" 줄, 출처 꼬리표 2개, 체크박스 묶음 3개, 403/429 (C-O1·C-O3·C3-1·DR22)
  - Files: web/app.js, web/style.css
  - Verify: fixture로 각 상태
- [x] **DT4 (P3, human: ~2h / CC: ~15min)** — docs/designs/prototype — 프로토타입을 재리뷰 #2 기준으로 갱신 (2026-10-22, 상태 27개, `node --check` 통과, 헤드리스 Edge 760px로 1·4·5·8·13번 상태 확인)
  - Verify: `#state=N`으로 새 상태 확인

JSONL artifact: skipped — jq not installed.

## Design Review Completion Summary (재리뷰 #2)

```
  +====================================================================+
  |         DESIGN PLAN REVIEW — COMPLETION SUMMARY (재리뷰 #2)          |
  +====================================================================+
  | System Audit         | DESIGN.md 없음, CEO 결정으로 DR4·DR8·DR16 낡음 |
  | Step 0               | 변경 영역만 재검토                          |
  | Pass 1  (Info Arch)  | 5/10 → 9/10 after fixes                    |
  | Pass 2  (States)     | 7/10 → 9/10 after fixes                    |
  | Pass 3  (Journey)    | 8/10 → 9/10 after fixes                    |
  | Pass 4  (AI Slop)    | 8/10 → 8/10 after fixes                    |
  | Pass 5  (Design Sys) | 7/10 → 7/10 after fixes                    |
  | Pass 6  (Responsive) | 9/10 → 9/10 after fixes                    |
  | Pass 7  (Decisions)  | 1 resolved, 0 deferred                     |
  +--------------------------------------------------------------------+
  | NOT in scope         | 1차와 같음 + 첫 화면 영상(S7, TODOS)          |
  | What already exists  | 1차 + prototype/review-tab.html(구버전)      |
  | TODOS.md updates     | 0 items proposed (DESIGN.md 항목 유지)       |
  | Approved Mockups     | 0 generated (designer 미설치)                |
  | Decisions made       | 3 added (DR20~DR22)                         |
  | Decisions deferred   | 0                                           |
  | Overall design score | 5/10 → 7/10                                 |
  +====================================================================+
```

### Unresolved Decisions
없음.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | CLEAR | mode: SCOPE_REDUCTION, 0 critical gaps |
| Outside Review | codex via `/plan-ceo-review` | Independent 2nd opinion | 1 | completed | 6 findings; 6 resolved; 0 unresolved |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 3+ | ISSUES OPEN | 8 issues, 0 critical gaps (최신 행) |
| Design Review | `/plan-design-review` | UI/UX gaps | 2 | ISSUES OPEN | score: 5/10 → 7/10, 3 decisions |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **OUTSIDE COVERAGE:** 이번 재리뷰는 외부 의견 없이 진행했다. CEO 리뷰의 Codex 의견(completed)을 입력으로 썼다. 1차 디자인 리뷰의 Codex는 unverified였다.
- **VERDICT:** CEO CLEARED — eng review required (엔지니어링 리뷰 진행 중, 다른 에이전트). Design review issues_open: overall 7/10 (Pass 5, DESIGN.md 없음).

NO UNRESOLVED DECISIONS
