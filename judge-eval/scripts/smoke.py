"""실험 전 점검: 시나리오 S2~S5의 입력을 화면 대신 API로 한 번씩 보내 두 앱이 끝까지 도는지 본다.
앱은 고치지 않는다. 결과는 runs/smoke-<시각>/에 원문 그대로 저장한다. B는 이때 받은 외부 데이터가 apps_cache/B에 쌓인다.

  python scripts/smoke.py              # 전체
  python scripts/smoke.py --only A     # 한 앱만
LLM 호출: A 약 4회, B 요청 6회(요청마다 내부 호출 2~4회). 무료 한도에 걸리면 --gap 초를 늘린다.
"""
import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from serve import EVAL, a_opener, servers  # noqa: E402

MY = ["Garchomp", "Dragonite", "Incineroar", "Kingambit", "Gengar", "Rotom-Wash"]
OPP = ["Sneasler", "Charizard", "Tyranitar", "Gyarados", "Sylveon", "Whimsicott"]
NO_MEGA = {"my_holders": {}, "opp": "none"}
RULE = {"game": "champions", "battle": "singles"}

A_TEXT = {  # scenarios.yaml v2와 같은 문장
    "S2": "내 한카리아스가 상대 포푸니크보다 늦게 움직였고, 인파이트 한 방에 쓰러졌어",
    "S3": "상대 포푸니크가 내 팬텀보다 먼저 지옥찌르기를 썼는데, 내 팬텀은 HP 25~50% 남기고 버텼어",
    "S4_unknown_name": "내 피카츄몽이 상대 포푸니크한테 한 방에 쓰러졌어",
    "S4_rule_mismatch": "내 팬텀이 지진으로 상대 리자몽을 공격했어",
}


def post(opener, url, body, timeout=300):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t = time.time()
    try:
        r = opener.open(req, timeout=timeout)
        return r.status, r.read().decode("utf-8"), round(time.time() - t, 1)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore"), round(time.time() - t, 1)


def sse_events(text):
    out = []
    for block in text.split("\n\n"):
        ev = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in ev:
            out.append({"event": ev["event"], "data": json.loads(ev.get("data", "null"))})
    return out


def run_a(urls, save, gap):
    op = a_opener(urls)
    rows = []
    extracted = {}
    for sid, text in A_TEXT.items():
        code, body, sec = post(op, urls["A"] + "/api/feature/review/extract", {"text": text})
        save(f"A_{sid}_extract.json", body)
        d = json.loads(body) if code == 200 else {}
        extracted[sid] = d
        rows.append(("A", sid, "extract", code, sec, f"type={d.get('type')} missing={d.get('missing')} reason={d.get('reason')}"))
        time.sleep(gap)
    code, body, sec = post(op, urls["A"] + "/api/feature/review/extract", {"text": ""})
    save("A_S4_empty_extract.json", body)
    rows.append(("A", "S4_empty", "extract", code, sec, "빈 입력(화면은 버튼 비활성으로 막을 수 있음)"))

    def review(sid, d, extra=None):
        f = dict(d.get("fields", {}))
        if not {"my_form_key", "opp_form_key", "actor", "move_key", "actual"} <= f.keys():
            rows.append(("A", sid, "review", "-", 0, f"추출에 필수 칸이 없어 계산하지 않음: {sorted(f)}"))
            return
        body = {**f, **(extra or {}), "extraction_id": d.get("extraction_id")}
        code, text, sec = post(op, urls["A"] + "/api/feature/review", body)
        evs = sse_events(text) if code == 200 else []
        save(f"A_{sid}_review.json", json.dumps({"http": code, "events": evs or text}, ensure_ascii=False, indent=1))
        last = evs[-1] if evs else {}
        rows.append(("A", sid, "review", code, sec, f"last_event={last.get('event')} " +
                     (str(last.get("data", {}).get("headline", ""))[:80] if last.get("event") == "answer" else str(last.get("data"))[:120])))

    review("S2", extracted.get("S2", {}))
    review("S3", extracted.get("S3", {}))
    review("S4_rule_mismatch", extracted.get("S4_rule_mismatch", {}))
    review("S5", extracted.get("S2", {}), {"my_build": {"nature": "jolly", "sp": {"spe": 32}}})
    return rows


def run_b(urls, save, gap):
    op = urllib.request.build_opener()
    rows = []
    chat = urls["B"] + "/api/chat"

    def send(sid, body):
        code, text, sec = post(op, chat, {**RULE, **body})
        save(f"B_{sid}.json", text)
        d = json.loads(text) if code == 200 else {}
        rows.append(("B", sid, "chat", code, sec, f"status={d.get('status')} intent={d.get('intent')} "
                     f"error={(d.get('error') or {}).get('code')} answer={str(d.get('answer', ''))[:60]!r}"))
        time.sleep(gap)
        return d

    s2 = send("S2", {"message": "3마리 뭐 뽑아?", "my_team": MY, "opp_team": OPP, "mega_choice": NO_MEGA})
    sess = s2.get("session_id")
    send("S3", {"message": "상대 포푸니크한테 내 팬텀이 먼저 때릴 수 있어? 뭐 써야 돼?", "session_id": sess})
    send("S5", {"message": "상대 엘풍 대신 워시로토무로 바꿔서 다시 짜줘", "session_id": sess})
    send("S4_unknown_name", {"message": "상대 팀은 피카츄몽, 리자몽, 마기라스, 갸라도스, 님피아, 엘풍. 3마리 뭐 뽑아?",
                             "my_team": MY, "mega_choice": NO_MEGA})
    send("S4_empty", {"message": "3마리 뭐 뽑아?", "my_team": [], "opp_team": []})
    send("S4_rule_mismatch", {"message": "3마리 뭐 뽑아?", "my_team": MY, "opp_team": OPP[:5], "mega_choice": NO_MEGA})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["A", "B"])
    ap.add_argument("--gap", type=float, default=4.0, help="요청 사이 대기(초). 무료 한도 대비")
    args = ap.parse_args()
    out = EVAL / "runs" / f"smoke-{datetime.now():%Y%m%d-%H%M%S}"
    out.mkdir(parents=True)

    def save(name, text):
        (out / name).write_text(text, encoding="utf-8")

    rows = []
    with servers(out) as urls:
        if args.only in (None, "A"):
            rows += run_a(urls, save, args.gap)
        if args.only in (None, "B"):
            rows += run_b(urls, save, args.gap)
    lines = ["| app | case | call | http | sec | 결과 |", "|---|---|---|---|---|---|"]
    lines += [f"| {' | '.join(str(x) for x in r)} |" for r in rows]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n저장: {out}")


if __name__ == "__main__":
    main()
