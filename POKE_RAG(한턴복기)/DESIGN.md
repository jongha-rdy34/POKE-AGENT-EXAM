---
# gstack: design-md-format=spec
name: 포켓몬 챔피언스 한 턴 복기
description: 패배 직후의 짜증 위에 장식을 얹지 않고, 답 하나와 할 일 하나를 또렷하게 보여 주는 조용한 작업 화면
colors:
  primary: "#15191b"
  on-primary: "#ffffff"
  accent: "#0d6453"
  surface: "#f6f7f7"
  text: "#15191b"
  text-muted: "#525a61"
  line: "#d9dee1"
  chip: "#e9eced"
  roll: "#3b4349"
  warning: "#875200"
  error: "#b0261b"
  dark-primary: "#e5e8ea"
  dark-on-primary: "#101315"
  dark-accent: "#46c2a6"
  dark-surface: "#101315"
  dark-text: "#e5e8ea"
  dark-text-muted: "#a1a9af"
  dark-line: "#2b3135"
  dark-chip: "#1d2225"
  dark-roll: "#c3cacf"
  dark-warning: "#efb45c"
  dark-error: "#ff8b7d"
typography:
  conclusion:
    fontFamily: Pretendard Variable
    fontWeight: 700
    fontSize: 26px
    lineHeight: 34px
    letterSpacing: -0.01em
  conclusion-mobile:
    fontFamily: Pretendard Variable
    fontWeight: 700
    fontSize: 22px
    lineHeight: 30px
  title:
    fontFamily: Pretendard Variable
    fontWeight: 700
    fontSize: 22px
    lineHeight: 30px
  body:
    fontFamily: Pretendard Variable
    fontWeight: 400
    fontSize: 16px
    lineHeight: 26px
  label:
    fontFamily: Pretendard Variable
    fontWeight: 500
    fontSize: 14px
    lineHeight: 22px
    fontFeature: tnum
rounded:
  sm: 4px
  md: 6px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 12px
  base: 16px
  lg: 24px
  xl: 32px
  2xl: 48px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
  input:
    borderColor: "{colors.text-muted}"
    rounded: "{rounded.sm}"
  chip:
    backgroundColor: "{colors.chip}"
    rounded: "{rounded.full}"
  roll-strip-lead:
    backgroundColor: "{colors.accent}"
  roll-strip:
    backgroundColor: "{colors.roll}"
---

# 포켓몬 챔피언스 한 턴 복기

## Overview

**Creative North Star:** "아, 그래서 졌구나" — 납득의 차분함. 장식 없는 한 열 화면에서 결론 문장이 제목이 되고, 청록 한 색이 그 답(결론이 가리키는 계산표 줄의 난수 띠)을 가리킨다.
**Product context:** 포켓몬 챔피언스 싱글 랭크에서 연패 중인 한국어 뉴비. 패배 직후 자연어 한 줄로 "왜 졌지"를 묻는다. 그러면 계산과 근거로 그 타격의 원인 후보와 다음 행동을 돌려준다. 경쟁 도구(Pikalytics·Championite 등)는 배틀 전 준비용이고 영어다.
**Mode per surface:** 복기 탭·결과·채팅 = Operate(작업 화면). 첫 화면 배틀 영상(HANDOFF-design-implementation 지시 2, 미룸) = Experience. 영상을 붙일 때 이 문서에 따로 정한다.
**Reference sites:** 없음(조사 생략, 2026-10-23 사용자 선택).
**Key characteristics:**
- 첫 3초에 결론 문장 하나가 읽힌다.
- 카드·그림자·아이콘·그라데이션이 없다. 위계는 크기·굵기·여백·구분선으로 만든다.
- 강조색은 청록 하나뿐이고, 데이터(결론이 가리키는 계산표 줄의 난수 띠)와 포커스, 제품 표식에만 쓴다. 주 버튼은 거의 검정이다.
- 난수는 칸 16개짜리 띠로 보여 준다. 계산 사실이지 확률이 아니다.
- 화면 위에는 제품 표식(채워진 칸 3개 + 빈 칸 2개의 작은 난수 띠)과 이름 "한 턴 복기"가 있다. 포켓몬 공식 로고는 쓰지 않는다.

## Colors

**Strategy:** Restrained.
- 중립 회색 위에 청록 한 색을 쓴다. 청록은 화면의 답(결론이 가리키는 계산표 줄의 난수 띠)에 둔다. 그래야 결론 바로 아래에서 답이 색으로 보인다(taste-skill 앱 화면 규칙 "colour goes on data, not chrome", 2026-10-23 검수).
- 주 버튼은 거의 검정(`#15191b`)이고, 어두운 테마에서는 밝은 회색(`#e5e8ea`) 바탕에 검정 글자다. 다음 행동은 색이 아니라 굵기와 2px `text` 윗선으로 강조한다.
- 경고(참고용·저하)와 오류만 별도 색을 쓰고, 둘 다 글자와 함께 표시한다.

**Light or dark:** 시스템 설정(`prefers-color-scheme`)을 따른다. 이용 장면은 랭크배틀 직후의 방이고, 폰이나 PC로 보며 밤에도 자주 본다. 그래서 어느 한쪽을 강제하지 않는다.
- 어두운 테마는 밝기를 뒤집기만 하지 않는다. 청록은 밝게(`#46c2a6`) 바꾸고, 주 버튼은 밝은 회색 바탕에 검정 글자로 뒤집어 대비를 지킨다.
- 대비 계산값(2026-10-23):
  - 밝은 테마: 본문 16.5, 보조 6.5, 강조 6.6, 경고 6.0, 오류 6.2
  - 어두운 테마: 본문 15.2, 보조 7.8, 강조 8.5, 경고 10.1, 오류 8.2
  - 주 버튼(글자 대 바탕): 두 테마 모두 본문 대비와 같음(약 15~16)
- `line`(구분선, 대비 1.3~1.4)은 장식 전용이다. 입력 칸처럼 조작 대상의 경계에는 쓰지 않고, `text-muted`를 쓴다(3:1 이상).
- 선택 영역·포커스 링·커서 색은 `accent`로 칠한다.
- 링크는 강조색을 쓰지 않는다. `text` 색에 밑줄을 긋는다.

## Typography

- **글꼴:** Pretendard Variable 한 가족만 쓴다. SIL OFL 1.1, v1.3.9, [github.com/orioncactus/pretendard](https://github.com/orioncactus/pretendard).
- **불러오기:** `web/fonts/`에 직접 둔다(DR11). 개발 중에는 jsDelivr `pretendardvariable-dynamic-subset.min.css`를 써도 된다.
- **고른 이유:** 한국어 앱 사용자가 가장 익숙하게 읽는 본문 글꼴이라, 작업 화면에서 읽는 부담이 없다. 대신 결론(26px·700)과 본문(16px·400)의 크기·굵기 차이를 크게 벌려 위계를 만든다.
- **크기 단계:** 결론 26/34(폰 22/30) · 화면 제목 22/30 · 본문 16/26 · 보조·라벨 14/22. **이 네 단계만 쓴다.** 14px 아래로는 내리지 않는다.
- **줄바꿈:** 모든 텍스트에 `word-break: keep-all; overflow-wrap: break-word`를 건다. 한국어 단어가 줄 끝에서 잘리지 않게 하려는 것이다(검수 전 폰에서 "테/마", "쓰러졌/어"처럼 잘렸다).
- **h1:** 화면마다 하나. 제품 이름은 화면 위 표식 옆에, 각 화면의 h1은 그 화면의 질문("어떤 한 턴이 납득 안 되나요?")이나 결론이다.
- **숫자:** 모든 숫자(채용률·k/16·데미지 %·날짜)는 `tabular-nums`로 쓴다. 고정폭 글꼴은 쓰지 않는다.
- **강조:** 굵기(700)로만 강조한다. 기울임·그라데이션 글자는 쓰지 않는다.

## Layout

- 모든 폭에서 최대 720px 한 열(DR12). 예외 하나: 결과가 다른 두 기준 묶음은 1200px 이상에서 1104px 좌우 배열(Components "두 기준 묶음"). 폰(<600px)은 좌우 여백 16px이고, 대결 줄은 3줄로 나눈다.
- 영역 사이는 여백 24~48px과 1px `line` 구분선으로 나눈다. 제목 위 여백이 아래 여백보다 크다.
- 결과 순서는 DR3를 따른다: 결론 → 가정 줄 → 원인 순위 → 다음 행동 → 추가 질문 → U7 문구 → 접힘 → "진짜 패인?".
  - 2026-10-23 현재 서버 응답에 다음 행동이 없고 채팅이 없어, 다음 행동·추가 질문은 빠진다. 원인 순위는 두 기준 묶음이 되고, 접힘은 "가정 · 계산하지 않은 것 · 출처"다.
- 원인 비교는 순위 목록(`<ol>`)의 행으로 그린다.
  - PC: 순위 | 도구(위)·성립 조건(아래) | 난수 띠 + "16번 중 k번 한 방"(오른쪽 끝 정렬)
  - 폰(<600px): 1줄 도구, 2줄 난수 띠 + 글자, 3줄 성립 조건
- 확인 단계 칩 사이의 구분 기호(←, ·)는 다음 칩과 한 덩어리(`white-space: nowrap`)로 묶는다. 구분 기호가 줄 끝이나 줄 맨 앞에 혼자 남지 않게 하려는 것이다.

## Elevation & Depth

그림자·흐림·후광을 쓰지 않는다. 깊이는 구분선과 `chip` 배경색으로만 표현한다.

## Shapes

- 입력 칸 4px, 버튼 6px. 확인 단계 칩만 완전히 둥글게.
- 그 밖의 요소는 둥글리지 않는다. 같은 큰 반경을 모든 요소에 쓰지 않는다.

## Components

- **주 버튼:** `primary`(거의 검정) 배경 + `on-primary` 글자, 화면당 하나. PC에서는 글자 폭(최소 160px), 폰에서는 줄 폭을 채운다. 포커스는 `accent` 2px 링(2px 간격). 터치 대상 44px 이상.
  - **비활성:** 투명 배경 + `line` 테두리 + `text-muted` 글자. 흐리게만 두지 않고, 바로 아래에 이유를 한 줄로 쓴다("남은 HP 구간을 골라 주세요"). `aria-describedby`로 연결한다.
- **보조 버튼:** 투명 배경 + `text-muted` 테두리. 링크형 버튼은 `text` 색 밑줄.
- **입력 칸:** `text-muted` 1px 테두리. 레이블은 항상 보이게 둔다(placeholder만으로 대신하지 않는다). 오류는 `error` 글자로 칸 아래에 보이고 `aria-describedby`로 연결한다.
- **칩(확인 단계):** `chip` 배경 + 700 굵기. 빠진 값은 투명 배경 + `error` 점선 테두리 + 안내 글자. 누르면 해당 칸을 편집한다(combobox, DR13).
  - **다시 볼 값(서버 `ask`):** 값은 그대로 두고 `warning` 1px **실선** 테두리 + 칩 안 꼬리 " · 확인"(14px, `warning`). 버튼을 막지 않는다. 누르면 표시가 사라진다. 점선은 빈 칸 전용이다.
  - 서버 안내 문장(`notes`)은 칩 줄 바로 아래 14px `text` 색, 글머리표 없이.
- **두 기준 묶음:** "실제 랭크배틀 기준"(pokedb)과 "Showdown 시뮬레이터 기준"(Smogon). 제목 16/700, 아래 출처 이름표 14px `text-muted`.
  - Smogon 묶음은 "Pokémon Showdown(시뮬레이터) 환경에서 수집된 데이터 · 출처" 줄을 항상 보인다.
  - 결과가 다르면 우선순위 순(pokedb 위·왼쪽, Smogon "(참고)" 아래·오른쪽)으로 둘 다 보인다. 같으면 pokedb + 접힌 "다른 기준(Showdown 시뮬레이터)으로 보기".
  - 반응형: 화면 1200px 이상이면 이 영역만 1104px로 넓혀 좌우 두 열(536px씩, 사이 `line` 세로선). 그 아래는 상하로 쌓고 2px `line` 구분선으로 뗀다. 720px 본문 안에 두 열을 만들지 않는다(열이 좁아 조건이 단어마다 끊긴다).
- **계산표(상대 빌드별):** 결론 아래, 통계 원인표 위. 구역 제목 22/700("계산 결과 · 상대 빌드별", "통계로 보면") + 위 1px `line`.
  - 한 줄 = 빌드 이름(14/500) → **데미지 범위**(16/700, 계산기처럼 가장 먼저 보이게) + 난수 띠(`roll`) + 결과("난수 1타 · 16번 중 k번 (75%)", "확정 1타") → 통계 표기(14px `text-muted`).
  - 계산표의 %는 계산 사실이라 보인다(C-O1 부분 변경). 원인 확률 %는 여전히 내지 않는다.
  - 챔피언스에 없는 도구는 흐리지 않고 아래에 "참고" 배지와 함께 따로 묶는다. 처음 3줄 + "빌드 N개 더 보기" 접힘.
- **도구로 구분 불가 목록:** 순위 숫자와 청록 없이 나열한다. 캡션 "상대 도구로는 구분하기 어려워요. 아래 후보 모두 이 결과와 맞아요".
- **참고용 배지:** `warning` 글자 + 같은 색 1px 테두리, 반경 4px. 이유 한 줄을 함께 둔다.
- **난수 띠:** 8×14px 칸 16개(폰 7px), 간격 2px.
  - 결론(`headline`)이 가리키는 계산표 줄(결과가 나오는 줄 중 챔피언스에 있는 첫 줄)만 `accent` 테두리와 채움이고, 나머지는 모두 `roll`이다. 통계 원인표는 순위와 관계없이 `roll`이다. 결론이 "어려워요"류(가리키는 줄 없음)이거나 띠가 없는 스피드 결과면 청록을 쓰지 않는다.
  - 띠 옆 글자는 "16번 중 k번"으로 짧게 쓰고, "띠는 가장 그럴듯한 조건에서 난수 16번 중 실제 결과와 같게 나온 횟수예요"를 결과 아래 한 번만 쓴다.
  - `role="img"`와 `aria-label="16번 중 k번 한 방"`을 붙이고, 같은 글자 표기를 옆에 항상 둔다.
- **다음 행동:** 위쪽 2px `text` 선 + 14px `text-muted` 라벨 + 700 본문.
- **제품 표식:** 4×18px 칸 5개(앞 3칸 `accent` 채움). 제품 이름 "한 턴 복기" 22/700 옆에 둔다.
- **안내 문구(저하·오류):** 배경 없이 `warning`/`error` 글자 + 아래 구분선. 결과 자리를 오류가 대신하면 그 문구가 화면의 h1(22px)이다. 문구는 서버 `code`로 고르고, 영문 키가 든 서버 `message`는 그대로 내지 않는다(문구표: docs/designs/HANDOFF-design-parallel.md "디자인 결과").

## Do's and Don'ts

- Do: 결론 문장을 제목 크기로 쓰고, 그 위에 따로 제목이나 라벨을 두지 않는다.
- Do: 색으로 전하는 상태(참고용·오류·난수)에는 항상 글자를 함께 둔다.
- Do: 숫자는 tabular-nums. 원인 확률 %는 정답 평가(CEO-T4)로 확인되기 전까지 화면에 내지 않는다(C-O1). 계산표의 난수 %(16번 중 k번의 비율)는 계산 사실이라 낸다.
- Do: 두 테마 모두에서 본문 대비 4.5:1 이상을 확인한 뒤 색을 바꾼다.
- Don't: 카드·그림자·아이콘 타일·이모지·그라데이션·색 왼쪽 테두리.
- Don't: 포켓몬 공식 아트·로고·타입 아이콘을 장식으로 쓰지 않는다(IP 위험, 전제 4). 포켓몬 이름은 글자로만 쓴다.
- Don't: 포켓몬 하면 떠오르는 빨강·노랑을 기본 강조색으로 쓰지 않는다.
- Don't: 청록을 결론이 가리키는 띠·포커스·제품 표식이 아닌 곳(버튼·링크·제목·배경)에 쓰지 않는다.
- Don't: 13·15·18px처럼 네 단계 밖의 글자 크기를 새로 만들지 않는다.

## Motion

- **Approach:** minimal-functional. 상태가 바뀔 때만 움직인다. `prefers-reduced-motion: reduce`이면 모두 끈다.
- **Easing:** enter(ease-out) exit(ease-in) move(ease-in-out)
- **Duration:** micro 100ms · short 120~240ms · 결과 등장 240ms
- **The one authored moment:** 결과가 나올 때 난수 띠가 왼쪽부터 한 칸씩(35ms 간격, 칸마다 120ms) 채워진다. 그 밖의 등장 효과는 결과 영역 한 번(240ms, 4px 위로)뿐이다.

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-10-23 | Initial design system created | /design-consultation, 조사 생략. 기준 "납득의 차분함", DR10·DR11·DR12·DR13·C-O1·DR20~DR22를 이어받음 |
| 2026-10-23 | 모험 1: 결론 문장을 26px 제목으로 | 3초 안에 답이 읽혀야 함 |
| 2026-10-23 | 모험 2: 난수 띠 16칸 | %를 숨긴 대신 계산 사실을 보여 주는 이 제품만의 표시 |
| 2026-10-23 | taste-skill 검수 반영: 강조색을 1순위 난수 띠로, 주 버튼은 거의 검정 | 사용자 선택(검수 A안). DR10·DR11의 "청록 = 다음 행동·주 버튼"을 바꿈. 앱 화면 규칙 "colour on data, not chrome" |
| 2026-10-23 | taste-skill 검수 반영: keep-all, h1·제품 표식, 폰 원인 목록, 구분 기호 묶기, 비활성 이유, 글자 4단계, PC 버튼 글자 폭 | lint·inspect(--app) 0 FAIL·0 WARN (1440·768·390), 어두운 테마는 직접 촬영해 확인 |
| 2026-10-23 | 두 기준 묶음, 다시 볼 값 칩(실선), 구분 불가 목록(순위·청록 없음), 오류 문구 h1, 청록은 주 기준 1순위에만 | 엔지니어링 인계(HANDOFF-design-parallel) P1·P2. 실제 샘플 응답으로 시안 29개 상태 검수, lint·inspect 0 FAIL·0 WARN |
| 2026-10-23 | 두 기준 묶음을 반응형으로: 1200px+ 좌우(1104px로 넓힘), 그 아래 우선순위 순 상하. DR12(720px 한 열)의 예외 | 사용자 지시. web/ 화면에서 720px 안 두 열이 좁아 조건이 단어마다 끊기고 결론이 4줄 문단이 됨 |
| 2026-10-23 | 계산표(상대 빌드별): 데미지 범위 굵게 + 띠 + 계산기 용어(확정·난수 1타), 챔피언스에 없는 도구는 따로 묶음, 3줄 + 접힘. 구역 제목 22px | 엔지니어링 인계 P0(개정 v1.4). 친구 사례에서 챔피언스에 없는 도구 줄이 결과를 설명해 흐리지 않음 |
| 2026-10-23 | 청록을 통계 1순위에서 결론이 가리키는 계산표 줄로 옮김 | 사용자 선택(web/ 검수 W3). 결론이 계산표에서 나오게 바뀌어, 급소 사례에서 결론(생명의구슬 확정 1타)과 청록(통계 1순위 영향 없는 도구 2/16)이 어긋났다 |
