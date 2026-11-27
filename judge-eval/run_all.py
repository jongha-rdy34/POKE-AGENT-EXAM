"""Phase 2~6을 한 번에 다시 실행한다.

  python run_all.py --dry-run            # 판정 모델마다 1건 호출 + 비용 추정까지(본 판정 없음)
  python run_all.py                      # 전체(캡처 → 발췌 → 패킷 → 판정 → 집계)
  python run_all.py --reuse-captures     # captures/를 다시 받지 않고 재사용
  python run_all.py --from judge         # 특정 단계부터 (capture|excerpts|packets|judge|aggregate)
  python run_all.py --mock               # 키 없이 판정 단계를 가짜 모델로(흐름 점검)

각 단계는 별도 스크립트다. 아직 없는 단계(capture.py, build_packets.py)는 건너뛰지 않고 멈춘다.
Claude 하위 에이전트 판정은 API로 부를 수 없어서 judge 단계에서 작업 파일만 만든다(진행 세션이 처리).
"""
import argparse
import subprocess
import sys
from pathlib import Path

EVAL = Path(__file__).resolve().parent
PY = sys.executable
STEPS = ["capture", "excerpts", "packets", "judge", "aggregate"]


def run(cmd, what):
    print(f"\n== {what}: {' '.join(str(c) for c in cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=EVAL)
    if r.returncode:
        sys.exit(f"{what} 실패(종료 코드 {r.returncode}). 이 단계부터 다시: python run_all.py --from {what}")


def need(path, what):
    if not (EVAL / path).exists():
        sys.exit(f"{what} 단계 스크립트가 없습니다: {path}")
    return EVAL / path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reuse-captures", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--from", dest="start", choices=STEPS, default="capture")
    a = ap.parse_args()
    todo = STEPS[STEPS.index(a.start):]

    if "capture" in todo:
        if a.reuse_captures and any((EVAL / "captures").rglob("*.png")):
            print("== capture: captures/ 재사용")
        else:
            run([PY, need("scripts/capture.py", "capture")], "capture")
    if "excerpts" in todo:
        run([PY, need("scripts/excerpts.py", "excerpts")], "excerpts")
    if "packets" in todo:
        run([PY, need("scripts/build_packets.py", "packets")], "packets")
    if "judge" in todo:
        judge = need("judges/judge.py", "judge")
        extra = ["--mock"] if a.mock else []
        if a.dry_run:
            run([PY, judge, "--dry-run", *extra], "judge")
            print("\n--dry-run: 본 판정을 하지 않았습니다. 비용 추정과 dry run 결과를 확인한 뒤 --from judge로 다시 실행하세요.")
            return
        run([PY, judge, *extra], "judge")
        run([PY, judge, "--claude-tasks"], "judge")
        print("Claude 판정: judges/claude_tasks/의 작업을 진행 세션의 하위 에이전트로 처리한 뒤 "
              "python judges/import_manual.py judges/claude_answers")
    if "aggregate" in todo:
        run([PY, need("scripts/aggregate.py", "aggregate")], "aggregate")


if __name__ == "__main__":
    main()
