"""수동 판정(Codex 세션, Claude 하위 에이전트, 대안으로 ChatGPT 앱) 응답 가져오기.

사용: python judges/import_manual.py judges/raw/openai          (Codex 수동 판정 → judges/raw/openai.jsonl)
      python judges/import_manual.py judges/claude_answers       (Claude 하위 에이전트 → judges/raw/claude_answers.jsonl)
  {run_id}.json 파일들과 log.csv(run_id,시각,모델 이름,재요청 횟수)를 읽어 judges/raw/<폴더 이름>.jsonl을 만든다.
  집계(aggregate.py)는 파일 이름을 판정 모델 이름으로 쓴다(openai, claude).
  응답 내용은 고치지 않는다. 스키마 위반은 status=schema_fail로 남긴다.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schema import parse, validate  # noqa: E402


def main(folder):
    folder = Path(folder)
    log = {}
    if (folder / "log.csv").exists():
        with open(folder / "log.csv", encoding="utf-8") as f:
            for row in csv.reader(f):
                if row and row[0] != "run_id":
                    log[row[0]] = {"at": row[1], "model_shown": row[2], "retries": int(row[3] or 0)}
    out, ok = [], 0
    for p in sorted(folder.glob("*.json")):
        run_id = p.stem
        mode = "absolute" if run_id.startswith("abs_") else "pairwise"
        raw = p.read_text(encoding="utf-8")
        rec = {"source": folder.name, "run_id": run_id, "mode": mode, "raw": raw, **log.get(run_id, {})}
        rec["judge_model"] = rec.get("model_shown")   # 화면에 보인 모델 이름(log.csv). 없으면 집계가 응답 JSON의 값을 쓴다
        try:
            obj = parse(raw)
            errs = validate(obj, mode)
        except Exception as e:  # JSON 아님
            obj, errs = None, [f"parse: {e}"]
        rec.update(parsed=obj, errors=errs, status="ok" if not errs else "schema_fail")
        ok += not errs
        out.append(rec)
    raw = Path(__file__).resolve().parent / "raw"
    raw.mkdir(exist_ok=True)
    dest = raw / f"{folder.name}.jsonl"
    dest.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    print(f"{len(out)}건 중 {ok}건 통과 → {dest}")
    missing = sorted(set(log) - {r["run_id"] for r in out})
    if missing:
        print("log.csv에는 있으나 응답 파일이 없음:", ", ".join(missing))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "judges/raw/openai")
