"""챔피언스 도구 목록(prep/champions_items.py): Bulbapedia·Showdown 대조와 PokeAPI 키 대응. 원본은 data/raw/champions_items/."""
import sqlite3
import unittest

import config
from prep import champions_items as ci
from prep import review


class ChampionsItems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ci.RAW / "showdown" / "champions_items.ts").exists() or not config.DB_PATH.exists():
            raise unittest.SkipTest("원본 없음: python -m prep.champions_items download")

    def test_sources_agree_on_held_items(self):
        sd = {k for k, m in ci.showdown_allowed().items() if not m}
        bp = {k for k, m in ci.bulbapedia_allowed().items() if not m}
        self.assertEqual(sd, bp)  # 2026-10-23: 85종 일치. 업데이트 뒤 어긋나면 어느 쪽이 늦었는지 확인
        self.assertIn("lifeorb", sd)
        self.assertNotIn("choiceband", sd)
        self.assertNotIn("assaultvest", sd)  # pokedb M-2 더블에 1건 있지만 두 출처 모두 사용 불가

    def test_loaded_with_pokeapi_keys(self):
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE item (key TEXT)")
        db.executemany("INSERT INTO item VALUES (?)", [(k,) for k in ("life-orb", "choice-scarf", "focus-sash", "garchompite-z", "kings-rock")])
        n, warn = ci.load_into(db)
        keys = {k for (k,) in db.execute("SELECT key FROM champion_item")}
        self.assertTrue({"life-orb", "choice-scarf", "stick", "kings-rock"} <= keys)  # Leek → PokeAPI 옛 키 stick
        self.assertEqual(db.execute("SELECT is_mega FROM champion_item WHERE key='garchompite-z'").fetchone(), (1,))
        self.assertTrue(any("PokeAPI 도구 표에 없는 이름" in w for w in warn))  # 작은 표라 대부분 못 찾는다

    def test_review_uses_official_list(self):
        db = sqlite3.connect(config.DB_PATH)
        items = review.champions_items(db)
        self.assertTrue({"life-orb", "aspear-berry", "cheri-berry"} <= items)  # 실전 통계엔 0건이지만 게임에는 있다
        self.assertFalse({"choice-band", "choice-specs", "assault-vest"} & items)


if __name__ == "__main__":
    unittest.main()
