"""한 턴 복기 서버 (agent.md 1.2, eng #3 R1·R3·R4·R7·R8).
  .venv/Scripts/python -m uvicorn server.app:app --port 8000 --no-access-log   # 접속 기록에 첫 ?t= 주소가 남지 않게
흐름: POST /api/feature/review/extract(문장 → 칸) → 화면의 "이렇게 이해했어요" 확인 → POST /api/feature/review(SSE 계산·설명).
계산은 스레드풀에서 요청마다 새 DB 연결로 돌리고(sqlite3는 스레드를 넘겨 쓸 수 없다), 동시에 2개까지만 돈다.
"""
import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config
from prep import calculator as c
from prep import review as rv
from server import access, logs, summary
from server import extract as ex

TYPE_KO = {"normal": "노말", "fire": "불꽃", "water": "물", "electric": "전기", "grass": "풀", "ice": "얼음", "fighting": "격투",
           "poison": "독", "ground": "땅", "flying": "비행", "psychic": "에스퍼", "bug": "벌레", "rock": "바위", "ghost": "고스트",
           "dragon": "드래곤", "dark": "악", "steel": "강철", "fairy": "페어리"}
CATEGORY_KO = {"physical": "물리", "special": "특수"}
MAX_TEXT = 300  # 자연어 한 줄 길이 상한(신뢰 경계)
FIELDS = ("my_form_key", "opp_form_key", "actor", "move_key", "actual", "flags", "my_build", "opp_sp", "pre_hit_hp")

quota = access.Quota()
extractions = ex.Extractions()
slots = asyncio.Semaphore(2)
EXTRACT_LLM = ex.default_llm  # 테스트에서 고정 응답으로 바꾼다
SUMMARY_LLM = summary.llm.chat


@asynccontextmanager
async def lifespan(app):
    quota.seed(logs.read())  # 재시작해도 오늘 쓴 횟수를 이어서 센다
    yield


app = FastAPI(title="한 턴 복기 코치", lifespan=lifespan)
app.middleware("http")(access.token_middleware)


def with_db(fn, *args):
    """스레드 안에서 연결을 열고 닫는다."""
    db = c.connect()
    try:
        return fn(db, *args)
    finally:
        db.close()


class ExtractIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT)


class Actual(BaseModel):
    kind: Literal["ko", "survived", "outsped", "slower"]
    hp_band: Literal["75+", "50-75", "25-50", "<25"] | None = None


class Build(BaseModel):
    sp: dict[str, int] | None = None
    nature: str | None = None
    item: str | None = None
    ability: str | None = None


class ReviewIn(BaseModel):
    session_id: str | None = Field(default=None, max_length=64)
    extraction_id: str | None = Field(default=None, max_length=64)
    my_form_key: str = Field(max_length=64)
    opp_form_key: str = Field(max_length=64)
    actor: Literal["me", "opp"]
    move_key: str = Field(max_length=64)
    actual: Actual
    flags: list[str] = Field(default_factory=list, max_length=10)
    my_build: Build | None = None
    opp_sp: dict[str, int] | None = None
    pre_hit_hp: float | None = Field(default=None, gt=0, le=1)


class FeedbackIn(BaseModel):
    answer: Literal["yes", "no", "unsure"]  # "그 턴이 진짜 패인이었나요?"(C-O3)


def _extract(db, text):
    """추출 + 확인 화면에 보일 이름(한글·타입)."""
    result = ex.extract(db, text, EXTRACT_LLM)
    f = result["fields"]
    result["labels"] = {side: _pokemon_one(db, f[key]) for side, key in (("my", "my_form_key"), ("opp", "opp_form_key")) if key in f}
    if "move_key" in f:
        result["labels"]["move"] = _move_one(db, f["move_key"])
    return result


@app.post("/api/feature/review/extract")
async def extract_route(body: ExtractIn, label: str = Depends(access.require_label)):
    quota.take(label, "extract", llm_calls=1)
    result = await run_in_threadpool(with_db, _extract, body.text)
    eid = extractions.put(body.text, result)
    calls = result.pop("llm_calls", 1)
    quota.add_llm(calls - 1)  # 다시 물은 호출도 서버 전체 상한에 넣는다
    logs.append({"kind": "extract", "label": label, "extraction_id": eid, "type": result["type"],
                 "reason": result.get("reason"), "llm_calls": calls})
    return {**result, "extraction_id": eid}


def _compute(db, req):
    out = rv.review(db, req)
    text, degraded, calls = summary.summarize(db, out, SUMMARY_LLM)
    return out, calls, summary.answer(db, out, req, text, degraded)


def _sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/feature/review")
async def review_route(body: ReviewIn, label: str = Depends(access.require_label)):
    req = body.model_dump(include=set(FIELDS), exclude_none=True)
    if body.my_build:
        req["my_build"] = body.my_build.model_dump(exclude_none=True)
    req["actual"] = body.actual.model_dump(exclude_none=True)
    quota.take(label, "review", llm_calls=1 if config.REVIEW_SUMMARY_LLM else 0)
    saved = extractions.get(body.extraction_id) if body.extraction_id else None
    review_id = uuid.uuid4().hex

    async def stream():
        t0 = time.perf_counter()
        yield _sse("status", {"state": "computing"})
        try:
            async with slots:
                out, calls, answer = await run_in_threadpool(with_db, _compute, req)
        except ValueError as e:  # 알 수 없는 폼·기술, SP 초과 등 입력 오류
            yield _sse("error", {"code": "bad_input", "message": str(e)})
            return
        except Exception:  # 추적 정보는 내보내지 않는다(NF2004)
            yield _sse("error", {"code": "internal", "message": "계산 중 문제가 생겼어요. 잠시 뒤 다시 시도해 주세요"})
            return
        answer["review_id"] = review_id
        yield _sse("answer", answer)
        logs.append({"kind": "review", "label": label, "review_id": review_id, "session_id": body.session_id,
                     "text": saved["text"] if saved else None, "request": req,
                     "corrected": ex.corrected(saved["result"].get("fields", {}), req) if saved else None,
                     "causes": {b: [x["label"] for x in r["causes"]] for b, r in out["bases"].items()},
                     "unsupported": out["unsupported"], "reference_only": out["reference_only"], "differs": out["differs"],
                     "degraded": answer["degraded"], "llm_calls": calls, "latency_ms": round((time.perf_counter() - t0) * 1000)})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})


@app.post("/api/feature/review/{review_id}/feedback")
def feedback_route(review_id: str, body: FeedbackIn, label: str = Depends(access.require_label)):
    if len(review_id) > 64:
        raise HTTPException(422, {"code": "bad_input", "message": "review_id"})
    return {"ok": logs.append({"kind": "feedback", "label": label, "review_id": review_id, "answer": body.answer})}


@app.post("/api/feature/review/delete")
def delete_route(label: str = Depends(access.require_label)):
    return {"deleted": logs.delete_label(label)}


@app.get("/api/quota")
def quota_route(label: str = Depends(access.require_label)):
    return {"remaining": quota.remaining(label)}


def _pokemon_one(db, form_key):
    k, n, t1, t2 = db.execute("SELECT form_key, name_ko, type1, type2 FROM pokemon WHERE form_key=?", (form_key,)).fetchone()
    return {"form_key": k, "name_ko": summary.display_name(n), "types": [TYPE_KO.get(t, t) for t in (t1, t2) if t]}


def _move_one(db, move_key):
    k, n, t, cat, p, pr = db.execute("SELECT move_key, name_ko, type, category, power, priority FROM move WHERE move_key=?", (move_key,)).fetchone()
    return {"move_key": k, "name_ko": n, "type": TYPE_KO.get(t, t), "category": CATEGORY_KO.get(cat, cat), "power": p, "priority": pr}


def _pokemon(db, q):
    rows = db.execute("""SELECT DISTINCT p.form_key, p.name_ko, p.type1, p.type2 FROM alias a JOIN pokemon p ON p.form_key = a.target_key
                         WHERE a.kind='pokemon' AND a.alias LIKE ? ORDER BY length(a.alias) LIMIT 20""", (q.replace("%", "") + "%",))
    return [{"form_key": k, "name_ko": summary.display_name(n), "types": [TYPE_KO.get(t, t) for t in (t1, t2) if t]} for k, n, t1, t2 in rows]


def _moves(db, form_key, q):
    sql = "SELECT DISTINCT m.move_key, m.name_ko, m.type, m.category, m.power FROM move m"
    where, args = ["m.category IN ('physical', 'special')"], []
    if form_key:  # 그 폼(또는 같은 종 기본 폼)이 배우는 기술(DR14)
        sql += " JOIN learnset l ON l.move_key = m.move_key"
        where.append("l.form_key IN (?, (SELECT form_key FROM pokemon WHERE is_default=1 AND species=(SELECT species FROM pokemon WHERE form_key=?)))")
        args += [form_key, form_key]
    if q:
        where.append("m.name_ko LIKE ?")
        args.append("%" + q.replace("%", "") + "%")
    rows = db.execute(f"{sql} WHERE {' AND '.join(where)} ORDER BY m.name_ko LIMIT 200", args)
    return [{"move_key": k, "name_ko": n, "type": TYPE_KO.get(t, t), "category": CATEGORY_KO.get(cat, cat), "power": p} for k, n, t, cat, p in rows]


@app.get("/api/pokemon")
async def pokemon_route(q: str = "", label: str = Depends(access.require_label)):
    return await run_in_threadpool(with_db, _pokemon, q[:20])


@app.get("/api/moves")
async def moves_route(form_key: str = "", q: str = "", label: str = Depends(access.require_label)):
    return await run_in_threadpool(with_db, _moves, form_key[:64], q[:20])


WEB = Path(__file__).resolve().parent.parent / "web"
if WEB.exists():  # 화면(4단계)이 생기면 같은 서버에서 정적 파일로 낸다
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
