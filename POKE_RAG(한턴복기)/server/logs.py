"""복기 기록 data/logs/reviews.jsonl (CEO C8-1, eng #3 R8). 한 줄 = 한 사건(kind: extract / review / feedback).
키·프롬프트·토큰 비밀값은 넣지 않는다(이름표만). 쓰기 실패는 복기를 막지 않는다(False 반환). 삭제는 같은 잠금 아래에서 파일을 다시 쓴다.
"""
import json
import os
import threading
from datetime import datetime, timedelta, timezone

import config

KST = timezone(timedelta(hours=9))
_lock = threading.Lock()


def now():
    return datetime.now(KST)


def append(record, path=None):
    path = path or config.REVIEW_LOG
    line = json.dumps({"ts": now().isoformat(timespec="seconds"), **record}, ensure_ascii=False)
    try:
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return True
    except OSError:
        return False


def read(path=None):
    """깨진 줄은 건너뛴다(쓰다 끊긴 마지막 줄 등)."""
    path = path or config.REVIEW_LOG
    if not path.exists():
        return []
    out = []
    with _lock, open(path, encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def delete_label(label, path=None):
    """그 이름표의 모든 줄을 지운다(삭제 요청). 지운 줄 수."""
    path = path or config.REVIEW_LOG
    with _lock:
        if not path.exists():
            return 0
        keep, gone = [], 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    mine = json.loads(line).get("label") == label
                except json.JSONDecodeError:
                    mine = False
                if mine:
                    gone += 1
                else:
                    keep.append(line)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(keep)
        os.replace(tmp, path)
    return gone
