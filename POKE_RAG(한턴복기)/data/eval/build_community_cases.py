"""커뮤니티(Reddit) 혼동 사례 → data/eval/community_cases.jsonl (F2015 평가셋, D20).
라벨은 커뮤니티 답변이라 verified=False. 채점 기준으로 쓰기 전에 Bulbapedia 원문과 대조한다.
  .venv/Scripts/python -m data.eval.build_community_cases  (또는 파일 경로로 직접 실행)
"""
import json
from collections import Counter
from pathlib import Path

R, C, O = "review", "chat", "out_of_scope"  # 복기 계산 / 채팅(RAG) / v1 범위 밖
SRC = "reddit (사용자 수집 2026-10-22, URL 미기록)"

# (id, 질문, 라벨, 경로, 태그, 원문 인용 또는 스레드 제목, 중복 id)
ROWS = [
    ("A1", "메가 갑주무사 흡혈이 계산상 확정 1타인데 왜 키키링을 못 잡음?", "앞 턴 찌르호크의 위협으로 공격 -1", R, ["intimidate", "stat_stage"], "", ["N13"]),
    ("A2", "더시마사리 HP 142인데 도각참 70+70 맞고 72 남았는데 왜 다음 타에 죽음?", "16단계 난수(저난수 뒤 고난수)", R, ["random_roll"], "", []),
    ("A3", "님피아 하이퍼보이스 첫 타 86인데 둘째 타에 왜 죽음? 급소 아님", "난수 범위 87~103, 저난수 후 고난수로 2타", R, ["random_roll"], "", []),
    ("A4", "껍질깨기+도우미 거북왕 해수스파우팅이 왜 2~3밖에 안 닳음?", "현재 HP 비례 위력, 1HP면 위력 바닥", R, ["variable_power"], "", []),
    ("A5", "급소 터졌는데 비 속 불꽃기술이 왜 반토막?", "급소는 날씨 보정을 무시하지 않음", R, ["crit", "weather"], "", []),
    ("A6", "슬러지웨이브 95가 오물폭탄 90보다 왜 못 죽이는 것처럼 계산됨?", "난수·실제 내구·기술 조건 포함 KO 확률, 33.3% OHKO는 일부 난수만 1타", R, ["random_roll"], "", []),
    ("A7", "계산기에선 확정 1타인데 실전에선 왜 안 죽음?", "위협·랭크·도구·특성·필드·날씨·대상 수·테라/메가 입력 누락", R, ["intimidate", "item", "ability"], "", []),
    ("A8", "더블에서 하이퍼보이스가 싱글 계산보다 왜 약함?", "복수 대상 기술 0.75 보정", O, ["spread_move", "doubles"], "", []),
    ("A9", "급소면 상대 철벽 +6도 무시하는데 왜 내 공격 감소는 반영 안 되는 경우가 있음?", "급소는 공격자 불리 랭크·방어자 유리 랭크 무시, 날씨는 그대로", R, ["crit", "stat_stage"], "", ["N5"]),
    ("A10", "같은 포켓몬 같은 기술인데 왜 매번 데미지가 다름? 급소 아님", "0.85~1.00 16단계 난수", R, ["random_roll"], "", []),
    ("B1", "트릭룸인데 왜 느린 코터스 가뭄이 먼저 발동하고 왕구리 잔비가 나중?", "트릭룸이면 행동 순서 반전, 동시 등장 특성도 그 순서", C, ["trick_room", "weather_ability_order"], "", []),
    ("B2", "패리퍼 교체했는데 왜 잔비가 안 깔리고 그냥 죽음?", "설치기 데미지가 등장 특성보다 먼저 처리", C, ["entry_hazard", "ability_timing"], "", []),
    ("B3", "상대가 공격기 눌렀는데 왜 내 기습이 실패함?", "상대가 이미 행동을 끝냈으면 기습 실패", C, ["sucker_punch", "priority"], "", []),
    ("B4", "상대 아쿠아제트인데 왜 내 기습이 먼저 맞음? 둘 다 선공기", "같은 우선도 안에서는 스피드 순", C, ["priority", "speed"], "", ["N4"]),
    ("B5", "내가 더 빠른데 왜 상대가 먼저 때림?", "상대 구애스카프", R, ["choice_scarf", "speed"], "", []),
    ("B6", "짓궂은마음 변화기가 왜 상대 악타입에 실패함?", "악타입은 짓궂은마음으로 우선도가 오른 변화기에 면역", C, ["prankster", "dark_immunity"], "", []),
    ("B7", "버섯포자가 왜 상대 풀타입에 안 통함?", "풀타입은 가루 계열 기술 면역", C, ["powder_immunity"], "", []),
    ("B8", "격투기가 왜 '효과가 없는 것 같다'임?", "히스이 조로아크 일루전(실제 타입 노말/고스트)", C, ["illusion"], "", []),
    ("B9", "위협 넣었는데 왜 상대 공격이 안 떨어짐? 클리어바디 아님", "정신력은 위협의 공격 하락도 막음", C, ["intimidate", "inner_focus"], "", []),
    ("B10", "와이드가드를 여러 번 연속 썼는데 왜 계속 성공함?", "와이드가드는 연속 사용으로 성공률이 감소하지 않음", C, ["wide_guard", "doubles"], "", ["N2"]),
    ("N1", "첫 턴 지나니까 왜 속이기 자체를 못 누름?", "Champions에서는 첫 등장 턴이 아니면 속이기를 선택할 수 없도록 변경", C, ["fake_out", "champions_change"], "Why do they not allow you to use Fake out when it’s not the first turn?", []),
    ("N2", "와이드가드 연속으로 썼는데 왜 또 성공함?", "와이드가드는 연속 사용으로 성공률이 감소하지 않음", C, ["wide_guard", "doubles"], "Wait, Wide Guard doesnt fail when used consecutively??", ["B10"]),
    ("N3", "몰드류한테 검은철구를 왜 줌? 스피드 떨어지면 손해 아닌가?", "트릭룸 안에서 더 빨리 행동하려고 스피드를 낮춤", C, ["trick_room", "iron_ball"], "Wait why Iron Ball on Excadrill? Just for Hard tr?", []),
    ("N4", "상대 기습 눌렀는데 왜 내 아쿠아제트가 먼저 나감?", "아쿠아제트·기습 모두 +1, 같은 우선도에서는 스피드 순, 이후 기습 실패", C, ["priority", "speed", "sucker_punch"], "I realised I had Aqua Jet and I was faster.", ["B4"]),
    ("N5", "리플렉터에 철벽까지 쌓았는데 왜 급소 한 방이 이렇게 셈?", "급소는 벽·공격자 불리 랭크·방어자 유리 방어 랭크를 무시하고 1.5배", R, ["crit", "screens", "stat_stage"], "Critical Hits… Ignoring Screens, stats drops, defense boosts + doing a 1.5x damage boost", ["A9"]),
    ("N6", "쾌청인데 왜 리자몽 솔라빔이 한 턴 충전함?", "날씨부정(Cloud Nine)이 있으면 날씨 효과 무효", C, ["cloud_nine", "weather"], "Cloud Nine… negates the effects of weather.", []),
    ("N7", "초점렌즈 + 급소보정 기술 + 기충전 쓰면 급소랭크가 더해짐?", "급소 단계는 합산됨", C, ["crit_stage"], "are these additive?", []),
    ("N8", "리자몽Y랑 메가마기라스가 동시에 메가진화했는데 왜 모래바람이 남음?", "빠른 쪽 특성이 먼저 발동하고 느린 쪽 날씨가 나중에 덮어씀", C, ["weather_ability_order", "speed"], "How does the game determine which weather stays… Is it Sandstorm since Charizard is faster?", []),
    ("N9", "비 오는데 브리두라스 일렉트릭샷이 왜 바로 안 나가고 충전함?", "상대 Drampa의 날씨부정으로 비 효과 무효", C, ["cloud_nine", "weather"], "I used Electro shot in the rain… it just started charging.", []),
    ("N10", "화상딜 6%씩 들어오다 마지막엔 왜 5%만 닳고 1HP 생존함?", "실제 HP는 정수, 표시 %는 반올림이라 일치하지 않을 수 있음", C, ["hp_rounding", "burn"], "Does burn not drop a Pokemon's HP below 1…?", []),
    ("N11", "화상은 공격 -2랑 똑같은 거 아님? 왜 계산 결과가 다름?", "화상은 랭크가 아니라 물리 데미지 별도 보정, 더블 리플렉터도 별도 배율", R, ["burn", "screens"], "I was under the impression since burn cuts attack in half, I could either do -2… or reflect.", []),
    ("N12", "대쓰여너 Last Respects가 왜 계산기에서 이렇게 약하게 나옴?", "쓰러진 아군 수에 따라 위력 증가, 계산기에 KO 수 입력 필요", R, ["variable_power"], "Last Respects… barely any damage… Any ideas?", []),
    ("N13", "메가 갑주무사 흡혈이 확정 1타인데 왜 키키링 피가 35%나 남음?", "앞서 찌르호크의 위협으로 공격 -1", R, ["intimidate", "stat_stage"], "Leech Life… only did about 65%… this should have OHKO'ed.", ["A1"]),
    ("N14", "사이코필드인데 왜 비행 포켓몬한테 속이기가 들어감?", "사이코필드는 목표가 접지 상태일 때만 우선기 차단", C, ["psychic_terrain", "grounded"], "Psychic Terrain protects grounded Pokemon from priority…", []),
    ("N15", "비 오는데 메가 메가니움 웨더볼이 왜 쏘콘 약점을 찌름?", "Mega Sol로 자신의 기술은 쾌청처럼 계산되어 웨더볼이 불꽃 타입", R, ["weather_ball", "mega_sol", "champions_change"], "Mega Meganium use weather ball… while it was raining and it was super effective?", []),
    ("N16", "비에서 패리퍼 웨더볼 결정력은 200임 225임?", "100 × 비 1.5 × 자속 1.5 = 225 상당, 보정은 곱연산", R, ["weather_ball", "weather", "stab"], "Pelipper weather ball on rain is 200 Base Power or 225?", []),
    ("N17", "리자몽Y는 왜 화염방사 대신 웨더볼을 씀?", "쾌청에서 웨더볼은 불꽃 100위력, 날씨가 바뀌어도 타입 변화로 활용", C, ["weather_ball"], "Why does Charizard Y run weather ball over flamethrower?", []),
    ("N18", "부유 로토무인데 왜 사이코시드가 터짐?", "필드 시드는 비접지여도 해당 필드가 있으면 발동", C, ["terrain_seed", "grounded"], "Does the Pokémon holding seed item need to be grounded for it to activate?", []),
    ("N19", "트릭룸 켜졌는데 내가 트릭룸 또 쓰니까 왜 정상 스피드로 돌아옴?", "트릭룸 중 다시 쓰면 종료", C, ["trick_room"], "What is the counter to Trick Room? → Set up your own trick room. It reverts it.", []),
    ("N20", "사이코필드에서 내 깜까미가 접지인데 비행 리자몽한테 짓맘 사슬묶기 왜 들어감?", "우선도 차단은 사용자가 아니라 목표의 접지 여부로 판정", C, ["psychic_terrain", "grounded", "prankster"], "the not-grounded pokemon… is it the target, or the user of the move?", []),
    ("N21", "비 웨더볼은 이미 100위력인데 비 1.5배도 또 받음?", "비가 웨더볼을 물타입 100위력으로 바꾸고 다시 비 1.5배 적용", R, ["weather_ball", "weather"], "Does the rain boost add to the 100 BP it already has under rain?", []),
    ("T1", "트릭룸인데 왜 내 엘풍 트릭룸보다 상대 눈보라가 먼저 나감?", "트릭룸 자체가 우선도 -7, 짓궂은마음이어도 -6", C, ["trick_room", "priority"], "Why didn't Prankster trigger?", []),
    ("T2", "엘풍이 짓궂은마음인데 왜 트릭룸 선공 못함?", "-7 + 1 = -6, 여전히 일반 공격보다 느림", C, ["trick_room", "prankster", "priority"], "Why didn't Prankster trigger?", []),
    ("T3", "사이코필드인데 왜 상대가 날 속이기로 때림?", "사이코필드는 접지 상태인 대상만 보호", C, ["psychic_terrain", "grounded"], "Can someone explain why did Fake Out go off when psychic terrain was active?", ["N14"]),
    ("T4", "사이코필드인데 왜 내 아쿠아제트가 상대 비행타입한테 맞음?", "상대가 비접지면 선공기 차단 효과 없음", C, ["psychic_terrain", "grounded"], "Can someone explain why did Fake Out go off when psychic terrain was active?", ["N14"]),
    ("T5", "키키링 있는데 왜 내 도우미는 정상적으로 나감?", "테일아머는 상대 진영을 노리는 우선도 기술만 차단", C, ["armor_tail", "priority"], "PSA to all new players: If you see these 2, do NOT click Fake Out", []),
    ("T6", "달코퀸 있는데 왜 기습이 실패함?", "여왕의위엄이 상대 우선도 기술 차단", C, ["queenly_majesty", "priority"], "PSA to all new players: If you see these 2, do NOT click Fake Out", []),
    ("T7", "캥카가 속이기/비장의무기인데 왜 갑자기 발버둥만 나감?", "비장의무기는 다른 기술을 실제로 써야 사용 가능, 첫 턴 속이기 전에 풀죽으면 조건 미충족 가능", C, ["last_resort"], "Am I missing something here?", []),
    ("T8", "키키링한테 속이기가 막혔는데 그 뒤 비장의무기는 왜 쓸 수 있음?", "테일아머 등에 막혀도 사용 시도가 비장의무기 조건에 포함될 수 있음", C, ["last_resort", "armor_tail"], "They never learn...", []),
    ("T9", "내 한카리아스 지진이 로토무한테 왜 0딜임?", "부유 특성으로 땅 기술 무효", R, ["levitate", "ability"], "They never learn...", []),
    ("T10", "위협 맞았는데 내 밀로틱 특공이 오히려 올라가서 더 세졌는데 왜?", "승기: 상대에 의해 능력이 떨어지면 특공 크게 상승", C, ["competitive", "intimidate"], "My experience with this game", []),
]


def main():
    here = Path(__file__).parent
    out = here / "community_cases.jsonl"
    vf = here / "community_cases_verification.json"  # 원문 대조 결과(T10). 없으면 전부 미대조
    ver = json.loads(vf.read_text(encoding="utf-8")) if vf.exists() else {}
    with out.open("w", encoding="utf-8") as f:
        for i, q, label, route, tags, quote, dup in ROWS:
            v = ver.get(i, {})
            f.write(json.dumps({"id": i, "question_ko": q, "label": label, "route": route, "tags": tags, "source": SRC,
                                "source_quote": quote, "duplicate_of": dup, "verified": v.get("status") == "verified",
                                "verify_status": v.get("status", "unchecked"), "evidence": v.get("evidence", ""), "verify_note": v.get("note", "")},
                               ensure_ascii=False) + "\n")
    assert len({r[0] for r in ROWS}) == len(ROWS), "id 중복"
    assert not set(ver) - {r[0] for r in ROWS} - {"_about"}, "대조 파일에 없는 id"
    print(f"{len(ROWS)}건 → {out.name}", dict(Counter(r[3] for r in ROWS)), dict(Counter(ver.get(r[0], {}).get("status", "unchecked") for r in ROWS)))


if __name__ == "__main__":
    main()
