# 쌍비교

아래에 서비스 두 개의 패킷이 {{FIRST}} → {{SECOND}} 순서로 있습니다. 순서는 무작위이며 의미가 없습니다.

질문: **포켓몬 대전 초보자가 계속 쓰고 싶은 서비스는 어느 쪽인가?**

두 서비스는 목적이 다를 수 있습니다. 항목마다 "각자 밝힌 목적 안에서" 어느 쪽이 더 잘했는지 고르고, 차이가 작거나 판단 근거가 없으면 tie를 고릅니다.

항목:
- accuracy: 기능 정확성
- purpose_fit: 스스로 밝힌 목적을 얼마나 달성했나 (기능 개수가 아님)
- usability: 처음 온 사용자가 막힘 없이 쓸 수 있나
- ui: 화면 시각 품질(데스크톱·모바일)
- code: 코드 발췌의 가독성·구조·오류 처리
- overall: 초보자가 계속 쓰고 싶은 쪽 (종합)

## 출력 형식 (이 JSON 하나만)
{"judge_model":"{{JUDGE_MODEL}}","mode":"pairwise","order":"{{ORDER}}","run":{{RUN}},
 "scores":null,
 "pairwise":{"accuracy":"X|Y|tie","purpose_fit":"X|Y|tie","usability":"X|Y|tie","ui":"X|Y|tie","code":"X|Y|tie","overall":"X|Y|tie"},
 "rationale":["근거 1","근거 2","근거 3"]}

- 각 값은 "X", "Y", "tie" 중 하나만 씁니다.
- rationale은 정확히 3개이고, overall 선택의 근거를 패킷의 구체적 장면·수치로 한 문장씩 씁니다.

## 패킷 {{FIRST}}
{{PACKET_FIRST}}

## 패킷 {{SECOND}}
{{PACKET_SECOND}}
