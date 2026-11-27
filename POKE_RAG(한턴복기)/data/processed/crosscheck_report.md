# champions-data ↔ PokeAPI 교차검증 보고

- champions-data: v1.1.0 (2026-04-16, Serebii·Showdown 기반). PokeAPI: 2026-10-21 수집

## 1. 포켓몬 종족값
- 짝지어진 폼 256개 (도감번호+종족값 일치)
- 종족값 차이 0건, 짝 없음 0건, 모호 2건

- 모호: `Paldean Tauros` 후보 ['tauros-paldea-aqua-breed', 'tauros-paldea-blaze-breed', 'tauros-paldea-combat-breed']
- 모호: `Mega Meowstic` 후보 ['meowstic-female-mega', 'meowstic-male-mega']

## 2. 기술
- champions-data 챔피언스 기술 494개, PokeAPI 챔피언스 습득 기술 496개
- champions-data에만 있음 5개: ['Milk Drink', 'Power Shift', 'Soft-Boiled', 'Spore', 'Struggle']
- PokeAPI에만 있음 7개: ['Barb Barrage', 'Make It Rain', 'No Retreat', 'Pound', 'Rage Fist', 'Spirit Break', 'Topsy-Turvy']
- champions-data 기술 중 PokeAPI 기술 데이터에 이름이 없음: ['Milk Drink', 'Power Shift', 'Soft-Boiled', 'Spore', 'Struggle']
- 위력·명중·PP·우선도·타입 차이 395개 기술, 필드별 {'power': 13, 'accuracy': 3, 'pp': 395, 'priority': 0, 'type': 0}

- **데이터 우선순위(사용자 지정): PokeAPI·pokedb가 항상 우선, champions-data는 구버전(2026-04)이라 PokeAPI에 값이 없을 때만 보충한다.** 아래 차이는 모두 PokeAPI 값을 채택한다.
- PP는 거의 전부 다르다(예: PokeAPI 10 / champions-data 12, 15/16, 5/8). PokeAPI 값을 쓰되, 위키 `/Champions 기술`에서 챔피언스 PP가 본가와 다른 사례가 확인된 바 있어 PokeAPI PP가 본가 값일 위험이 있다(agent.md 10절 미결 사항).
- 위력·명중이 다른 기술(champions-data 쪽이 구버전이므로 PokeAPI 값 채택, 참고용 목록):
  - `Apple Acid` {'power': [90, 80], 'pp': [12, 10]}
  - `Beak Blast` {'power': [120, 100], 'pp': [8, 15]}
  - `Bone Rush` {'power': [30, 25], 'pp': [12, 10]}
  - `Clangorous Soul` {'accuracy': [None, 100], 'pp': [8, 5]}
  - `Comeuppance` {'power': [None, 1], 'pp': [12, 10]}
  - `Crabhammer` {'accuracy': [95, 90], 'pp': [12, 10]}
  - `Fire Lash` {'power': [90, 80], 'pp': [16, 15]}
  - `First Impression` {'power': [100, 90], 'pp': [12, 10]}
  - `Grav Apple` {'power': [90, 80], 'pp': [12, 10]}
  - `Infernal Parade` {'power': [65, 60], 'pp': [16, 15]}
  - `Mountain Gale` {'power': [120, 100], 'pp': [12, 10]}
  - `Night Daze` {'power': [90, 85], 'pp': [12, 10]}
  - `Psyshield Bash` {'power': [90, 70], 'pp': [12, 10]}
  - `Spirit Shackle` {'power': [90, 80], 'pp': [12, 10]}
  - `Syrup Bomb` {'accuracy': [90, 85], 'pp': [12, 10]}
  - `Trop Kick` {'power': [85, 70], 'pp': [16, 15]}

## 3. 습득기
- PokeAPI 습득기가 비어 champions-data로 보충 가능한 폼 1개
  - `floette` (cd `Floette` 40기)
- 두 출처 습득기가 다른 폼 96개: {'cd_gap_only': 65, 'cd_superset': 19, 'api_superset': 2, 'both_differ': 10}
  - `cd_gap_only`: champions-data에 Psychic/Grassy Terrain이 빠진 것뿐
  - `cd_superset`: champions-data에만 있는 기술이 있음(구버전이라 채택하지 않음)
- 결론: 습득기는 **PokeAPI만** 쓴다. PokeAPI 습득기가 비어 있는 폼에 한해서만 champions-data로 보충하고 출처를 `cd`로 표시한다.

  - `raichu-alola` cd만 ['brutalswing', 'drainpunch'] / api만 ['psychic']
  - `slowbro-galar` cd만 ['focuspunch', 'psychicnoise', 'scald'] / api만 ['psychic']
  - `slowbro-mega` cd만 ['acidspray', 'doubleedge', 'gunkshot', 'haze', 'icefang', 'poisonjab', 'powergem', 'rockblast', 'sandstorm', 'scaryface', 'shellsidearm', 'sludgebomb', 'sludgewave', 'smackdown', 'toxic', 'toxicspikes', 'venoshock'] / api만 ['psychic']
  - `slowbro` cd만 ['acidspray', 'doubleedge', 'gunkshot', 'haze', 'icefang', 'poisonjab', 'powergem', 'rockblast', 'sandstorm', 'scaryface', 'shellsidearm', 'sludgebomb', 'sludgewave', 'smackdown', 'toxic', 'toxicspikes', 'venoshock'] / api만 ['psychic']
  - `ariados` cd만 ['psychicfangs'] / api만 ['psychic']
  - `slowking-galar` cd만 ['focuspunch', 'reflect', 'rockslide', 'rocktomb', 'scald'] / api만 ['psychic']
  - `slowking` cd만 ['acidspray', 'eeriespell', 'gunkshot', 'hex', 'lowsweep', 'poisonjab', 'scaryface', 'sludgebomb', 'sludgewave', 'snarl', 'stompingtantrum', 'taunt', 'toxic', 'toxicspikes', 'venoshock'] / api만 ['psychic']
  - `zoroark-hisui` cd만 ['counter', 'encore', 'nightdaze', 'nightslash', 'suckerpunch', 'sunnyday', 'toxic'] / api만 ['psychic']
  - `zoroark` cd만 ['bittermalice', 'comeuppance', 'curse', 'focuspunch', 'icywind', 'phantomforce', 'poltergeist', 'shadowsneak', 'snowscape', 'willowisp'] / api만 ['psychic']
  - `meowstic-male` cd만 ['extrasensory', 'futuresight'] / api만 ['psychic']
  - `aegislash-shield` cd만 [] / api만 ['kingsshield']
  - `trevenant` cd만 [] / api만 ['forestscurse', 'psychic']

## 4. 두 출처 모두 습득기가 없는 종
- PokeAPI 챔피언스 도감 종 중 champions-data(2026-04 판)에 없는 종 45개 — 게임 업데이트로 추가된 포켓몬으로 추정
- 그중 PokeAPI 습득기도 빈 종 23개 (pokedb에 실제 등장: 9개): wigglytuff, persian, farfetchd, mr-mime, swalot, salamence*, gogoat, golisopod*, rillaboom*, cinderace*, inteleon, thievul, toxtricity*, grapploct, perrserker, sirfetchd, pincurchin, indeedee*, pawmot*, arboliva*, squawkabilly, mabosstiff, baxcalibur*  (*=pokedb 등장)
- 이 종들의 습득기는 현재 데이터로는 알 수 없다. 후속: Bulbapedia 포켓몬 문서 선수집(2단계)에서 보충하거나, 습득기 없음을 답변에 명시.
