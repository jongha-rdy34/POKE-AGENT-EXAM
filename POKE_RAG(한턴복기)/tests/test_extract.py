"""자연어 추출(server/extract.py). LLM은 고정 응답으로 바꿔 흔들림 없이 확인한다(CEO S6)."""
import json
import unittest

from prep import calculator as c
from server import extract as ex


def fixed(obj):
    return lambda text: obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)


class Extract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not c.DB_PATH.exists():
            raise unittest.SkipTest("pokedex.sqlite 없음: python -m prep.build_db")
        cls.db = c.connect()

    def run_x(self, text, obj):
        return ex.extract(self.db, text, fixed(obj))

    def test_failure_types(self):
        def boom(text):
            raise RuntimeError("키 없음")
        self.assertEqual(ex.extract(self.db, "망나뇽 역린에 죽음", boom)["reason"], "llm_unavailable")
        self.assertEqual(self.run_x("x", "")["reason"], "empty")
        self.assertEqual(self.run_x("x", '{"type": "review", "my": ')["reason"], "broken_json")
        self.assertEqual(self.run_x("x", "죄송하지만 도와드릴 수 없어요")["reason"], "refusal")
        self.assertEqual(self.run_x("", {"type": "review"})["reason"], "empty_input")
        for r in (self.run_x("x", ""), self.run_x("x", "죄송")):
            self.assertEqual(r["type"], "fail")

    def test_retries_once_on_fail(self):
        replies = iter(['{"type": "fail"}', '{"type": "review", "my": "메한카Z", "opp": "빠르모트", "actor": "opp", "result": "ko"}'])
        r = ex.extract(self.db, "빠르모트가 그렇게 빠르지 않는데 왜 내 CS 조심 메한카Z가 죽은거지", lambda t: next(replies))
        self.assertEqual((r["type"], r["llm_calls"]), ("review", 2))
        self.assertEqual(r["fields"]["my_form_key"], "garchomp-mega-z")
        self.assertEqual(r["fields"]["my_build"], {"sp": {"spa": 32, "spe": 32, "hp": 2}, "nature": "modest"})  # CS·조심은 코드가 읽는다

    def test_rule_question_goes_to_chat(self):
        self.assertEqual(self.run_x("화상은 공격 -2랑 같음?", {"type": "rule"})["type"], "rule")

    def test_names_resolve_and_code_fenced_json(self):
        raw = '```json\n{"type": "review", "my": "한카리아스", "opp": "망나뇽", "move": "역린", "actor": "opp", "result": "ko"}\n```'
        r = self.run_x("망나뇽 역린에 내 한카리아스가 한 방에 죽었어", raw)
        self.assertEqual(r["fields"], {"my_form_key": "garchomp", "opp_form_key": "dragonite", "move_key": "outrage",
                                       "actor": "opp", "actual": {"kind": "ko"}})
        self.assertEqual(r["missing"], [])

    def test_invented_name_becomes_missing(self):
        r = self.run_x("가짜몬 무덤 공격", {"type": "review", "my": "가짜몬", "move": "Last Respects", "result": "ko"})
        self.assertNotIn("my_form_key", r["fields"])
        self.assertIn("my_form_key", r["missing"])
        self.assertTrue(any("가짜몬" in n for n in r["notes"]))
        self.assertEqual(r["fields"]["move_key"], "last-respects")  # 영문 기술 이름도 별칭에 있다

    def test_mega_and_form_names(self):
        r = self.run_x("메가 갑주무사 흡혈", {"type": "review", "my": "메가 갑주무사", "opp": "로토무", "move": "흡혈"})
        self.assertEqual((r["fields"]["my_form_key"], r["fields"]["opp_form_key"]), ("golisopod-mega", "rotom"))

    def test_actor_swapped_by_learnset(self):
        # 한카리아스는 하이퍼보이스를 못 배우고 님피아는 배운다 → LLM이 me라고 해도 opp로 바꾸고 확인에서 묻는다
        r = self.run_x("님피아 하이퍼보이스에 한카리아스 죽음", {"type": "review", "my": "한카리아스", "opp": "님피아",
                                                        "move": "하이퍼보이스", "actor": "me", "result": "ko"})
        self.assertEqual(r["fields"]["actor"], "opp")
        self.assertIn("actor", r["ask"])

    def test_speed_actor_filled_from_learnset(self):
        r = self.run_x("내 드래펄트가 드래곤애로 쓰려다가 상대 메가리자몽Y보다 느렸음",
                       {"type": "review", "my": "드래펄트", "opp": "메가리자몽Y", "move": "드래곤애로", "actor": None, "result": "outsped"})
        self.assertEqual(r["fields"]["actor"], "me")
        self.assertIn("actor", r["ask"])

    def test_mirror_asks_actor(self):
        r = self.run_x("미러전 한카리아스 지진", {"type": "review", "my": "한카리아스", "opp": "한카리아스", "move": "지진", "actor": "opp", "result": "ko"})
        self.assertIn("actor", r["ask"])
        self.assertIn("같은 포켓몬끼리라 누가 공격했는지 확인해 주세요", r["notes"])  # 확인 칩의 이유(디자인 A1)

    def test_sp_attaches_to_nearest_name(self):
        text = "AS 한카리아스한테 H32B32 망나뇽이 죽음"
        r = self.run_x(text, {"type": "review", "my": "망나뇽", "opp": "한카리아스", "move": "지진", "actor": "opp", "result": "ko"})
        self.assertEqual(r["fields"]["my_build"], {"sp": {"hp": 32, "def": 32}})
        self.assertEqual(r["fields"]["opp_sp"], {"atk": 32, "spe": 32, "hp": 2})  # 별칭은 남는 2를 H에

    def test_bad_values_are_dropped(self):
        r = self.run_x("한카 지진", {"type": "review", "my": "한카", "result": "dead", "actor": "both", "flags": ["crit", "lol"]})
        self.assertNotIn("actual", r["fields"])
        self.assertNotIn("actor", r["fields"])
        self.assertEqual(r["fields"]["flags"], ["crit"])

    def test_sp_prefixed_name(self):
        r = self.run_x("상대 드래펄트가 내 AS한카보다 먼저", {"type": "review", "my": "AS한카", "opp": "드래펄트", "move": "드래곤애로", "actor": "opp", "result": "outsped"})
        self.assertEqual(r["fields"]["my_form_key"], "garchomp")
        self.assertEqual(r["fields"]["my_build"], {"sp": {"atk": 32, "spe": 32, "hp": 2}})

    def test_missing_move_found_in_text(self):
        r = self.run_x("급소 맞고 내 망나뇽이 한카 역린에 죽음", {"type": "review", "my": "망나뇽", "opp": "한카", "move": None, "actor": "opp", "result": "ko"})
        self.assertEqual(r["fields"]["move_key"], "outrage")
        self.assertIn("move_key", r["ask"])
        self.assertIn("문장에서 기술 '역린'을 찾았어요. 맞는지 확인해 주세요", r["notes"])  # 받침 있으면 을(디자인 A2)

    def test_ko_with_hp_left_becomes_survived(self):
        r = self.run_x("핫삼 불릿펀치에 내 망나뇽 7할 남음", {"type": "review", "my": "망나뇽", "opp": "핫삼", "move": "불릿펀치", "actor": "opp", "result": "ko", "hp_band": "50-75"})
        self.assertEqual(r["fields"]["actual"], {"kind": "survived", "hp_band": "50-75"})
        self.assertIn("actual", r["ask"])

    def test_corrected_fields(self):
        before = {"my_form_key": "garchomp", "actor": "me"}
        self.assertEqual(ex.corrected(before, {"my_form_key": "garchomp", "actor": "opp", "move_key": "earthquake"}), ["actor", "move_key"])
        self.assertEqual(ex.corrected(before, dict(before, flags=[])), [])

    def test_store_expires(self):
        s = ex.Extractions(ttl=0)
        self.assertIsNone(s.get(s.put("t", {})))
        s = ex.Extractions()
        self.assertEqual(s.get(s.put("t", {"a": 1}))["result"], {"a": 1})


if __name__ == "__main__":
    unittest.main()
