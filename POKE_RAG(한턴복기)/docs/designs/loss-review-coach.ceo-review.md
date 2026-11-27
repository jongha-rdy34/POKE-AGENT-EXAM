# CEO Review — /plan-ceo-review (2026-10-22)

대상: `docs/designs/loss-review-coach.md` 본문 v1.2 + 결정 기록(D11~D30, R1~R20).
함께 읽은 것: `HANDOFF-plan-ceo-review.md`, `loss-review-coach.design-review.md`(DR3~DR18), `HANDOFF-design-implementation.md`(자연어 우선·첫 화면 영상), `community-cases.md`.
설계 문서와 agent.md는 다른 세션이 편집 중이라 **수정하지 않는다.** 변경은 이 보고서에 제안으로 적는다.

## 사전 감사

- 커밋 0개, 원격 없음, stash 없음. 다른 세션이 계산기 기반 함수(`damage_rolls`·`speed`·`item_kind`)를 구현 중이고, T6(도구 전체 분포)은 완료.
- TODOS.md: DESIGN.md 1건(디자인 리뷰 DR19).
- 시장(2026-10-22 웹 검색):
  - [Championite](https://193-122-133-254.sslip.io/): 사용률로 상대의 미공개 세트를 추정하는 배틀 보드.
  - [Pikalytics](https://www.pikalytics.com/ai/damage-calculator): 데미지 계산기.
  - [Ai Rotom](https://mcpmarket.com/server/ai-rotom): AI 배틀 조언 MCP.
  - 모두 배틀 전 준비용이고 영어다. **패배 뒤 복기 + 한국어는 비어 있다.**
  - 공식 대회는 VGC 더블이다. 리텐션(이탈률) 공개 데이터는 찾지 못했다.

## 사용자 답 (Step 0)

- **D1 마감:** "과제 제출 자체가 필수가 아니게 되었으므로 고려하지 않아도 됩니다. 그러므로 이것을 확장해서 시행 중입니다." → 마감 제약 없음. SSAFY 명세 준수는 설계 Constraints에 남아 있으나 강제 기한은 없다.
- **D1 추가 사실:** GMS API 키가 2026-10-23 만료된다. ChatGPT Plus는 API를 포함하지 않는다(OpenAI 도움말·포럼 확인). 대체 경로는 `.env`의 `OPENAI_API_KEY` 교체와 `OPENAI_BASE_URL` 비움이다. 임베딩은 같은 모델(`text-embedding-3-small`)이면 재색인이 필요 없을 가능성이 크다. 단 확인 전이다(저장 벡터와 새 임베딩 대조).
- **D2 포맷:** 주 사용자는 싱글 → v1 싱글 전용 전제 유지.

## 0A. 전제 점검

| 전제 | 주장 | 근거 | 판정 |
|---|---|---|---|
| P1 쐐기는 패배 진단 | 첫 화면·대표 질의 = 왜 졌지 | 설계 Premises 1, 경쟁 도구 전부 배틀 전 | 근거 있음(시장 공백 확인) |
| P2 최신 = 세 겹 | 시즌 꼬리표·필터·평가셋 | D11·D13·D26, T7 보류(M-6 기준) | 부분 — 현재 시즌 M-7 통계 없음, M-6 고정 |
| P3 명세가 먼저 | F2001–F2012 | Constraints | **변경됨** — 제출 필수 아님(D1). 명세는 품질 기준으로만 남음 |
| P4 수익은 광고뿐 | IP 위험 | Premises 4 | 유지. 첫 화면 배틀 영상(HANDOFF-design-implementation)이 IP 위험을 키움 |
| P5 이탈 원인 = 정보 격차 | 가설 | The Assignment 미확보, community-cases 51건 verified=false·URL 없음 | **unverified** |
| P6 싱글이 주 사용자 | v1 싱글 전용 | D2 사용자 답 | 사용자 진술 |

unverified=1 (P5). 사용자 진술만 있는 것: P6, 현재 시즌 M-7.

**두 가지 발견:**
1. 검증(The Assignment, 친구 3명)보다 범위가 먼저 커졌다. 엔지니어링 리뷰 #2에서 특성 5종, 방어 도구, 특수 기술, 체크박스 10개, 상대 기술 입력, 회복 열매 문구, 규칙 문서 선수집이 추가됐다.
2. 사용자의 "자연어 질의 우선" 지시(HANDOFF-design-implementation 지시 1)가 office-hours에서 기각한 **접근 A(채팅 + 진단 의도)**를 일부 되살린다. 기각 이유는 "뉴비가 무엇을 입력할지 몰라 정보 부족 질문이 대부분"이었다. 새 지시는 선택 항목과 안내 문구로 이 약점을 보완한다. 이 결정은 사용자의 직접 지시이므로 정해진 것으로 기록하고, 다시 묻지 않는다.

## 0B. 기존 코드 활용

| 하위 문제 | 재사용 |
|---|---|
| 실수치·SP 검증 | `prep/calculator.py` `actual_stats`·`check_sp` |
| 도구 보정 | `item_multiplier`(D17) |
| SP 별칭 | `prep/alias.py` 15종 |
| 사용률 | SQLite `meta_usage`(D24) |
| 기술 목록 | SQLite `learnset`·`move` |
| 근거 검색 | Chroma 두 컬렉션 |

## 0C. 12개월 이상형

```
지금                        이 계획(v1.2)                         12개월 이상형
계산기·색인만, 커밋 0  ---> 싱글 한 턴 복기 + 채팅,         --->  한국어 뉴비가 패배 직후 자연어 한 줄로
화면·서버 없음              입력 칸 10여 개, 친구 검증 0건        묻고 납득하는 복기(현재 시즌, 검증된 정확도)
```

## Decision ledger

| ID and owner | Contract and evidence | Current | Proposed | Status | Exact approval and scope |
|---|---|---|---|---|---|
| C0 사용자 | 자연어 질의 우선, 구조화 입력은 선택 (HANDOFF-design-implementation 지시 1) | 설계 v1.2 = 폼 구조화 입력 | — | approved(직접 지시) | 2026-10-22 사용자 메시지 "사용자의 자연어 질의를 우선하여 받고…". 접근 A 기각 이유를 선택 항목·안내 문구로 보완하는 형태. 파싱 주체·API 계약은 엔지니어링 미결 |
| C1 사용자 | 마감 | 미정 | 없음 | approved | D1 답: 제출 필수 아님, 확장 진행 |
| C2 사용자 | v1 포맷 | 싱글 | 싱글 | approved | D2 답: 주로 싱글 |

## Mode

Mode: SCOPE REDUCTION; approved decisions: C0,C1,C2. D3 답: "테스트용으로 최소 복기하겠습니다." → 친구 3명이 써 볼 수 있는 최소 복기를 목표로, 리뷰 #2까지 늘어난 항목을 하나씩 미룸(TODOS.md)/유지로 정한다.
- D3 부가 지시 (1): 2026-10-23 이후 노트북으로 이전 → `docs/HANDOFF-machine-migration.md` 작성 완료.
- D3 부가 지시 (2): `claude rc` 확인 → `claude rc` = `claude remote-control` 별칭(2.1.301, `--help` 동일). 이 VS Code 세션은 Remote Control에 연결돼 있지 않다(ListAgents에 RC 행 없음). 이어 가려면 터미널에서 `claude --resume` → `/remote-control`. 이 PC에서 실행되므로 PC가 꺼지면 끊긴다. 모바일 쪽 동작은 확인하지 못했다.

## 0G. 범위 축소 — 미룸/유지 후보 (각 항목 개별 결정)

최소 복기(유지 전제, 질문 안 함): C0 자연어 입력 + 선택 구조화 입력, `damage_rolls`·`speed`·`item_kind`(진행 중), 공격 측 도구 3분류, 16단계 난수 가중(D15), 결과 화면(DR3·DR7~DR9), degraded(D16), 현재 시즌 M-6 고정(T7 보류).

| ID | 항목 | 출처 | Status | 답 |
|---|---|---|---|---|
| S1 | 특수 계산 기술 분기(바디프레스·속임수·사이코쇼크·연속기·고정·무게·HP 비례) | U6·R9 | deferred | D4 A — "확인 불가: v1 미지원 기술" 안전망만 유지 |
| S2 | 체크박스 계산 확장: 화상·리플렉터·빛의장막 계산 + 필드·순풍 칸 | D28 | deferred | D5 A — 체크박스는 급소·날씨·능력 변화·테라·트릭룸 5개, 체크 시 "확인 불가·참고용" |
| S3 | 상대 기술 선택 입력 + 우선도 비교·재계산 | D29 | deferred | D6 A — "상대가 우선도 0 기술을 썼다는 가정" 표시 + U7 문구만 유지 |
| S4 | 회복 열매 보조 문구 | D27 | deferred | D7 A — 회복 열매는 "이 타격에 영향 없음"으로 계산 |
| S5 | 규칙 문서 40~60개 선수집 + 혼동 사례 라벨 대조 | D23·T10 | **kept** | D8 B — 자연어 입력창으로 들어올 규칙 질문의 근거 |
| S6 | 조건 탐색 화면(F2011)·결정력 계산기/시즌 메타 리포트 별도 화면(agent.md 7) | agent.md | deferred | D9 A — 복기 내부 재사용만 |
| S7 | 첫 화면 배틀 영상·채팅 칸 배경 | HANDOFF-design-implementation 지시 2 | deferred | D10 A — 지침은 인계장에 보존 |
| S8 | 방어 측 도구(돌격조끼·기합의띠·반감 열매·풍선) | U2 | **kept** | D11 B |
| S9 | 특성 5종 계산(천하장사·순수한힘·적응력·테크니션·멀티스케일) | U5 | **kept** | D12 B |
| S10 | 복기 정답 사례 10건(Showdown 대조) 평가 | D30·T11 | **kept** | D13 B — 친구 테스트 전에 오진율 측정 |

### 축소 후 최소 복기 범위 (accepted)

- **입력:** 자연어 한 칸(C0) + 선택 구조화 입력(대결 줄·결과 선택지·「더 정확하게」: 내 빌드·SP 칸·맞기 전 HP·체크박스 5개·예상 결과).
- **계산:**
  - `damage_rolls`·`speed`·`item_kind`(진행 중)
  - 공격·방어 도구 3분류(U1·U2)
  - 특성 5종(U5), 위협 한 경로(D19·D21)
  - 16단계 난수 가중(D15), 도구 확률 숨김 규칙(D25)
  - SP 파서(D22)
- **근거:** SQLite 시즌 통계(M-6 고정, T7 보류) + 규칙 문서 선수집(D23).
- **출력:** DR3 순서, 상태표(DR7), 원인 표기(DR8), 가정 줄(DR9), degraded(D16).
- **검증:** Showdown 정답 10건(S10) → 친구 3명(The Assignment).
- **미룸:** S1·S2·S3·S4·S6·S7 → TODOS.md.

## 리뷰 섹션 결정 (ledger 계속)

| ID and owner | Contract and evidence | Current | Proposed | Status | Exact approval and scope |
|---|---|---|---|---|---|
| C1-1 Section 1 | 자연어 추출 주체 없음 (HANDOFF-design-implementation 미결) | 없음 | LLM 추출 → SQLite 검증 → 선택 칸 미리 채움 → "이렇게 이해했어요" 확인 | approved | D14 A — 키 없음·실패 4유형(깨진 JSON·빈 응답·지어낸 키·거절) 시 직접 입력 칸, SP는 D22대로 코드만, 추출 정확도 평가 문항(커뮤니티 51건 원문 + 친구 원래 말) 포함 |
| C3-1 Section 3 | 임시 터널로 유료 키 노출 (Distribution Plan) | 보호 없음 | 초대 토큰(?t=) 없으면 403, 토큰당 하루 상한(예: 50) 초과 429 + 안내, OpenAI 월 한도 설정 | approved | D15 A |
| C8-1 Section 8 | TODOS 순서를 정할 "확인 불가" 횟수 기록 없음 | 없음 | `data/logs/reviews.jsonl`: 토큰·원문·확인된 값·추출 수정 여부·원인·unsupported·degraded·응답 시간, 집계 스크립트, 키·프롬프트 제외, 첫 화면 기록 안내 | approved | D16 A — 동의·삭제 요청 처리 포함 |

## 섹션별 기록

- **S1 Architecture:** CRITICAL GAP 1건(자연어 추출) → C1-1. API 키 하나가 추출·임베딩·생성을 모두 쥔 단일 장애점이다. 계산은 D16으로 보존된다.
- **S2 Error & Rescue:** 기능 단위 지도. GAP 0건(C1-1·D16·DR7로 처리).
- **S3 Security:** 터널 노출 WARNING → C3-1. 프롬프트 인젝션은 "LLM은 판정하지 않는다" + SQLite 검증으로 숫자에 영향 없음.
- **S4 Data/UX:** 엣지 케이스 7개(빈 문장·긴 문장·미러전·키 없음·두 번 제출·확인 전 수정·토큰 상한). 미처리 0건.
- **S5 Quality:** 코드 없음. 리뷰 #2의 `prep/review.py` 함수 분리 기록 유지.
- **S6 Tests:** 새 테스트는 모두 승인 범위 안(C1-1 실패 4유형·추출 정확도, C3-1 403/429, S10). 추출 단위 테스트는 LLM 고정 응답 사용(흔들림 방지).
- **S7 Performance:** 추출 LLM 호출 1회 증가. R3-10(응답 시간 목표 수치 없음)은 열린 채 기록.
- **S8 Observability:** CRITICAL GAP 1건(친구 테스트 기록 없음) → C8-1.
- **S9 Deploy:** 노트북 이전 = 배포(HANDOFF-machine-migration). `data/logs/`를 `.gitignore`에 넣는다(C8-1 개인정보 범위).
- **S10 Trajectory:** 되돌리기 쉬움 4/5. 문서 빚: agent.md 1.2 API 표(`/api/moves`·`review_id`·`text`·초대 토큰)와 디자인 DR4(폼 필수)가 C0·C1-1과 어긋난다.
- **S11 Design:** 새 상태 3개(확인 단계·추출 실패→직접 입력·토큰 403/429)가 DR7에 없다. 구현 전 `/plan-design-review` 재실행 권장(HANDOFF-design-implementation에 이미 기록).

```
[첫 화면: 자연어 한 줄]──제출──►[이렇게 이해했어요]──확인──►[진행 3단계]──►[결과 DR3]──►[결과 아래 채팅]
      │                             │ 수정/추출 실패                                │
      │ 키 없음 ──────────────────────┴──►[직접 입력 칸]──제출─────────────────────────┘
      └ 초대 토큰 없음 → 403 안내
```

## Outside Voice (Codex, completed)

Codex gpt-6-astra, plan-review, `OUTSIDE_STATUS: completed`. 지적 6건(High 5, Medium 1). 결론: "Reduce the pilot to observed-hit explanations for actual friend cases, with explicit abstention and no inferred item percentages, because the current validation proves arithmetic rather than diagnostic accuracy."

| ID and owner | Contract and evidence | Current | Proposed | Status | Exact approval and scope |
|---|---|---|---|---|---|
| C-O1 Outside | 확률 = 채용률 × 균등 SP·성격·특성, 보정 미측정 (DR8·D15·D25) | DR8: "후보 중 비중 N%" 막대 + 제외 비율 | 친구 테스트는 % 숨김, "가능성 높은 순" 정렬 + "16번 중 k번" + 성립 조건. 내부 계산 유지. C-O4 평가로 상위 후보 적중률을 확인하면 % 복구 | approved | D18 B |
| C-O2 Outside | S2를 미루며 화상·벽 감지 입력까지 사라짐 (D5) | 체크박스 5개 | 계산은 미루고 감지 칸 5개(화상·리플렉터·빛의장막·순풍·필드) 추가 → 10개, 체크 시 "확인 불가·참고용", 자연어 언급 시 추출이 미리 체크. 테스트: 각 칸 체크 시 참고용 표시 | approved (D5 재개) | D17 A |
| C-O3 Outside | 한 타격 설명 ≠ 패인 | DR3 단정형 결론·다음 행동 | 결론은 "이 타격은 상대가 OO일 때 가장 잘 맞아요", 다음 행동은 "상대가 OO라면, …" 조건부. 프롬프트 3·degraded 템플릿에 같은 규칙. C8-1 기록에 "그 턴이 진짜 패인이었나" 질문 추가 | approved | D20 A |
| C-O4 Outside | S10이 계산 검산만 함 (tests/test_calculator.py:114) | 계산 일치 10건 | 가린 정답 평가: 상대 실제 빌드를 정해 결과를 만든 뒤 빌드를 가리고 전체 복기 → 상위 3 적중·보류·오진 분리 집계. 후보 밖 원인·입력 오기억 사례 각 2건 이상. 계산 일치는 "계산 검산"으로만 보고 | approved | D19 A |
| C-O5 Outside | 출처 간 위력 차이 13개 기술 [measured: data/processed/crosscheck_report.md:17] | PokeAPI 값, 표시 없음 | PokeAPI로 계산(agent.md 1.3 유지) + 13개 기술이면 assumptions에 "출처 간 위력 차이(PokeAPI X / champions-data Y)" + 참고용 | approved | D21 A. 사용자 메모: "가장 정확한 것은 bulbapedia에 나오는 것… 수치가 차이나는 경우에는 추후에 확인하며 정확한 데이터를 전달하겠습니다. 즉, 내가 패치노트를 전달하겠습니다. 계획에만 적어두세요." → 설계 Open Question 2(패치 노트 출처)의 답: **사용자가 패치 노트를 직접 제공.** 우선순위 규칙은 바꾸지 않음 |
| C-O6 Outside | 친구 테스트 통과·중단 기준 없음 | "자기 말로 설명"만 | 계속 = 3명 중 2명 이상이 원인을 자기 말로 설명 + "다음에 도움이 됐다" / 방향 수정 = 설명은 했으나 "그 턴은 패인이 아니었다"(C-O3 질문) 다수 / 중단 = 보류·확인 불가가 과반이거나 아무도 설명 못 함. C8-1 기록·C-O4 평가로 판정. 중단이면 미룬 TODOS를 열지 않고 전제 5를 다시 본다. 숫자는 사용자가 조정 가능 | approved | D22 A |

- O6의 다른 지적(S5 규칙 문서 유지가 필요한지 입증되지 않음)은 D8 B가 이미 답했다. 새 근거가 없어 유지한다(이견 기록).
- 사실 확인: 위력 차이 13개, 타입·우선도 차이 0개 [measured: crosscheck_report.md:17].

Approval readiness: PASS — C0(사용자 직접 지시), C1(D1), C2(D2), mode(D3), S1(D4 A)·S2(D5 A → D17 A로 감지 칸 복원)·S3(D6 A)·S4(D7 A)·S5(D8 B)·S6(D9 A)·S7(D10 A)·S8(D11 B)·S9(D12 B)·S10(D13 B → D19 A로 평가 방식 지정), C1-1(D14 A), C3-1(D15 A), C8-1(D16 A), C-O1(D18 B), C-O2(D17 A), C-O3(D20 A), C-O4(D19 A), C-O5(D21 A + 메모), C-O6(D22 A). 미해결 없음.

## NOT in scope

미룸 (TODOS.md):
- S1 특수 계산 기술 분기 — D4 A. "확인 불가" 안전망이 있어 미뤄도 오진이 없다.
- S2 화상·벽 **계산** — D5 A. 감지 칸은 D17 A로 남긴다.
- S3 상대 기술 입력·우선도 재계산 — D6 A. 가정 표시 + U7로 버틴다.
- S4 회복 열매 보조 문구 — D7 A. 여러 타 질문용이다.
- S6 조건 탐색·계산기·메타 별도 화면 — D9 A. 제출 의무가 없어졌다.
- S7 첫 화면 배틀 영상 — D10 A. 영상이 없고 IP 검토가 필요하다.

거절: 없음.
범위 밖(기존): 더블 배틀(C2 싱글), M-7 통계 출처(agent.md 10절).

## What already exists

| 하위 문제 | 기존 것 | 재사용 |
|---|---|---|
| 실수치·SP 검증 | `prep/calculator.py` `actual_stats`·`check_sp` | 예 |
| 도구 보정 | `item_multiplier`(D17 보존) | 예, `item_kind` 추가 |
| SP 별칭 | `prep/alias.py` 15종 | 예(D22 파서) |
| 사용률 | SQLite `meta_usage`(D24 전체 분포, T6 완료) | 예 |
| 기술 목록 | SQLite `learnset`·`move` | 예(DR14 `/api/moves`) |
| 출처 차이 | `prep/crosscheck.py`·`crosscheck_report.md` | 예(C-O5 13개 목록) |
| 혼동 사례 | `data/eval/community_cases.jsonl` 51건 | 예(C1-1 추출 평가 문장) |
| 화면 시안 | `docs/designs/prototype/review-tab.html` | 참고(C0 반영 전) |

## Dream state delta

이 리뷰 뒤의 계획은 12개월 이상형(자연어 한 줄 → 납득 가능한 복기, 검증된 정확도)에 두 가지로 가까워졌다.
1. 입구가 자연어 + 확인 단계로 바뀌었다.
2. 정확도를 "계산 일치"가 아니라 "가린 정답 적중"으로 잰다.

남은 거리는 다음과 같다.
- 현재 시즌 M-7 통계가 없다.
- 미룬 기능이 6개 있다.
- 더블 배틀은 다루지 않는다.
- 확률 표시는 보정이 확인된 뒤에야 복구한다.
- 실제 사용자 근거는 친구 3명뿐이다.

## Error & Rescue Registry (기능 단위, 전략 깊이)

| 기능 | 실패 방식 | 처리 | 사용자에게 보이는 것 | 구현 소유자가 증명할 것 |
|---|---|---|---|---|
| 자연어 추출 | 깨진 JSON·빈 응답·지어낸 키·거절 | C1-1: 직접 입력 칸 | "이해하지 못했어요, 아래 칸을 채워 주세요" / 빈 칸 강조 | 4유형별 테스트(LLM 고정 응답) |
| 자연어 추출 | 키 없음·만료 | C1-1 + D16 | 직접 입력 화면 | 키를 비운 상태로 전체 흐름 실행 |
| 입력 검증 | 없는 키·SP 오류 | NF2004 | 칸 아래 문구 | 오류 응답에 키·프롬프트·traceback 없음 |
| 초대 토큰 | 없음·상한 초과 | C3-1 | 403 / 429 안내 | 두 경우 테스트 |
| 역계산 | 일치 0건·통계 없음·감지 칸 체크·13개 기술 | 상태표 DR7, C-O2, C-O5 | 보류·참고용 표시 | 각 상태 fixture |
| 근거·생성 | 임베딩·LLM 실패 | D16 | degraded 안내 + 계산 결과 | LLM 실패·임베딩 실패 각각 테스트 |
| 기록 | 디스크 쓰기 실패 | 복기는 계속, 서버 로그에 경고 | 보이지 않음(사용자 흐름 유지) | 쓰기 실패 테스트. 기록 실패가 복기를 막지 않음 |

## Failure Modes Registry

```
  CODEPATH        | FAILURE MODE              | RESCUED? | TEST?        | USER SEES?         | LOGGED?
  ----------------|---------------------------|----------|--------------|--------------------|--------
  자연어 추출     | 오독(다른 포켓몬)          | Y 확인단계 | Y C1-1      | 이렇게 이해했어요   | Y C8-1(수정 여부)
  자연어 추출     | 키 만료                    | Y        | Y            | 직접 입력          | Y
  확률 표시       | 보정 안 된 % 과신          | Y C-O1   | Y C-O4       | 순위+k/16만        | -
  화상·벽 턴      | 감지 못 해 오진            | Y C-O2   | Y            | 참고용             | Y
  13개 기술       | 출처 위력 차이             | Y C-O5   | Y            | 참고용+assumptions | Y
  패인 오해       | 한 타격을 패인으로 표현     | Y C-O3   | 문구 테스트   | 조건부 문구         | Y(C-O3 질문)
  터널            | 키 남용                    | Y C3-1   | Y            | 403/429            | Y
  기록 파일       | 친구 문장 유출             | Y .gitignore·동의 | 확인 | 첫 화면 안내   | -
```
CRITICAL GAPS: 0 (S1·S8의 2건은 C1-1·C8-1로 해소).

## Diagrams

- 시스템 아키텍처: Section 1 그림(채팅 기록).
- 데이터 흐름 + 그림자 경로: Section 4.
- 화면 상태 흐름: Section 11(위).
- 오류 흐름: Error & Rescue Registry.
- 배포 순서: HANDOFF-machine-migration "노트북에서 확인할 것" 1~5.
- 롤백: 로컬 서버라 이전 폴더로 되돌린다(그림 생략, 단계 1개).

**Stale Diagram Audit:** 디자인 리뷰 보고서의 화면 그림(대결 줄이 앵커인 폼, `% 막대` 결과)은 C0·C-O1로 **낡았다.** 디자인 재리뷰 때 고친다. 설계 문서에는 ASCII 그림이 없다.

## Implementation Tasks
Synthesized from this review's findings. Each task derives from a specific
finding above. Run with Claude Code or Codex; checkbox as you ship.
(엔지니어링 세션의 T1~T11과 겹치지 않도록 CEO-T로 표기한다. 비율 가정: 기능 ~30x, 테스트 ~50x, 문서 ~10x.)

- [ ] **CEO-T1 (P1, human: ~1일 / CC: ~40min)** — prep/review.py·server — 자연어 추출 → SQLite 검증 → "이렇게 이해했어요" 확인 → 실패 시 직접 입력
  - Surfaced by: Section 1 — C1-1 (D14 A)
  - Files: prep/review.py, server/ 복기 라우트, tests/test_review.py, data/eval/
  - Verify: 실패 4유형 테스트(LLM 고정 응답) + 커뮤니티 51건 원문 추출 정확도 보고
- [ ] **CEO-T2 (P1, human: ~2h / CC: ~10min)** — server — 초대 토큰(403) + 토큰당 하루 상한(429) + OpenAI 월 한도 설정
  - Surfaced by: Section 3 — C3-1 (D15 A)
  - Files: server/, config.py, .env.example
  - Verify: 토큰 없음 403, 51번째 호출 429 테스트
- [ ] **CEO-T3 (P1, human: ~2h / CC: ~10min)** — server·data — `data/logs/reviews.jsonl` 기록 + 집계 스크립트 + `.gitignore` + 첫 화면 기록 안내 + "그 턴이 진짜 패인이었나" 질문
  - Surfaced by: Section 8 — C8-1 (D16 A), C-O3 (D20 A)
  - Files: server/, data/eval/aggregate_reviews.py, .gitignore, web/
  - Verify: 복기 1회 → 한 줄 기록, 키·프롬프트 없음, 쓰기 실패가 복기를 막지 않음
- [ ] **CEO-T4 (P1, human: ~반나절 / CC: ~30min)** — data/eval — 가린 정답 평가 10건(후보 밖 원인·입력 오기억 각 2건 이상)
  - Surfaced by: Outside Voice — C-O4 (D19 A), S10
  - Files: data/eval/, tests/
  - Verify: 상위 3 적중·보류·오진 분리 보고서. 계산 검산은 별도 표기
- [ ] **CEO-T5 (P1, human: ~1h / CC: ~5min)** — prep/review.py·web — 친구 테스트 표시: % 숨김, 가능성 순 + k/16 + 성립 조건. CEO-T4 적중률 확인 후 % 복구
  - Surfaced by: Outside Voice — C-O1 (D18 B)
  - Files: prep/review.py, web/app.js
  - Verify: 응답에 %가 보이지 않음, 정렬 순서가 내부 비중과 같음
- [ ] **CEO-T6 (P2, human: ~1h / CC: ~5min)** — prep/review.py·web — 감지 전용 체크박스 5개(화상·리플렉터·빛의장막·순풍·필드) + 추출 자동 체크
  - Surfaced by: Outside Voice — C-O2 (D17 A)
  - Files: prep/review.py, web/
  - Verify: 각 칸 체크 시 "확인 불가·참고용"
- [ ] **CEO-T7 (P2, human: ~1h / CC: ~5min)** — rag 프롬프트 3·degraded 템플릿 — 타격 단위 결론 + 조건부 다음 행동
  - Surfaced by: Outside Voice — C-O3 (D20 A)
  - Files: rag/ 프롬프트, prep/review.py 템플릿
  - Verify: 템플릿 출력에 "이 타격은"·"~라면" 포함 테스트
- [ ] **CEO-T8 (P2, human: ~1h / CC: ~5min)** — prep/review.py — 출처 간 위력 차이 13개 기술에 assumptions + 참고용 표시
  - Surfaced by: Outside Voice — C-O5 (D21 A)
  - Files: prep/review.py, prep/crosscheck.py 결과 사용
  - Verify: Beak Blast 복기 시 "출처 간 위력 차이" 표시
- [ ] **CEO-T9 (P2, human: ~30min / CC: ~5min)** — docs — 설계 Success Criteria에 판정 규칙(C-O6), Open Question 2에 "사용자가 패치 노트 제공"(C-O5 메모) 반영
  - Surfaced by: Outside Voice — C-O6 (D22 A), C-O5
  - Files: docs/designs/loss-review-coach.md(엔지니어링 세션이 반영)
  - Verify: 두 문단 존재
- [ ] **CEO-T10 (P3, human: ~1h / CC: ~10min)** — docs — agent.md 1.2 API 표 갱신(`/api/moves`·`review_id`·`text`·초대 토큰) + 설계 본문에 CEO 범위 반영 + `/plan-design-review` 재실행(C0·C-O1로 DR4·DR8 변경)
  - Surfaced by: Section 10·11
  - Files: agent.md, docs/designs/loss-review-coach.md
  - Verify: 표·본문 갱신, 디자인 리뷰 로그 새 행
- [ ] **CEO-T11 (P1, human: ~1h / CC: ~10min)** — ops — 노트북 이전 + 새 OpenAI 키 + 임베딩 호환 확인
  - Surfaced by: Step 0 — D1 추가 사실(GMS 키 2026-10-23 만료), D3 지시
  - Files: .env(전송 금지), docs/HANDOFF-machine-migration.md
  - Verify: 인계장 "노트북에서 확인할 것" 1~4

JSONL artifact: skipped — jq not installed (install jq for /autoplan aggregation).

## Reality rows

REALITY: premise-table finding unverified=1 (P5 이탈 원인=정보 격차, The Assignment 미확보), 사용자 진술만: P6 싱글·현재 시즌 M-7 docs/designs/loss-review-coach.md:47
REALITY: already-done pass 커밋 0개, CEO 과제 중 구현된 것 없음, 엔지니어링 T6(도구 전체 분포)만 완료 docs/designs/loss-review-coach.md:1199
REALITY: surface-check finding `POST /api/feature/review`·`/api/moves`·`review_id`·초대 토큰은 아직 없는 계약(server/ 없음). `claude rc`는 `claude remote-control` 별칭으로 `--help` 확인 docs/designs/loss-review-coach.md:133
REALITY: binding-decisions pass agent.md 1.3 데이터 우선순위 유지(C-O5), U7 유지(S3), 자연어 우선은 사용자 직접 지시(C0) agent.md:96
REALITY: numbers finding 위력 차이 13개·타입 0개 [measured: data/processed/crosscheck_report.md:17], 변경 파일 약 18개 [estimated], 미지원 도구 약 72% [re-measure before gate: D24 전체 분포 이후] data/processed/crosscheck_report.md:17
REALITY: deferred-asks pass 연결된 이슈 없음 docs/designs/loss-review-coach.md:1
REALITY: pr-count pass `.gstack/ship-policy.json` 없음 → 기본 1 PR docs/designs/loss-review-coach.md:1

## Completion Summary

```
  +====================================================================+
  |            MEGA PLAN REVIEW — COMPLETION SUMMARY                   |
  +====================================================================+
  | Mode selected        | SCOPE REDUCTION                             |
  | System Audit         | 커밋 0, 서버·화면 없음, 시장 공백(패배 뒤 복기·한국어) |
  | Step 0               | 마감 없음·싱글·자연어 우선, 미룸 6·유지 4    |
  | Section 1  (Arch)    | 1 issue found (자연어 추출 → C1-1)           |
  | Section 2  (Errors)  | 7 error paths mapped, 0 GAPS                |
  | Section 3  (Security)| 1 issue found, 0 High severity (터널 Med)    |
  | Section 4  (Data/UX) | 7 edge cases mapped, 0 unhandled            |
  | Section 5  (Quality) | 0 issues found                              |
  | Section 6  (Tests)   | Diagram produced, 0 gaps                    |
  | Section 7  (Perf)    | 0 issues found (R3-10 열린 채 기록)          |
  | Section 8  (Observ)  | 1 gaps found (→ C8-1)                       |
  | Section 9  (Deploy)  | 1 risks flagged (data/logs 개인정보)         |
  | Section 10 (Future)  | Reversibility: 4/5, debt items: 8           |
  | Section 11 (Design)  | 3 issues (새 상태 3개, 디자인 재리뷰 권장)    |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (6 items)                           |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Error/rescue registry| 7 rows, 0 CRITICAL GAPS                     |
  | Failure modes        | 8 total, 0 CRITICAL GAPS                    |
  | TODOS.md updates     | 6 items (S1·S2·S3·S4·S6·S7), S2 수정 1       |
  | Scope proposals      | 0 proposed, 0 accepted (REDUCTION)          |
  | CEO plan             | skipped by mode                             |
  | Outside voice        | codex completed, 6 findings, 6 resolved     |
  | Lake Score           | 1/1 recommendations chose complete option   |
  | Diagrams produced    | 4 (architecture, data flow, UI states, failure modes) |
  | Stale diagrams found | 1 (디자인 리뷰 화면 그림)                    |
  | Unresolved decisions | 0                                           |
  | Reality rows         | 7/7 rows (PLAN_REALITY), 1 unverified       |
  +====================================================================+
```

### Unresolved Decisions
없음.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | CLEAR | mode: SCOPE_REDUCTION, 0 critical gaps (미룸 6·유지 4, 결정 22개) |
| Outside Review | codex via `/plan-ceo-review` outside voice | Independent 2nd opinion | 1 | completed | 6 findings; 6 resolved; 0 unresolved |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 3 | ISSUES OPEN | 24 issues, 0 critical gaps (최신 행 unresolved 0) |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | ISSUES OPEN | score: 1/10 → 7/10, 16 decisions (C0·C-O1로 DR4·DR8 일부 낡음) |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **OUTSIDE COVERAGE:** codex(gpt-6-astra, probe 보고), CEO plan-review, completed, 6 findings(High 5·Medium 1). 모두 결정(D17~D22). 디자인 리뷰의 codex 시도는 unverified(별도 기록).
- **CROSS-MODEL:** 이 리뷰(Claude, 모델 식별 미기록)와 Codex 모두 "검증보다 범위가 앞섬"에 동의했다. Codex가 추가로 찾은 것은 네 가지다: 확률 보정 부재, 감지 입력 소실, 계산 검산과 진단 평가의 혼동, 출처 간 위력 차이. 이견은 S5 규칙 문서 유지다(D8 B로 유지).
- **VERDICT:** CEO CLEARED — eng review required (CEO 결정 C1-1·C3-1·C8-1·C-O1~O6이 API 계약·평가 방식을 바꿈. 엔지니어링 재리뷰 필요).

NO UNRESOLVED DECISIONS
