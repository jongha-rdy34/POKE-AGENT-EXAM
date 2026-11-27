"""복기 기록 집계 (CEO C8-1·C-O6). 친구 테스트 판정과 미룬 TODOS 순서("확인 불가"가 많은 것부터)를 정하는 데 쓴다.
  .venv/Scripts/python -m data.eval.aggregate_reviews [기록 경로] [--exclude 이름표,이름표]   # 기본으로 검수용 이름표(design-review)는 뺀다
기록 줄 형식(server/logs.py): kind=review {label, review_id, corrected[], unsupported[], degraded, latency_ms, reference_only}
                              kind=feedback {label, review_id, answer}  · kind=extract {label, type, reason}
"""
import statistics
import sys
from collections import Counter
from pathlib import Path

import config
from server import logs


NOT_FRIENDS = {"design-review"}  # 디자인 검수용 토큰(2026-10-23). 친구 테스트 집계에 넣지 않는다


def summarize(records, exclude=NOT_FRIENDS):
    records = [r for r in records if r.get("label") not in exclude]
    reviews = [r for r in records if r.get("kind") == "review"]
    extracts = [r for r in records if r.get("kind") == "extract"]
    feedback = [r for r in records if r.get("kind") == "feedback"]
    unsupported = Counter(u.split(":")[0] for r in reviews for u in r.get("unsupported", []))
    lat = [r["latency_ms"] for r in reviews if isinstance(r.get("latency_ms"), (int, float))]
    return {
        "reviews": len(reviews),
        "by_label": dict(Counter(r.get("label") for r in reviews)),
        "extract_types": dict(Counter(r.get("type") for r in extracts)),
        "extract_fail_reasons": dict(Counter(r.get("reason") for r in extracts if r.get("type") == "fail")),
        "corrected_rate": round(sum(bool(r.get("corrected")) for r in reviews) / len(reviews), 3) if reviews else None,
        "corrected_fields": dict(Counter(f for r in reviews for f in r.get("corrected", []))),
        "reference_only": sum(bool(r.get("reference_only")) for r in reviews),
        "degraded": sum(bool(r.get("degraded")) for r in reviews),
        "unsupported": dict(unsupported.most_common()),
        "feedback": dict(Counter(r.get("answer") for r in feedback)),
        "latency_ms_median": statistics.median(lat) if lat else None,
    }


if __name__ == "__main__":
    import json
    args = sys.argv[1:]
    exclude = set(NOT_FRIENDS)
    if "--exclude" in args:
        i = args.index("--exclude")
        exclude |= set(args[i + 1].split(","))
        del args[i:i + 2]
    path = Path(args[0]) if args else config.REVIEW_LOG
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(summarize(logs.read(path), exclude), ensure_ascii=False, indent=1))
