""".venv/Scripts/python -m unittest discover -s tests -t .  (프로젝트 루트에서)"""
import sqlite3
import unittest

from prep import smogon


class FormKey(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE pokemon(form_key, species, is_default)")
        self.db.executemany("INSERT INTO pokemon VALUES(?,?,?)", [
            ("garchomp", "garchomp", 1), ("salamence-mega", "salamence", 0), ("mimikyu-disguised", "mimikyu", 1),
            ("meowstic-male", "meowstic", 1), ("meowstic-female-mega", "meowstic", 0), ("indeedee-female", "indeedee", 0),
            ("tauros-paldea-blaze-breed", "tauros", 0), ("mr-rime", "mr-rime", 1)])
        self.keys = {r[0] for r in self.db.execute("SELECT form_key FROM pokemon")}

    def test_mapping_rules(self):
        cases = {"Garchomp": "garchomp", "Salamence-Mega": "salamence-mega", "Mimikyu": "mimikyu-disguised",  # 종 이름 → 기본 폼
                 "Meowstic-F-Mega": "meowstic-female-mega", "Indeedee-F": "indeedee-female",  # -F → -female
                 "Tauros-Paldea-Blaze": "tauros-paldea-blaze-breed", "Mr. Rime": "mr-rime", "Nope": None}
        for name, want in cases.items():
            with self.subTest(name=name):
                self.assertEqual(smogon.form_key(self.db, name, self.keys), want)


class ShowdownIds(unittest.TestCase):
    def setUp(self):
        self.idx = {smogon.showdown_id(k): k for k in ("choice-scarf", "rocky-helmet", "stick", "rough-skin", "dragon-claw")}

    def test_to_pokeapi(self):
        pairs = [("choicescarf", 5.0), ("rockyhelmet", 2.0), ("nothing", 1.0), ("leek", 0.5), ("dragonclaw", 3.0), ("", 4.0), ("mystery", 0.1)]
        out, missing = smogon.to_pokeapi(pairs, self.idx)
        self.assertEqual(dict(out), {"choice-scarf": 5.0, "": 5.0, "dragon-claw": 3.0, "rocky-helmet": 2.0, "stick": 0.5, "showdown:mystery": 0.1})
        self.assertEqual(missing, ["mystery"])
        self.assertEqual(out[0][1], 5.0)  # 가중치 큰 순(도구 없음 1 + 빈 칸 4가 ""로 합쳐짐)


if __name__ == "__main__":
    unittest.main()
