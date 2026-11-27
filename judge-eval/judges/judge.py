"""Phase 5 판정 실행기.

  python judges/judge.py --plan                 # 호출 목록·예상 토큰·비용만 출력(호출 없음)
  python judges/judge.py --dry-run              # 판정 모델마다 1건씩 실제 호출 → judges/raw/dryrun_*.jsonl
  python judges/judge.py                        # 본 실행(사용자 확인 뒤)
  python judges/judge.py --mock                 # 가짜 판정 모델로 전체 흐름 시험(키 불필요, judges/raw_mock/)
  python judges/judge.py --claude-tasks         # Claude 하위 에이전트용 작업 파일 생성(judges/claude_tasks/)

패킷 형식(build_packets가 만든다):
  packets/X/packet.md   텍스트(목적·기능 목록·시나리오 설명·코드 발췌·객관 지표). 캡처는 [[img:파일명]] 자리표시
  packets/X/images/*.png
  packets/Y/...         (X/Y ↔ A/B 배정은 packets/mapping.secret.json, 판정 입력에 넣지 않는다)

원본 응답은 전부 judges/raw/{judge}.jsonl에 한 줄씩 남긴다. 응답이 스키마를 어기면 같은 대화에서 최대 2회 다시 요청한다.
"""
import argparse
import base64
import json
import os
import random
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

EVAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL / "judges"))
sys.path.insert(0, str(EVAL / "scripts"))
from schema import parse, validate  # noqa: E402

PROMPTS = EVAL / "judges" / "prompts"
PACKETS = Path(os.environ.get("JUDGE_PACKETS_DIR") or EVAL / "packets")  # 시험용으로 바꿀 수 있다
RUNS = 3                    # Claude·OpenAI 등 판정 모델 1개당 회차
# Gemini 판정은 두 모델을 섞는다(사용자 결정 2026-11-27 개정: 12건 = flash-lite 6 + flash 6, 3회차).
# 형식 "모델:단위+단위:호출간격초". 단위: "1"=1회차 4건 전부, "3abs"=3회차 절대 X·Y, "3pw"=3회차 쌍비교 XY·YX.
# 절대는 X·Y, 쌍비교는 XY·YX를 늘 짝으로 받으므로 모델마다 앱·순서가 균형을 이룬다.
GEMINI_PLAN_DEFAULT = "gemini-3.5-flash-lite:1+3abs:6,gemini-3.5-flash:2+3pw:20"
CLAUDE_JUDGE_MODEL = "claude-sonnet-5-5"   # 하위 에이전트 판정 모델(사용자 결정 2026-11-27: 제작 모델 Opus와 분리)
RPD = {"gemini-3.5-flash-lite": 500, "gemini-3.5-flash": 20}   # 무료 등급 하루 한도(STATUS 6절)
MAX_RETRY = 2
RETRY_MSG = "출력 형식을 어겼습니다. 지정한 JSON 하나만, 다른 글자 없이 다시 출력하세요."
IMG_RX = re.compile(r"\[\[img:([^\]]+)\]\]")

# 토큰 추정(호출 전 비용 보고용). 실제 값은 응답의 usage로 다시 기록한다.
EST = {"chars_per_token": 1.6,          # 한국어·코드 섞인 텍스트의 보수적 추정
       "image_tokens": {"gemini": 258 * 4, "openai": 1105, "mock": 0},  # 이미지 1장 상한 추정
       "output_tokens": 600}
# 가격(USD / 100만 토큰). 모르면 None으로 두고 "요금 미기재"로 보고한다. 무료 플랜이면 0.
PRICES = {"gemini": {"in": None, "out": None, "note": "무료 플랜이면 0. 유료 등급 단가는 AI Studio 요금표 확인"},
          "openai": {"in": 2.50, "out": 10.00, "note": "gpt-4o 공시가 가정(확인 필요)"},
          "mock": {"in": 0, "out": 0, "note": ""}}


def load_env():
    env = {}
    p = EVAL / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


# ---------------------------------------------------------------- 요청 목록
def plan(units=None):
    """단위마다 판정 목록. 정수(또는 "3")=그 회차 4건, "3abs"=절대 X·Y, "3pw"=쌍비교 XY·YX."""
    jobs = []
    for u in (units or range(1, RUNS + 1)):
        m = re.fullmatch(r"(\d+)(abs|pw)?", str(u))
        if not m:
            raise SystemExit(f"판정 단위를 읽지 못함: {u!r} (예: 1, 3abs, 3pw)")
        r, part = int(m.group(1)), m.group(2)
        if part in (None, "abs"):
            for app in ("X", "Y"):
                jobs.append({"run_id": f"abs_{app}_r{r}", "mode": "absolute", "app": app, "order": None, "run": r})
        if part in (None, "pw"):
            for order in ("XY", "YX"):
                jobs.append({"run_id": f"pw_{order}_r{r}", "mode": "pairwise", "app": None, "order": order, "run": r})
    return jobs


def read_packet(label):
    d = PACKETS / label
    text = (d / "packet.md").read_text(encoding="utf-8")
    return text, d / "images"


def render(job, judge_model):
    """프롬프트 텍스트와 [텍스트/이미지] 조각 목록. 이미지는 패킷 안 자리표시 순서대로 붙는다."""
    system = (PROMPTS / "system.md").read_text(encoding="utf-8")
    if job["mode"] == "absolute":
        body, img_dir = read_packet(job["app"])
        tpl = (PROMPTS / "absolute.md").read_text(encoding="utf-8")
        text = (tpl.replace("{{APP_LABEL}}", job["app"]).replace("{{JUDGE_MODEL}}", judge_model)
                .replace("{{RUN}}", str(job["run"])).replace("{{PACKET}}", body))
        dirs = {job["app"]: img_dir}
    else:
        first, second = job["order"][0], job["order"][1]
        b1, d1 = read_packet(first)
        b2, d2 = read_packet(second)
        tpl = (PROMPTS / "pairwise.md").read_text(encoding="utf-8")
        text = (tpl.replace("{{FIRST}}", first).replace("{{SECOND}}", second).replace("{{ORDER}}", job["order"])
                .replace("{{JUDGE_MODEL}}", judge_model).replace("{{RUN}}", str(job["run"]))
                .replace("{{PACKET_FIRST}}", b1.replace("[[img:", f"[[img:{first}/"))
                .replace("{{PACKET_SECOND}}", b2.replace("[[img:", f"[[img:{second}/")))
        dirs = {first: d1, second: d2}
    parts, pos = [], 0
    for m in IMG_RX.finditer(text):
        parts.append(("text", text[pos:m.start()]))
        ref = m.group(1)
        label, name = (ref.split("/", 1) if "/" in ref else (job["app"], ref))
        parts.append(("image", dirs[label] / name))
        pos = m.end()
    parts.append(("text", text[pos:]))
    return system, parts


def estimate(parts, provider):
    chars = sum(len(p) for k, p in parts if k == "text")
    imgs = sum(1 for k, _ in parts if k == "image")
    return round(chars / EST["chars_per_token"]) + imgs * EST["image_tokens"].get(provider, 1000), imgs


# ---------------------------------------------------------------- 판정 모델 호출
def _openai_compatible(base, model, temperature, messages, key):
    body = {"model": model, "messages": messages, "response_format": {"type": "json_object"}}
    if temperature is not None:
        body["temperature"] = temperature
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    return d["choices"][0]["message"]["content"] or "", d.get("usage", {}), d.get("model", model)


def to_messages(system, parts):
    content = []
    for kind, val in parts:
        if kind == "text":
            if val.strip():
                content.append({"type": "text", "text": val})
        else:
            b64 = base64.b64encode(Path(val).read_bytes()).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    return [{"role": "system", "content": system}, {"role": "user", "content": content}]


class Mock:
    """키 없이 흐름을 시험하는 가짜 판정 모델. 첫 응답을 일부러 틀리게 해 재요청 경로도 탄다."""
    def __init__(self, seed=0, name="mock", model="mock-judge", runs=None):
        self.rng = random.Random(seed)
        self.name, self.model, self.runs, self.gap, self.temperature = name, model, list(runs or range(1, RUNS + 1)), 0, None

    def call(self, messages, job):
        if sum(1 for m in messages if m["role"] == "user") == 1 and self.rng.random() < 0.3:
            return "점수는 다음과 같습니다: 4점", {}, self.model
        if job["mode"] == "absolute":
            obj = {"scores": {k: self.rng.randint(2, 5) for k in ("accuracy", "purpose_fit", "usability", "ui", "code")},
                   "pairwise": None}
        else:
            obj = {"scores": None, "pairwise": {k: self.rng.choice(["X", "Y", "tie"]) for k in
                                                ("accuracy", "purpose_fit", "usability", "ui", "code", "overall")}}
        obj.update(judge_model=self.model, mode=job["mode"], app=job["app"], order=job["order"], run=job["run"],
                   rationale=["가짜 근거 1", "가짜 근거 2", "가짜 근거 3"])
        return json.dumps(obj, ensure_ascii=False), {"prompt_tokens": 0, "completion_tokens": 0}, self.model


class OpenAICompatible:
    def __init__(self, name, base, model, key, temperature, runs=None, gap=None):
        self.name, self.base, self.model, self.key, self.temperature = name, base, model, key, temperature
        self.runs, self.gap = list(runs or range(1, RUNS + 1)), gap

    def call(self, messages, job):
        return _openai_compatible(self.base, self.model, self.temperature, messages, self.key)


def judge_one(provider, job, gap):
    system, parts = render(job, provider.model)
    messages = to_messages(system, parts)
    attempts, rec = [], None
    for attempt in range(MAX_RETRY + 1):
        t = time.time()
        try:
            text, usage, served = provider.call(messages, job)
        except urllib.error.HTTPError as e:
            attempts.append({"http": e.code, "error": e.read().decode("utf-8", "ignore")[:500]})
            rec = {"status": "http_error"}
            break
        attempts.append({"raw": text, "usage": usage, "served_model": served, "sec": round(time.time() - t, 1)})
        try:
            obj = parse(text)
            errs = validate(obj, job["mode"])
        except Exception as e:
            obj, errs = None, [f"parse: {e}"]
        rec = {"status": "ok" if not errs else "schema_fail", "parsed": obj, "errors": errs}
        if not errs:
            break
        messages = messages + [{"role": "assistant", "content": text}, {"role": "user", "content": RETRY_MSG}]
        time.sleep(gap)
    return {"judge": provider.name, "judge_model": provider.model, **job,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "temperature": getattr(provider, "temperature", None), "retries": len(attempts) - 1,
            "attempts": attempts, **rec}


def gemini_plan(spec):
    """"모델:단위+단위:간격" 목록 → [(모델, [단위], 간격)]. 모든 모델을 합쳐 판정 하나가 두 번 배정되면 멈춘다."""
    items, seen = [], {}
    for part in spec.split(","):
        model, units, gap = (part.strip().split(":") + ["20"])[:3]
        units = [u.strip() for u in units.split("+") if u.strip()]
        for j in plan(units):
            if j["run_id"] in seen:
                raise SystemExit(f"{j['run_id']}이 {seen[j['run_id']]}와 {model}에 두 번 배정됨")
            seen[j["run_id"]] = model
        items.append((model, units, float(gap)))
    return items


def providers(args, env):
    spec = env.get("JUDGE_GEMINI_PLAN", GEMINI_PLAN_DEFAULT)
    if args.mock:
        return [Mock(seed=k, name="gemini", model=m, runs=runs) for k, (m, runs, _) in enumerate(gemini_plan(spec))]
    out = []
    if env.get("GEMINI_API_KEY"):
        base = env.get("GEMINI_OPENAI_BASE", "https://generativelanguage.googleapis.com/v1beta/openai/")
        for model, runs, gap in gemini_plan(spec):
            out.append(OpenAICompatible("gemini", base, model, env["GEMINI_API_KEY"],
                                        float(env.get("JUDGE_TEMPERATURE", "0.2")), runs, gap))
    if env.get("OPENAI_API_KEY") and env.get("JUDGE_OPENAI_MODEL"):   # 선택: 크레딧을 충전한 경우만
        out.append(OpenAICompatible("openai", "https://api.openai.com/v1", env["JUDGE_OPENAI_MODEL"],
                                    env["OPENAI_API_KEY"], float(env.get("JUDGE_TEMPERATURE", "0.2"))))
    return out


# ---------------------------------------------------------------- Claude 하위 에이전트용 작업 파일
def write_claude_tasks():
    """Claude 판정은 API가 아니라 진행 세션의 하위 에이전트가 한다(모델: CLAUDE_JUDGE_MODEL, Agent 도구의 model="sonnet").
    작업마다 프롬프트 파일을 만든다.
    하위 에이전트는 이 폴더와 이미지 경로만 읽고, 응답 JSON을 judges/claude_answers/{run_id}.json에 저장한다.
    그다음 `python judges/import_manual.py judges/claude_answers`로 검사한다(출력: judges/raw/claude_answers.jsonl)."""
    out = EVAL / "judges" / "claude_tasks"
    out.mkdir(parents=True, exist_ok=True)
    for job in plan():
        system, parts = render(job, CLAUDE_JUDGE_MODEL)
        lines = [system, ""]
        for kind, val in parts:
            lines.append(val if kind == "text" else f"\n[이미지: {Path(val).resolve()} 를 Read로 열어 볼 것]\n")
        (out / f"{job['run_id']}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(plan())}건 → {out}")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--plan", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--claude-tasks", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--gap", type=float, default=20.0, help="호출 사이 대기(초). 무료 RPM 5·TPM 250K 대비")
    args = ap.parse_args()
    if args.claude_tasks:
        return write_claude_tasks()
    env = load_env()
    provs = providers(args, env)
    if not provs:
        sys.exit("판정 모델 키가 없습니다(judge-eval/.env의 GEMINI_API_KEY). 키 없이 흐름만 보려면 --mock")
    if args.plan or args.dry_run:
        print("| 판정 모델 | 회차 | 건수 | 이미지/건 | 예상 입력 토큰 합 | 예상 출력 토큰 합 | 예상 비용 | 무료 하루 한도 |\n|---|---|---|---|---|---|---|---|")
        for p in provs:
            jobs = plan(p.runs)
            tin, imgs = 0, 0
            for j in jobs:
                t, i = estimate(render(j, p.model)[1], p.name)
                tin, imgs = tin + t, max(imgs, i)
            tout = EST["output_tokens"] * len(jobs)
            pr = PRICES.get(p.name, {})
            cost = ("요금 미기재" if pr.get("in") is None else f"${(tin * pr['in'] + tout * pr['out']) / 1e6:.2f}")
            rpd = RPD.get(p.model)
            warn = "" if rpd is None or len(jobs) * (1 + MAX_RETRY) <= rpd else " ⚠ 재요청까지 하면 하루에 못 끝날 수 있음"
            print(f"| {p.name} `{p.model}` | {','.join(map(str, p.runs))} | {len(jobs)} | 최대 {imgs} | {tin:,} | {tout:,} | "
                  f"{cost} {pr.get('note', '')} | {rpd if rpd else '?'}{warn} |")
        print(f"Claude 하위 에이전트 `{CLAUDE_JUDGE_MODEL}` {len(plan())}건은 이 세션 사용량으로 처리(API 비용 없음). "
              "OpenAI는 Codex 수동 12건.")
        if args.plan:
            return
    raw_dir = Path(os.environ.get("JUDGE_RAW_DIR") or EVAL / "judges" / ("raw_mock" if args.mock else "raw"))
    raw_dir.mkdir(parents=True, exist_ok=True)
    # 회차 순서대로 모델을 번갈아 부른다(시간대가 한 모델에 몰리지 않게). dry run은 모델마다 첫 건만.
    work = []
    for p in provs:
        jobs = plan(p.runs)
        work += [(j["run"], k, p, j) for k, j in enumerate(jobs[:1] if args.dry_run else jobs)]
    work.sort(key=lambda w: (w[0], w[1]))
    # 이어서 실행: 같은 파일에 status=ok로 이미 있는 (세부 모델, run_id)는 건너뛴다(무료 한도로 며칠에 나눠 돌릴 때)
    done = set()
    if not args.dry_run:
        for p in provs:
            f = raw_dir / f"{p.name}.jsonl"
            if f.exists():
                for line in f.read_text(encoding="utf-8").splitlines():
                    r = json.loads(line) if line.strip() else {}
                    if r.get("status") == "ok":
                        done.add((r.get("judge_model"), r.get("run_id")))
    skipped = [w for w in work if (w[2].model, w[3]["run_id"]) in done]
    work = [w for w in work if (w[2].model, w[3]["run_id"]) not in done]
    if skipped:
        print(f"이미 끝난 {len(skipped)}건 건너뜀, 남은 {len(work)}건")
    dests = set()
    for _, _, p, j in work:
        dest = raw_dir / (f"dryrun_{p.name}.jsonl" if args.dry_run else f"{p.name}.jsonl")
        dests.add(dest)
        gap = 0 if args.mock else (p.gap if p.gap is not None else args.gap)
        rec = judge_one(p, j, gap)
        with open(dest, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"{p.name} `{p.model}` {j['run_id']}: {rec['status']} (재요청 {rec['retries']})")
        time.sleep(gap)
    print("→ " + ", ".join(str(d) for d in sorted(dests)))


if __name__ == "__main__":
    main()
