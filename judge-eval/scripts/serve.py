"""두 앱 실행기 (Windows·macOS·Linux 공통). 앱 코드와 앱 .env는 건드리지 않고 환경변수로만 설정한다.

  python scripts/serve.py            # 두 앱을 띄우고 Ctrl+C까지 유지
  python scripts/serve.py --check    # 띄워서 상태만 확인하고 내림

다른 스크립트에서는:
  from serve import servers
  with servers(log_dir) as urls: ...   # 끝나면 서버를 내린다(지시서: 캡처하는 동안만 띄운다)

가상환경 위치: judge-eval/.env의 VENV_A, VENV_B. 없으면 저장소 옆 ../venvs/A, ../venvs/B.
"""
import argparse
import contextlib
import http.cookiejar
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

EVAL = Path(__file__).resolve().parents[1]          # judge-eval/
REPO = EVAL.parent
APP_A = REPO / "POKE_RAG(한턴복기)"
APP_B_BACKEND = REPO / "Poke-Agent-claude" / "backend"
PORT_A, PORT_B = 8101, 8102


def load_env():
    """judge-eval/.env를 읽는다(외부 패키지 없이). 이미 있는 환경변수가 우선한다."""
    env = {}
    p = EVAL / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k in env})
    return env


def venv_python(name, env):
    root = Path(env.get(f"VENV_{name}") or REPO.parent / "venvs" / name)
    for rel in ("Scripts/python.exe", "bin/python"):
        if (root / rel).exists():
            return str(root / rel)
    sys.exit(f"가상환경을 찾지 못했습니다: {root} (judge-eval/.env의 VENV_{name}로 지정)")


def invite_secret(env):
    """A_INVITE_TOKENS=이름표:비밀값 → 비밀값"""
    return env.get("A_INVITE_TOKENS", "eval:change-me").split(",")[0].split(":", 1)[1]


def _child_env(env, extra):
    e = {k: v for k, v in os.environ.items()}
    e.update(extra)
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def _wait(url, timeout=60):
    t = time.time()
    while time.time() - t < timeout:
        try:
            urllib.request.urlopen(url, timeout=3)
            return True
        except Exception:
            time.sleep(0.5)
    return False


@contextlib.contextmanager
def servers(log_dir=None):
    env = load_env()
    key = env.get("GEMINI_API_KEY", "")
    if not key:
        print("경고: judge-eval/.env에 GEMINI_API_KEY가 없습니다. LLM 단계는 실패합니다.", file=sys.stderr)
    base = env.get("GEMINI_OPENAI_BASE", "https://generativelanguage.googleapis.com/v1beta/openai/")
    model = env.get("APP_LLM_MODEL", "gemini-3.5-flash")
    cache_b = (EVAL / "apps_cache" / "B").resolve()      # 절대경로: B의 데이터 시점 고정
    log_dir = Path(log_dir or EVAL / "runs" / "serve")
    log_dir.mkdir(parents=True, exist_ok=True)

    specs = [
        ("A", APP_A, [venv_python("A", env), "-m", "uvicorn", "server.app:app", "--port", str(PORT_A), "--no-access-log"],
         {"INVITE_TOKENS": env.get("A_INVITE_TOKENS", "eval:change-me"), "OPENAI_API_KEY": key,
          "OPENAI_BASE_URL": base, "CHAT_MODEL": model}, f"http://127.0.0.1:{PORT_A}/"),
        ("B", APP_B_BACKEND, [venv_python("B", env), "-m", "uvicorn", "app.main:app", "--port", str(PORT_B)],
         {"GMS_API_KEY": key, "GMS_BASE_URL": base, "LLM_MODEL": model, "CACHE_DIR": str(cache_b)},
         f"http://127.0.0.1:{PORT_B}/health"),
    ]
    procs = []
    try:
        for name, cwd, cmd, extra, health in specs:
            log = open(log_dir / f"server_{name}.log", "w", encoding="utf-8")
            procs.append((subprocess.Popen(cmd, cwd=cwd, env=_child_env(env, extra), stdout=log, stderr=subprocess.STDOUT), log))
            if not _wait(health):
                raise RuntimeError(f"{name} 서버가 뜨지 않았습니다. 로그: {log_dir / f'server_{name}.log'}")
        yield {"A": f"http://127.0.0.1:{PORT_A}", "B": f"http://127.0.0.1:{PORT_B}",
               "A_login": f"http://127.0.0.1:{PORT_A}/?t={invite_secret(env)}", "model": model}
    finally:
        for p, log in procs:
            p.terminate()
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                p.kill()
            log.close()


def a_opener(urls):
    """A는 초대 토큰 쿠키가 있어야 API를 쓸 수 있다."""
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.open(urls["A_login"], timeout=10)
    return op


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    with servers() as urls:
        a_opener(urls)
        print(f"A {urls['A_login'].split('?')[0]}  (접속은 ?t=<비밀값>)\nB {urls['B']}/\n앱 LLM {urls['model']}")
        if not args.check:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    print("서버를 내렸습니다.")
