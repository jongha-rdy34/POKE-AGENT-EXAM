""".venv/Scripts/python -m unittest discover -s tests -t .  (프로젝트 루트에서)
기대값은 data/docs/stat_damage_formulas.md 예시와 같다: 한카리아스 H108 A130 B95 C80 D85 S102."""
import unittest
from fractions import Fraction

from prep import calculator as c


class Formulas(unittest.TestCase):
    def test_actual_stat_examples(self):
        self.assertEqual(c.other_stat(130, 32, 100), 182)  # 명랑 공격
        self.assertEqual(c.other_stat(130, 32, 110), 200)  # 고집: floor(182×1.1)=200.2
        self.assertEqual(c.hp_stat(108, 2), 185)
        self.assertEqual(c.other_stat(95, 32), 147)

    def test_nature_floor_and_minus(self):
        self.assertEqual(c.other_stat(100, 0, 110), 132)  # 120×1.1
        self.assertEqual(c.other_stat(100, 0, 90), 108)
        self.assertEqual(c.other_stat(1, 0, 90), 18)  # (1+0+20)×0.9=18.9 → 내림

    def test_decisive_power_examples(self):
        self.assertEqual(c.decisive_power(182, 100, stab=True), 27300)
        self.assertEqual(c.decisive_power(200, 100, stab=True), 30000)
        self.assertEqual(c.decisive_power(200, 100), 20000)  # 자속 없음

    def test_life_orb(self):
        self.assertEqual(c.decisive_power(200, 100, True, [c.FINAL_ITEMS["life-orb"]]), int(30000 * 5324 / 4096))

    def test_bulk(self):
        self.assertEqual(c.bulk(185, 147), 27195)

    def test_sp_validation(self):
        c.check_sp({"atk": 32, "spe": 32, "hp": 2})  # 합계 66 허용
        for bad in ({"atk": 33}, {"atk": -1}, {"atk": 32, "spe": 32, "hp": 3}, {"luck": 1}, {"atk": 1.5}):
            with self.assertRaises(ValueError, msg=bad):
                c.check_sp(bad)


class WithDb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not c.DB_PATH.exists():
            raise unittest.SkipTest("pokedex.sqlite 없음: python -m prep.build_db")
        cls.db = c.connect()

    def test_garchomp_stats(self):
        s = c.actual_stats(self.db, "garchomp", {"atk": 32}, "jolly")
        self.assertEqual(s["atk"], 182)  # 명랑은 공격 보정 없음
        self.assertEqual(c.actual_stats(self.db, "garchomp", {"atk": 32}, "adamant")["atk"], 200)
        self.assertEqual(s["hp"], 183)  # 108+0+75

    def test_earthquake_example(self):
        r = c.attack_decisive_power(self.db, "garchomp", "earthquake", {"atk": 32}, "adamant")
        self.assertEqual((r["value"], r["stab"], r["stat"]), (30000, True, "atk"))
        r = c.attack_decisive_power(self.db, "garchomp", "earthquake", {"atk": 32}, "jolly")
        self.assertEqual(r["value"], 27300)

    def test_unknown_form_raises_value_error(self):
        with self.assertRaises(ValueError):  # TypeError가 아니라 ValueError여야 호출부가 처리할 수 있다
            c.attack_decisive_power(self.db, "nope", "earthquake", {})

    def calc(self, move, item=None, nature="adamant", **kw):
        return c.attack_decisive_power(self.db, "garchomp", move, {"atk": 32, "spa": 32}, nature, item, **kw)

    def test_choice_items_not_in_champions(self):
        # 챔피언스에서 확인되지 않은 도구도 PokeAPI에 있으면 계산한다 (agent.md 1.3절)
        self.assertEqual(self.calc("earthquake", "choice-band")["value"], 45000)  # 200×100×1.5×1.5
        self.assertEqual(c.attack_decisive_power(self.db, "garchomp", "flamethrower", {"spa": 32}, "modest", "choice-specs")["value"],
                         int((80 + 32 + 20) * 110 // 100 * 90 * Fraction(3, 2)))  # 땅/드래곤은 불꽃 자속 없음: 145×90×1.5
        r = self.calc("flamethrower", "choice-band")  # 특수기에 구애머리띠 → 적용 안 됨
        self.assertEqual(r["item_multiplier"], "1")
        self.assertIn("적용되지 않음", r["item_note"])

    def test_other_items(self):
        self.assertEqual(self.calc("earthquake", "muscle-band")["value"], 33000)  # 30000×1.1
        self.assertEqual(self.calc("earthquake", "life-orb")["value"], int(30000 * 5324 / 4096))
        self.assertEqual(self.calc("earthquake", "expert-belt")["item_multiplier"], "1")  # 효과 굉장 아님
        self.assertEqual(self.calc("earthquake", "expert-belt", super_effective=True)["item_multiplier"], "4915/4096")

    def test_type_boost_items_from_pokeapi_text(self):
        self.assertEqual(self.calc("dragon-claw", "dragon-fang")["value"], 28800)  # 200×80×1.5×1.2
        self.assertEqual(self.calc("earthquake", "soft-sand")["value"], 36000)  # 땅 20%: 30000×1.2
        self.assertEqual(self.calc("earthquake", "charcoal")["item_multiplier"], "1")  # 불 도구는 땅 기술에 무효
        self.assertEqual(self.calc("earthquake", "flame-plate")["item_multiplier"], "1")

    def test_species_items(self):
        self.assertEqual(self.calc("earthquake", "light-ball")["item_multiplier"], "1")  # 피카츄 전용
        r = c.attack_decisive_power(self.db, "pikachu", "thunderbolt", {"spa": 32}, "modest", "light-ball")
        self.assertEqual(r["item_multiplier"], "2")

    def test_item_values_match_pokeapi_text(self):
        """계산기 상수가 PokeAPI 효과 문구와 어긋나지 않는지 확인 (PokeAPI 우선)."""
        eff = lambda k: self.db.execute("SELECT effect_en FROM item WHERE key=?", (k,)).fetchone()[0]
        self.assertIn("Attack by 50%", eff("choice-band"))
        self.assertIn("Special Attack by 50%", eff("choice-specs"))
        self.assertIn("10%", eff("muscle-band"))
        self.assertIn("10%", eff("wise-glasses"))
        self.assertIn("30%", eff("life-orb"))
        self.assertIn("20%", eff("expert-belt"))
        self.assertIn("Doubles", eff("light-ball"))

    def test_rejects(self):
        with self.assertRaises(ValueError):
            c.attack_decisive_power(self.db, "garchomp", "swords-dance", {})  # 변화기
        with self.assertRaises(ValueError):
            self.calc("earthquake", "metronome")  # 계산식 없는 도구
        with self.assertRaises(ValueError):
            self.calc("earthquake", "no-such-item")
        with self.assertRaises(ValueError):
            c.actual_stats(self.db, "nope", {})


class DamageRolls(unittest.TestCase):
    """기대값은 @smogon/calc 0.10.0(Showdown 계산기, Gen 9)에 같은 조건(Lv50, IV31, EV = 8×SP−4, 데미지에 영향 없는 특성)을 넣어 얻은 값이다(2026-10-22).
    타입 강화·힘의머리띠는 PokeAPI 값(6/5·11/10, U3)을 쓰고 Showdown은 4915/4096·4505/4096을 써서 위력에 따라 1 차이가 날 수 있다(아래 사례는 일치)."""

    @classmethod
    def setUpClass(cls):
        if not c.DB_PATH.exists():
            raise unittest.SkipTest("pokedex.sqlite 없음: python -m prep.build_db")
        cls.db = c.connect()

    SHOWDOWN = [  # (공격, 방어, 기술, 방어 HP, 16개 데미지)
        (("garchomp", "adamant", {"atk": 32}, None), ("dragonite", "hardy", {"hp": 32, "def": 32}, None), "dragon-claw",
            198, [122, 126, 126, 128, 128, 132, 132, 134, 134, 138, 138, 140, 140, 144, 144, 146]),
        (("garchomp", "adamant", {"atk": 32}, "choice-band"), ("tyranitar", "hardy", {"hp": 32}, None), "earthquake",
            207, [260, 264, 266, 270, 272, 276, 278, 282, 284, 288, 290, 294, 296, 300, 302, 308]),
        (("gengar", "modest", {"spa": 32}, "life-orb"), ("dragapult", "hardy", {}, None), "shadow-ball",
            163, [250, 252, 257, 257, 260, 265, 268, 268, 273, 276, 281, 281, 283, 289, 291, 296]),
        (("kingambit", "adamant", {"atk": 32}, "life-orb"), ("gengar", "hardy", {"hp": 32}, None), "iron-head",
            167, [152, 153, 156, 156, 157, 160, 161, 164, 165, 168, 169, 172, 173, 175, 177, 179]),
        (("gengar", "modest", {"spa": 32}, None), ("dragapult", "hardy", {"hp": 32, "spd": 32}, "assault-vest"), "sludge-bomb",
            195, [27, 27, 27, 27, 28, 28, 29, 29, 29, 30, 30, 30, 30, 31, 31, 32]),
        (("garchomp", "adamant", {"atk": 32}, None), ("tyranitar", "hardy", {"hp": 32}, "shuca-berry"), "earthquake",
            207, [87, 88, 90, 90, 91, 93, 93, 94, 96, 96, 97, 99, 99, 100, 102, 103]),
        (("gengar", "modest", {"spa": 32}, None), ("kingambit", "hardy", {"hp": 32}, None), "shadow-ball",
            207, [43, 44, 45, 45, 45, 46, 46, 47, 48, 48, 48, 49, 49, 50, 51, 51]),
        (("garchomp", "adamant", {"atk": 32}, "soft-sand"), ("kingambit", "hardy", {"hp": 32}, None), "earthquake",
            207, [194, 198, 198, 200, 204, 206, 210, 210, 212, 216, 218, 218, 222, 224, 228, 230]),
        (("garchomp", "adamant", {"atk": 32}, "muscle-band"), ("dragonite", "hardy", {"hp": 32, "def": 32}, None), "dragon-claw",
            198, [134, 138, 138, 140, 144, 144, 146, 146, 150, 150, 152, 152, 156, 156, 158, 162]),
    ]

    @staticmethod
    def build(t):
        return dict(zip(("form_key", "nature", "sp", "item"), t))

    def test_matches_showdown(self):
        for a, d, move, hp, rolls in self.SHOWDOWN:
            with self.subTest(attacker=a[0], item=a[3] or d[3], move=move):
                r = c.damage_rolls(self.db, self.build(a), self.build(d), move)
                self.assertEqual((r["hp"], r["rolls"]), (hp, rolls))

    SHOWDOWN_ABILITIES = [  # (공격: 폼·성격·SP·특성·공격 랭크, 방어: 폼·성격·SP·특성, 기술, 방어 HP, 16개 데미지) — 위협은 공격 랭크 −1
        (("pawmot", "adamant", {"atk": 32}, "iron-fist", 0), ("dragapult", "hardy", {"hp": 32}, "infiltrator"), "ice-punch",
            195, [132, 134, 134, 136, 138, 140, 140, 142, 144, 146, 148, 148, 150, 152, 154, 156]),  # iron_fist_ice_punch (2026-10-23)
        (("azumarill", "adamant", {"atk": 32}, "huge-power", 0), ("garchomp", "hardy", {"hp": 32}, "sand-veil"), "play-rough",
            215, [200, 200, 204, 206, 210, 212, 212, 216, 218, 222, 224, 224, 228, 230, 234, 236]),  # huge_power_play_rough
        (("azumarill", "adamant", {"atk": 32}, "huge-power", 0), ("garchomp", "hardy", {"hp": 32}, "sand-veil"), "aqua-jet",
            215, [45, 45, 46, 46, 48, 48, 48, 49, 49, 49, 51, 51, 51, 52, 52, 54]),  # huge_power_aqua_jet
        (("scizor", "adamant", {"atk": 32}, "technician", 0), ("dragapult", "hardy", {}, "infiltrator"), "bullet-punch",
            163, [72, 73, 73, 75, 75, 76, 76, 78, 79, 79, 81, 81, 82, 82, 84, 85]),  # technician_bullet_punch
        (("garchomp", "adamant", {"atk": 32}, "sand-veil", 0), ("dragonite", "hardy", {"hp": 32, "def": 32}, "multiscale"), "dragon-claw",
            198, [61, 63, 63, 64, 64, 66, 66, 67, 67, 69, 69, 70, 70, 72, 72, 73]),  # multiscale_dragon_claw
        (("garchomp", "adamant", {"atk": 32}, "sand-veil", -1), ("kingambit", "hardy", {"hp": 32}, "pressure"), "earthquake",
            207, [108, 108, 110, 110, 114, 114, 116, 116, 116, 120, 120, 122, 122, 126, 126, 128]),  # intimidated_eq
        (("dragalge", "modest", {"spa": 32}, "adaptability", 0), ("garchomp", "hardy", {"hp": 32}, "sand-veil"), "dragon-pulse",
            215, [204, 204, 208, 208, 212, 216, 216, 220, 220, 224, 228, 228, 232, 232, 236, 240]),  # adaptability_dragon_pulse
        (("medicham-mega", "adamant", {"atk": 32}, "pure-power", 0), ("kingambit", "hardy", {"hp": 32}, "pressure"), "close-combat",
            207, [640, 652, 660, 664, 676, 684, 688, 696, 708, 712, 720, 724, 736, 744, 748, 760]),  # pure_power_close_combat
    ]

    def test_abilities_and_stage_match_showdown(self):
        for (af, an, asp, aab, stage), (df, dn, dsp, dab), move, hp, rolls in self.SHOWDOWN_ABILITIES:
            with self.subTest(ability=aab if aab not in ("sand-veil",) else dab, move=move):
                r = c.damage_rolls(self.db, {"form_key": af, "nature": an, "sp": asp, "ability": aab, "atk_stage": stage},
                                   {"form_key": df, "nature": dn, "sp": dsp, "ability": dab}, move)
                self.assertEqual((r["hp"], r["rolls"]), (hp, rolls))

    def test_iron_fist_with_life_orb_matches_showdown(self):
        r = c.damage_rolls(self.db, {"form_key": "pawmot", "sp": {"atk": 32}, "nature": "adamant", "item": "life-orb", "ability": "iron-fist"},
                           {"form_key": "dragapult", "sp": {"hp": 32}, "nature": "hardy", "item": None, "ability": "infiltrator"}, "ice-punch")
        self.assertEqual(r["rolls"], [172, 174, 174, 177, 179, 182, 182, 185, 187, 190, 192, 192, 195, 198, 200, 203])

    def test_friend_case_pawmot_vs_mega_garchomp_z(self):
        """친구 사례 1(2026-10-23, 스마트누오 대조): A32 고집 철주먹 빠르모트 냉동펀치 → H2 C32 S32 조심 메가한카리아스Z(HP 185).
        생명의구슬 1/16(6.3%), 구애머리띠 12/16(75.0%), 철주먹 없거나 도구 없으면 0/16."""
        me = {"form_key": "garchomp-mega-z", "sp": {"hp": 2, "spa": 32, "spe": 32}, "nature": "modest", "item": None, "ability": "levitate"}
        def ko(item, ability):
            r = c.damage_rolls(self.db, {"form_key": "pawmot", "sp": {"atk": 32}, "nature": "adamant", "item": item, "ability": ability}, me, "ice-punch")
            return sum(x >= r["hp"] for x in r["rolls"])
        self.assertEqual((ko("life-orb", "iron-fist"), ko("choice-band", "iron-fist"), ko("life-orb", "volt-absorb"), ko(None, "iron-fist")), (1, 12, 0, 0))

    def test_levitate_and_multiscale_not_full_hp(self):
        r = c.damage_rolls(self.db, {"form_key": "garchomp"}, {"form_key": "rotom-wash", "ability": "levitate"}, "earthquake")
        self.assertEqual(r["rolls"], [0] * 16)
        full = c.damage_rolls(self.db, {"form_key": "garchomp"}, {"form_key": "dragonite", "ability": "multiscale"}, "dragon-claw")["rolls"]
        hurt = c.damage_rolls(self.db, {"form_key": "garchomp"}, {"form_key": "dragonite", "ability": "multiscale", "full_hp": False}, "dragon-claw")["rolls"]
        self.assertLess(full[-1], hurt[-1])

    def test_stage_stat(self):
        self.assertEqual([c.stage_stat(200, s) for s in (-1, 0, 1, -2)], [133, 200, 300, 100])

    def test_poke_round_half_down(self):
        self.assertEqual([c.poke_round(Fraction(x, 2)) for x in (3, 5, 7)], [1, 2, 3])  # 1.5→1, 2.5→2, 3.5→3
        self.assertEqual(c.poke_round(Fraction(51, 20)), 3)  # 2.55→3
        self.assertEqual(43 * 85 // 100, 36)  # 난수 단계는 내림(4-1절): 36.55 → 36

    def test_immunity_and_air_balloon(self):
        r = c.damage_rolls(self.db, {"form_key": "garchomp"}, {"form_key": "dragonite"}, "earthquake")  # 비행 타입 땅 무효
        self.assertEqual((r["rolls"], r["effectiveness"]), ([0] * 16, "0"))
        r = c.damage_rolls(self.db, {"form_key": "garchomp"}, {"form_key": "tyranitar", "item": "air-balloon"}, "earthquake")
        self.assertEqual(r["rolls"], [0] * 16)

    def test_rejects_special_formula_and_multi_hit(self):
        for move in ("body-press", "foul-play", "seismic-toss", "bullet-seed"):
            with self.subTest(move=move), self.assertRaises(ValueError):
                c.damage_rolls(self.db, {"form_key": "garchomp"}, {"form_key": "tyranitar"}, move)

    def test_speed_choice_scarf(self):
        s = c.speed(self.db, {"form_key": "garchomp", "sp": {"spe": 32}, "nature": "jolly"})
        self.assertEqual(s, (102 + 32 + 20) * 110 // 100)  # 169
        self.assertEqual(c.speed(self.db, {"form_key": "garchomp", "sp": {"spe": 32}, "nature": "jolly", "item": "choice-scarf"}), 253)  # 169×1.5=253.5→253

    def test_item_kind(self):
        k = lambda item, role: c.item_kind(self.db, item, role)
        self.assertEqual([k("choice-band", "attack"), k("soft-sand", "attack"), k("leftovers", "attack"), k("metronome", "attack")],
                         ["affects", "affects", "neutral", "unsupported"])
        self.assertEqual([k("assault-vest", "defense"), k("shuca-berry", "defense"), k("focus-sash", "defense"), k("leftovers", "defense"),
                          k("sitrus-berry", "defense"), k("choice-band", "defense"), k("", "defense")],
                         ["affects", "affects", "affects", "neutral", "recovery", "neutral", "none"])

    def test_defense_item_values_match_pokeapi_text(self):
        eff = lambda key: self.db.execute("SELECT effect_en FROM item WHERE key=?", (key,)).fetchone()[0]
        self.assertIn("Special Defense to 1.5", eff("assault-vest"))
        self.assertIn("immunity to Ground", eff("air-balloon"))
        self.assertIn("halve", eff("shuca-berry"))
        self.assertIn("1/4 max HP", eff("sitrus-berry"))
        self.assertIn("Speed by 50%", eff("choice-scarf"))


if __name__ == "__main__":
    unittest.main()
