"""초대 토큰·한도(server/access.py)와 복기 기록(server/logs.py)."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import config
from server import access, logs


def app_with(quota):
    app = FastAPI()
    app.middleware("http")(access.token_middleware)

    @app.get("/")
    def home():
        return {"ok": True}

    @app.post("/api/review")
    def review(label: str = Depends(access.require_label)):
        quota.take(label, "review")
        return {"label": label}

    return app


class Tokens(unittest.TestCase):
    def setUp(self):
        p = mock.patch.multiple(config, INVITE_TOKENS={"s3cret": "친구A"}, DAILY_REVIEWS_PER_TOKEN=2, DAILY_LLM_CALLS=10)
        p.start()
        self.addCleanup(p.stop)
        self.quota = access.Quota()
        self.client = TestClient(app_with(self.quota), base_url="https://testserver")

    def test_no_token_403(self):
        r = self.client.post("/api/review")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["detail"]["code"], "no_token")
        bad = self.client.get("/?t=wrong", follow_redirects=False)  # 화면: 초대 안내를 띄우도록 t를 뗀 주소로
        self.assertEqual((bad.status_code, bad.headers["location"]), (303, "https://testserver/"))
        self.assertNotIn("invite=wrong", bad.headers.get("set-cookie", ""))
        self.assertEqual(self.client.get("/api/review?t=wrong").status_code, 403)  # API: 그대로 403

    def test_link_becomes_cookie_and_clean_url(self):
        r = self.client.get("/?t=s3cret", follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertNotIn("t=", r.headers["location"])
        self.assertIn("httponly", r.headers["set-cookie"].lower())
        self.assertEqual(r.headers["referrer-policy"], "no-referrer")
        self.assertEqual(self.client.post("/api/review").json(), {"label": "친구A"})  # 쿠키로 통과

    def test_daily_limit_429(self):
        self.client.get("/?t=s3cret", follow_redirects=False)
        self.assertEqual([self.client.post("/api/review").status_code for _ in range(3)], [200, 200, 429])
        self.assertEqual(self.quota.remaining("친구A")["review"], 0)

    def test_server_wide_llm_cap(self):
        with mock.patch.object(config, "DAILY_REVIEWS_PER_TOKEN", 100):
            self.quota.llm = 10
            self.quota.day = logs.now().date().isoformat()
            with self.assertRaises(Exception) as e:
                self.quota.take("친구A", "review")
            self.assertEqual(e.exception.detail["code"], "server_limit")

    def test_seed_from_today_log_only(self):
        today = logs.now().date().isoformat()
        self.quota.seed([{"ts": today + "T10:00:00+09:00", "kind": "review", "label": "친구A", "llm_calls": 1},
                         {"ts": "2000-01-01T10:00:00+09:00", "kind": "review", "label": "친구A", "llm_calls": 1}])
        self.assertEqual(self.quota.remaining("친구A")["review"], 1)
        self.assertEqual(self.quota.llm, 1)

    def test_day_rolls_over(self):
        self.quota.take("친구A", "review")
        self.quota.day = "2000-01-01"
        self.assertEqual(self.quota.remaining("친구A")["review"], 2)


class Logs(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / "logs" / "reviews.jsonl"

    def test_append_read_delete(self):
        logs.append({"kind": "review", "label": "친구A", "review_id": "r1", "text": "한카 지진"}, self.path)
        logs.append({"kind": "feedback", "label": "친구A", "review_id": "r1", "answer": "yes"}, self.path)
        logs.append({"kind": "review", "label": "친구B", "review_id": "r2"}, self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write('{"broken"\n')
        self.assertEqual(len(logs.read(self.path)), 3)
        self.assertEqual(logs.delete_label("친구A", self.path), 2)
        self.assertEqual([r["label"] for r in logs.read(self.path)], ["친구B"])

    def test_write_failure_does_not_raise(self):
        bad = Path(self.dir.name) / "file"
        bad.write_text("x")
        self.assertFalse(logs.append({"kind": "review"}, bad / "under-a-file.jsonl"))

    def test_no_secret_in_record(self):
        logs.append({"kind": "review", "label": "친구A"}, self.path)
        self.assertNotIn("s3cret", self.path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
