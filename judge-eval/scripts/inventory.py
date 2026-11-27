"""Phase 1 메타데이터 수집. 앱 코드를 고치지 않고 읽기만 한다.

사용: python scripts/inventory.py  →  analysis/inventory_metrics.json
테스트 실행 결과는 run_all.py가 따로 채운다(여기서는 정적 수치만).
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS = {"A": ROOT / "apps" / "A", "B": ROOT / "apps" / "B"}
CODE_EXT = {".py", ".js", ".html", ".css"}
# 앱 코드로 세지 않는 경로: 수집 데이터, 문서, 에이전트 skill 사본, 캐시
SKIP_PARTS = {"data", "docs", ".agents", ".cache", "__pycache__", "node_modules", ".venv"}


def code_files(app_dir):
    for p in app_dir.rglob("*"):
        rel = p.relative_to(app_dir)
        if p.is_file() and p.suffix in CODE_EXT and not (set(rel.parts) & SKIP_PARTS):
            yield rel, p


def count_lines(p):
    return sum(1 for _ in p.open(encoding="utf-8", errors="ignore"))


def requirements(app_dir):
    reqs = []
    for f in app_dir.rglob("requirements*.txt"):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if line:
                reqs.append(line)
    return reqs


def git_meta():
    """이 비교 저장소의 git 기록. 두 앱 모두 원본 기록 없이 한 번에 들어왔다."""
    out = subprocess.run(["git", "-C", str(ROOT), "log", "--format=%H|%aI|%s"], capture_output=True, text=True).stdout
    rows = [r.split("|", 2) for r in out.splitlines() if r]
    return {"commits_in_exam_repo": len(rows), "first": rows[-1][1] if rows else None, "last": rows[0][1] if rows else None}


def main():
    result = {"exam_repo_git": git_meta(), "apps": {}}
    for name, d in APPS.items():
        by_ext, test_lines, files = {}, 0, 0
        for rel, p in code_files(d):
            n = count_lines(p)
            files += 1
            by_ext[p.suffix] = by_ext.get(p.suffix, 0) + n
            if "tests" in rel.parts or rel.name.startswith("test_"):
                test_lines += n
        reqs = requirements(d)
        result["apps"][name] = {
            "code_files": files,
            "code_lines_by_ext": dict(sorted(by_ext.items())),
            "code_lines_total": sum(by_ext.values()),
            "test_code_lines": test_lines,
            "python_requirements_pinned": len(reqs),
            "python_requirements": reqs,
            "doc_md_lines": sum(count_lines(p) for p in d.rglob("*.md") if not ({".agents"} & set(p.relative_to(d).parts))),
        }
    out = ROOT / "analysis" / "inventory_metrics.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "python_requirements"} for k, v in result["apps"].items()},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
