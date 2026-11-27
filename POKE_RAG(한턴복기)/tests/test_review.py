""".venv/Scripts/python -m unittest discover -s tests -t .  (프로젝트 루트에서)"""
import sqlite3
import unittest
from unittest import mock

import config
from prep import calculator as c
from prep import review


class CurrentSeason(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE meta_usage(season)")
        self.db.executemany("INSERT INTO meta_usage VALUES(?)", [("M-2",), ("M-10",), ("M-9",)])

    def test_latest_from_db_when_config_empty(self):
        with mock.patch.object(config, "CURRENT_SEASON", None):
            self.assertEqual(review.current_season(self.db), "M-10")  # 문자열 정렬이면 M-9가 나온다

    def test_config_value_wins(self):
        with mock.patch.object(config, "CURRENT_SEASON", "M-6"):
            self.assertEqual(review.current_season(self.db), "M-6")

    def test_empty_table_raises(self):
        self.db.execute("DELETE FROM meta_usage")
        with mock.patch.object(config, "CURRENT_SEASON", None), self.assertRaises(ValueError):
            review.current_season(self.db)


class Review(unittest.TestCase):
    """복기 계산 시나리오. 실제 DB(pokedb M-6·Smogon) 값에 기대므로 확률 숫자 대신 성질만 확인한다."""

    @classmethod
    def setUpClass(cls):
        if not config.DB_PATH.exists():
            raise unittest.SkipTest("pokedex.sqlite 없음: python -m prep.build_db")
        cls.db = c.connect()

    def build(self, form, nature="hardy", sp=None, item=None, ability=None):
        return {"form_key": form, "sp": sp or {}, "nature": nature, "item": item, "ability": ability}

    def test_parse_sp_text(self):
        self.assertEqual(review.parse_sp_text("A20 S32 한카리아스"), {"atk": 20, "spe": 32})
        self.assertEqual(review.parse_sp_text("AS 한카리아스", self.db), {"atk": 32, "spe": 32, "hp": 2})  # 남는 2는 H
        self.assertIsNone(review.parse_sp_text("한카리아스", self.db))
        with self.assertRaises(ValueError):
            review.parse_sp_text("A40 S32")  # 스탯당 최대 32
        # 한글에 붙여 쓴 표기(eng #3 F6)
        self.assertEqual(review.parse_sp_text("A20한카리아스"), {"atk": 20})
        self.assertEqual(review.parse_sp_text("H32B32 망나뇽"), {"hp": 32, "def": 32})
        self.assertEqual(review.parse_sp_text("AS한카", self.db), {"atk": 32, "spe": 32, "hp": 2})
        self.assertEqual(review.parse_sp_text("상대 S32인듯"), {"spe": 32})
        self.assertIsNone(review.parse_sp_text("BS32"))  # 영문 단어 안의 글자는 SP가 아니다

    def test_sp_mentions_keep_sides_apart(self):
        text = "AS 한카리아스한테 H32 B32 망나뇽이 죽음"
        found = review.sp_mentions(text, self.db)
        self.assertEqual([x["sp"] for x in found], [{"atk": 32, "spe": 32, "hp": 2}, {"hp": 32, "def": 32}])
        self.assertEqual(text[found[1]["start"]:found[1]["end"]], "H32 B32")

    def test_speed_and_trick_room(self):
        req = {"actor": "opp", "actual": {"kind": "outsped"}}
        fast, slow = self.build("dragapult", "timid", {"spe": 32}), self.build("garchomp")
        self.assertEqual(review.match_fraction(self.db, req, slow, fast)[0], 1.0)
        self.assertEqual(review.match_fraction(self.db, dict(req, flags=["trick_room"]), slow, fast)[0], 0.0)
        self.assertEqual(review.match_fraction(self.db, req, fast, fast)[0], 0.5)  # 동속

    def test_focus_sash_only_at_full_hp(self):
        req = {"actor": "me", "move_key": "dragon-claw", "actual": {"kind": "ko"}}
        me = self.build("garchomp", "adamant", {"atk": 32})
        self.assertGreater(review.match_fraction(self.db, req, me, self.build("dragapult"))[1], 0)
        self.assertEqual(review.match_fraction(self.db, req, me, self.build("dragapult", item="focus-sash"))[1], 0)
        self.assertGreater(review.match_fraction(self.db, dict(req, pre_hit_hp=0.5), me, self.build("dragapult", item="focus-sash"))[1], 0)

    def test_differs(self):
        base = {"zero_match": False, "undetermined": False, "causes": [{"key": "life-orb", "label": "life-orb", "prob": 0.6}]}
        self.assertFalse(review.differs(base, base)[0])
        other = dict(base, causes=[{"key": "life-orb", "label": "life-orb", "prob": 0.3}])
        self.assertTrue(review.differs(base, other)[0])  # 같은 1순위, 차이 30%p
        self.assertTrue(review.differs(base, dict(base, causes=[{"key": "_neutral", "label": "x", "prob": 0.6}]))[0])

    def test_survived_has_atk_minus1_with_conditions(self):
        out = review.review(self.db, {"my_form_key": "garchomp", "opp_form_key": "archaludon", "actor": "me",
                                      "move_key": "earthquake", "actual": {"kind": "survived", "hp_band": "25-50"}})
        for r in out["bases"].values():
            minus = [x for x in r["causes"] if x["key"] == "_atk_minus1"]
            self.assertTrue(minus and minus[0]["conditions"])
            self.assertNotIn("choice-scarf", [x["key"] for x in r["causes"]])  # 데미지 결과에 스카프는 영향 없음

    def test_rolls_follow_top_condition(self):
        out = review.review(self.db, {"my_form_key": "garchomp", "opp_form_key": "archaludon", "actor": "me",
                                      "move_key": "earthquake", "actual": {"kind": "survived", "hp_band": "25-50"}})
        for r in out["bases"].values():
            for x in r["causes"]:
                self.assertEqual(x["rolls"], f"가장 그럴듯한 조건에서 16번 중 {x['rolls_k']}번")
                self.assertGreater(x["rolls_k"], 0)

    def test_cache_gives_same_result(self):
        req = {"my_form_key": "dragonite", "opp_form_key": "garchomp", "actor": "opp", "move_key": "dragon-claw", "actual": {"kind": "ko"}}
        plain = sqlite3.connect(config.DB_PATH)
        self.assertEqual(review.review(plain, req), review.review(self.db, req))

    def test_speed_groups_only_scarf(self):
        out = review.review(self.db, {"my_form_key": "garchomp", "opp_form_key": "dragapult", "actor": "opp",
                                      "move_key": "dragon-darts", "actual": {"kind": "outsped"},
                                      "my_build": {"item": None, "sp": {"spe": 32}, "nature": "jolly"}})
        for r in out["bases"].values():
            self.assertLessEqual({x["key"] for x in r["causes"]}, {"choice-scarf", "_neutral"})

    def test_special_move_and_flags_are_reference_only(self):
        out = review.review(self.db, {"my_form_key": "garchomp", "opp_form_key": "garchomp", "actor": "opp",
                                      "move_key": "body-press", "actual": {"kind": "ko"}})
        self.assertTrue(out["reference_only"])
        self.assertEqual(out["bases"], {})
        out = review.review(self.db, {"my_form_key": "garchomp", "opp_form_key": "dragonite", "actor": "me",
                                      "move_key": "dragon-claw", "actual": {"kind": "ko"}, "flags": ["crit"]})
        self.assertTrue(out["reference_only"])
        self.assertTrue(any("급소" in u for u in out["unsupported"]))

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            review.review(self.db, {"my_form_key": "garchomp", "opp_form_key": "dragonite", "actor": "x",
                                    "move_key": "dragon-claw", "actual": {"kind": "ko"}})


if __name__ == "__main__":
    unittest.main()
