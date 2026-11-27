| app | case | call | http | sec | 결과 |
|---|---|---|---|---|---|
| A | S2 | extract | 200 | 5.8 | type=review missing=[] reason=None |
| A | S3 | extract | 200 | 4.6 | type=review missing=[] reason=None |
| A | S4_unknown_name | extract | 200 | 2.2 | type=review missing=['my_form_key', 'move_key'] reason=None |
| A | S4_rule_mismatch | extract | 200 | 6.4 | type=review missing=['actual'] reason=None |
| A | S4_empty | extract | 422 | 0.0 | 빈 입력(화면은 버튼 비활성으로 막을 수 있음) |
| A | S2 | review | 200 | 0.3 | last_event=answer 상대가 흔한 빌드라면 계산상 이 결과가 나오기 어려워요 |
| A | S3 | review | 200 | 0.1 | last_event=answer 상대가 노력 생명의구슬이면 16번 중 6번 이 HP로 버텨요 |
| A | S4_rule_mismatch | review | - | 0 | 추출에 필수 칸이 없어 계산하지 않음: ['actor', 'move_key', 'my_form_key', 'opp_form_key'] |
| A | S5 | review | 200 | 0.2 | last_event=answer 지금 챔피언스에 있는 도구로는 이 결과가 나오기 어려워요 |
| B | S2 | chat | 200 | 1.9 | status=error intent=error error=UPSTREAM_ERROR answer='요청을 처리하지 못했습니다: LLM 서버가 정상 응답하지 않았습니다.' |
| B | S3 | chat | 200 | 11.2 | status=ok intent=matchup_advice error=None answer='### 상대 파티 공격 성향\n- **파티 공격 성향**: 물리 중심 (물리 99.9%, 특수 0.1%)\n- ' |
| B | S5 | chat | 200 | 4.6 | status=ask intent=plan_selection error=None answer='확인이 필요해요.\n- 내 포켓몬을 알려주세요 (선출 수 이상, 보통 6마리). 예) 내 팀: 한카리아스, 마' |
| B | S4_unknown_name | chat | 200 | 2.8 | status=ask intent=plan_selection error=None answer="확인이 필요해요.\n- '피카츄몽'을(를) 정확히 찾지 못했어요. 혹시 피카츄, 리자몽, 미라몽, 피츄, 호연" |
| B | S4_empty | chat | 200 | 0.9 | status=error intent=error error=UPSTREAM_ERROR answer='요청을 처리하지 못했습니다: LLM 서버가 정상 응답하지 않았습니다.' |
| B | S4_rule_mismatch | chat | 200 | 0.7 | status=error intent=error error=UPSTREAM_ERROR answer='요청을 처리하지 못했습니다: LLM 서버가 정상 응답하지 않았습니다.' |
