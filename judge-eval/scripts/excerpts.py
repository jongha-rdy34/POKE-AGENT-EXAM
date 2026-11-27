"""Phase 4 코드 발췌: packets/excerpt_spec.json의 함수·클래스를 원문 그대로 잘라 익명화한다(LLM 불필요).

  python scripts/excerpts.py
출력(판정 입력에 직접 넣지 않는 중간 산출물, 앱 글자 A/B 그대로):
  packets/_internal/excerpt_A.md, excerpt_B.md   → build_packets가 X/Y로 바꿔 패킷에 넣는다
  packets/_internal/excerpt_report.json           → 줄 수, 익명화 적중 목록
"""
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anonymize import redact  # noqa: E402

EVAL = Path(__file__).resolve().parents[1]
REPO = EVAL.parent
SPEC = EVAL / "packets" / "excerpt_spec.json"
OUT = EVAL / "packets" / "_internal"


def segments(path, names):
    """최상위 정의를 이름으로 찾아 (이름, 시작줄, 원문)을 파일 순서대로 돌려준다. 데코레이터 포함."""
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    found = {}
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in names:
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            found[node.name] = (start, "\n".join(lines[start - 1:node.end_lineno]))
    missing = [n for n in names if n not in found]
    if missing:
        raise SystemExit(f"{path}: 정의를 찾지 못함 {missing} (excerpt_spec.json 확인)")
    return sorted(((n, *found[n]) for n in names), key=lambda x: x[1])


def build(app, spec, max_lines):
    root = REPO / spec["root"]
    parts, hits, total = [], [], 0
    for role, files in spec["roles"].items():
        parts.append(f"### {role}")
        for rel, names in files.items():
            for name, start, code in segments(root / rel, names):
                code, h = redact(code)
                hits += [{"file": rel, "def": name, "rule": r, "text": t} for r, t in h]
                n = code.count("\n") + 1
                total += n
                # 파일 경로는 앱 안의 상대 경로만 보인다(저장소·폴더 이름 없음)
                rel_shown, _ = redact(rel)
                parts.append(f"`{rel_shown}` · `{name}` ({n}줄)\n```python\n{code}\n```")
    if total > max_lines:
        raise SystemExit(f"{app}: 발췌 {total}줄 > 상한 {max_lines}줄. excerpt_spec.json을 줄인다")
    return "\n\n".join(parts) + "\n", total, hits


def main():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"max_lines": spec["max_lines"], "apps": {}}
    for app in ("A", "B"):
        text, total, hits = build(app, spec[app], spec["max_lines"])
        (OUT / f"excerpt_{app}.md").write_text(text, encoding="utf-8")
        report["apps"][app] = {"lines": total, "redactions": len(hits), "hits": hits}
        print(f"{app}: {total}줄, 익명화 {len(hits)}곳")
    (OUT / "excerpt_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
