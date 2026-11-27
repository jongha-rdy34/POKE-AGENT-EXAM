---
name: data-source-priority
description: "포켓몬 프로젝트 데이터 우선순위 PokeAPI > pokedb(부분집합), 챔피언스는 분기 게임이라 기준 아님, champions-data는 구버전 보충 전용"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4355691c-3097-4b2c-a44a-ab030cc27187
  modified: 2026-10-22T10:46:50.460Z
---

데이터 우선순위는 **PokeAPI > pokedb**다. pokedb는 PokeAPI의 부분집합(챔피언스 사용 통계만 담당)으로 본다. champions-data(otterlyclueless, 2026-04-16)는 구버전이라 PokeAPI에 값이 없는 공백만 보충하고 출처를 `cd`로 표시한다.

**포켓몬 챔피언스는 분기된 게임이므로 기준으로 삼지 않는다.** 구애머리띠·구애안경처럼 챔피언스에서 확인되지 않은 도구·기술·포켓몬도 PokeAPI에 있으면 계산·답변에서 취급한다. `in_champions`는 필터·안내용 표지일 뿐 제한 조건이 아니다.

**사용 통계 (2026-10-22 사용자 결정):** 도구·채용률·동반은 pokedb(실제 게임 상위 구축, 현재 M-6 — M-7 오픈데이터 미공개) 우선, 성격·SP 배분·특성 분포는 Smogon 월간 통계 `gen9championsbssregmc`(Showdown 래더, 레귤레이션 M-C, 1500+)로 보충, 출처·시점 표기. championsbattledata는 채택 안 함(개인·교육 한정). 같은 레귤레이션 안에서는 메타가 고착화되므로 한 달 지연은 감수한다는 게 사용자 판단.

**Why:** 사용자가 직접 지시함(2026-10-21~22). 내가 PP·위력·습득기를 champions-data 기준으로 쓰려던 것, 도구 보정을 챔피언스 확인 도구로만 제한한 것을 각각 철회시켰다.

**How to apply:** 구조화 저장소·색인·계산기 모두 PokeAPI 값을 채택하고 차이는 crosscheck 보고서에만 남긴다. 이 원칙은 agent.md 1.3절에 적혀 있다. 관련: [[ai-core-project-2]]
