"""초대 토큰과 하루 한도 (CEO C3-1, eng #3 R3).
첫 접속 ?t=비밀값 → HttpOnly 쿠키로 바꾸고 t를 뗀 주소로 보낸다(주소·Referer·방문 기록으로 새지 않게). 모든 응답에 Referrer-Policy: no-referrer.
한도: 토큰당 하루 복기·문장 읽기 횟수 + 서버 전체 하루 LLM 호출 수. 날짜는 한국 시간. 재시작하면 오늘 기록(reviews.jsonl)으로 다시 센다.
uvicorn은 --no-access-log로 띄운다(접속 기록에 첫 ?t= 주소가 남지 않게).
"""
import threading
from collections import Counter

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

import config
from server import logs

COOKIE = "invite"
LIMITS = {"review": lambda: config.DAILY_REVIEWS_PER_TOKEN, "extract": lambda: config.DAILY_EXTRACTS_PER_TOKEN}
FORBIDDEN = {"code": "no_token", "message": "초대 링크로 접속해 주세요"}


def label_of(secret):
    return config.INVITE_TOKENS.get(secret or "")


async def token_middleware(request: Request, call_next):
    t = request.query_params.get("t")
    if t is None:
        resp = await call_next(request)
    elif label_of(t):
        resp = RedirectResponse(str(request.url.remove_query_params("t")), status_code=303)
        resp.set_cookie(COOKIE, t, httponly=True, samesite="strict", secure=request.url.scheme == "https", max_age=30 * 86400)
    elif request.url.path.startswith("/api/"):
        resp = JSONResponse(FORBIDDEN, status_code=403)
    else:  # 틀린 초대 링크로 화면을 열면 JSON 대신 t를 뗀 화면으로 보내고, 화면이 API 403을 받아 초대 안내를 띄운다(디자인 E5)
        resp = RedirectResponse(str(request.url.remove_query_params("t")), status_code=303)
        resp.delete_cookie(COOKIE)
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


def require_label(request: Request):
    """API 의존성: 쿠키의 토큰 → 이름표. 없거나 모르는 토큰이면 403."""
    label = label_of(request.cookies.get(COOKIE))
    if not label:
        raise HTTPException(403, FORBIDDEN)
    return label


class Quota:
    def __init__(self):
        self._lock = threading.Lock()
        self.day, self.used, self.llm = None, Counter(), 0

    def _roll(self):
        today = logs.now().date().isoformat()
        if today != self.day:
            self.day, self.used, self.llm = today, Counter(), 0

    def seed(self, records):
        """오늘 기록으로 다시 센다. 기록 줄: kind(extract/review), label, llm_calls."""
        with self._lock:
            self._roll()
            for r in records:
                if str(r.get("ts", ""))[:10] == self.day and r.get("kind") in LIMITS:
                    self.used[r.get("label"), r["kind"]] += 1
                    self.llm += int(r.get("llm_calls", 0))

    def take(self, label, kind, llm_calls=1):
        """한 번 쓴다. 한도를 넘으면 429(쓰지 않음)."""
        with self._lock:
            self._roll()
            if self.used[label, kind] >= LIMITS[kind]():
                raise HTTPException(429, {"code": "token_limit", "message": "오늘 이용 횟수를 다 썼어요. 내일 다시 이용해 주세요"})
            if self.llm + llm_calls > config.DAILY_LLM_CALLS:
                raise HTTPException(429, {"code": "server_limit", "message": "오늘 서버 사용량이 다 찼어요. 내일 다시 이용해 주세요"})
            self.used[label, kind] += 1
            self.llm += llm_calls

    def add_llm(self, n):
        """이미 쓴 호출을 더한다(막지 않음). 다음 take부터 상한에 걸린다."""
        with self._lock:
            self._roll()
            self.llm += max(0, n)

    def remaining(self, label):
        with self._lock:
            self._roll()
            return {k: max(0, f() - self.used[label, k]) for k, f in LIMITS.items()}
