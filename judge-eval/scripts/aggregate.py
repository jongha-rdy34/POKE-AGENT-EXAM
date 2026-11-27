"""Phase 6 집계. 판정 원본(judges/raw/*.jsonl)과 X/Y 배정표만 읽는다. LLM 불필요, 외부 패키지 불필요.

  python scripts/aggregate.py                       # → analysis/summary.csv, analysis/report.md
  python scripts/aggregate.py --raw-dir D --mapping M --out-dir O   # 시험용

summary.csv는 긴 형식: metric,judge,app,item,value,n,note
report.md의 수치는 summary.csv를 다시 읽어서만 채운다(지시서 완료 기준).
"""
import argparse
import csv
import json
import re
import statistics as st
from collections import defaultdict
from itertools import combinations
from pathlib import Path

EVAL = Path(__file__).resolve().parents[1]
ITEMS = ("accuracy", "purpose_fit", "usability", "ui", "code")
PAIR_ITEMS = ITEMS + ("overall",)
RUN_RX = re.compile(r"^(abs)_([XY])_r(\d+)$|^(pw)_(XY|YX)_r(\d+)$")
CLAUDE = "claude"


# ---------------------------------------------------------------- 읽기
def load(raw_dir):
    """판정 모델별 레코드. API 기록(judge.py)과 수동 가져오기(import_manual.py) 두 형식을 같은 모양으로 맞춘다."""
    recs = []
    for f in sorted(Path(raw_dir).glob("*.jsonl")):
        if f.name.startswith("dryrun_"):
            continue
        judge = f.stem.replace("_answers", "")          # claude_answers.jsonl → claude
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            m = RUN_RX.match(r.get("run_id", ""))
            if not m:
                continue
            if m.group(1):
                mode, app, order, run = "absolute", m.group(2), None, int(m.group(3))
            else:
                mode, app, order, run = "pairwise", None, m.group(5), int(m.group(6))
            recs.append({"judge": r.get("judge", judge) if r.get("judge") != "mock" else judge, "mode": mode,
                         "label": app, "order": order, "run": run, "ok": r.get("status") == "ok",
                         "parsed": r.get("parsed") if r.get("status") == "ok" else None,
                         "retries": r.get("retries", 0),
                         "judge_model": r.get("judge_model") or (r.get("parsed") or {}).get("judge_model")})
    return recs


def real(label, mapping):
    return mapping.get(label, label) if label in ("X", "Y") else label   # tie는 그대로


# ---------------------------------------------------------------- 지표
def krippendorff_alpha(units, metric):
    """units: {unit: [coder 값, ...]} (값이 2개 이상인 unit만 쓴다). metric: 'interval' | 'nominal'."""
    def d(a, b):
        return (a - b) ** 2 if metric == "interval" else float(a != b)
    pairable = [v for v in units.values() if len(v) >= 2]
    n = sum(len(v) for v in pairable)
    if n < 2:
        return None, 0
    do = sum(sum(d(a, b) for a, b in combinations(v, 2)) * 2 / (len(v) - 1) for v in pairable) / n
    allv = [x for v in pairable for x in v]
    de = sum(d(a, b) for a, b in combinations(allv, 2)) * 2 / (n * (n - 1))
    if de == 0:
        return (1.0 if do == 0 else None), len(pairable)
    return 1 - do / de, len(pairable)


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return st.mean(xs) if xs else None


def compute(recs, mapping):
    """판정 모델(공급사) 단위로 값을 구하고, ALL은 판정 모델별 값의 단순 평균(동일 가중)이다.
    Gemini처럼 한 판정 모델 안에 여러 모델을 섞은 경우 "gemini:모델" 내역 행을 따로 남긴다(ALL에는 넣지 않음)."""
    rows = []

    def add(metric, judge, app, item, value, n, note=""):
        rows.append({"metric": metric, "judge": judge, "app": app, "item": item,
                     "value": "" if value is None else round(value, 4), "n": n, "note": note})

    judges = sorted({r["judge"] for r in recs})
    groups = {j: [r for r in recs if r["judge"] == j] for j in judges}
    for j in judges:
        models = sorted({r.get("judge_model") or "" for r in groups[j]} - {""})
        if len(models) > 1:
            for m in models:
                groups[f"{j}:{m}"] = [r for r in groups[j] if r.get("judge_model") == m]
    EQ = "판정 모델별 값의 단순 평균(동일 가중)"

    # 실패율(운영 지표라 ALL은 전체 건수 기준)
    for g, rs in list(groups.items()) + [("ALL", recs)]:
        add("fail_rate", g, "", "", (sum(not r["ok"] for r in rs) / len(rs)) if rs else None, len(rs), "스키마 실패·HTTP 오류")

    def ok(rs, mode):
        return [r for r in rs if r["ok"] and r["mode"] == mode]

    def score(r, item):
        sc = r["parsed"]["scores"]
        return sum(sc[k] for k in ITEMS) if item == "total" else sc[item]

    # 절대 평가
    for app in ("A", "B"):
        for item in ITEMS + ("total",):
            per = {}
            for g, rs in groups.items():
                vals = [score(r, item) for r in ok(rs, "absolute") if real(r["label"], mapping) == app]
                add("abs_mean", g, app, item, st.mean(vals) if vals else None, len(vals))
                add("abs_sd", g, app, item, st.stdev(vals) if len(vals) > 1 else None, len(vals), "회차 간 표준편차")
                if g in judges:
                    per[g] = (st.mean(vals) if vals else None, len(vals))
            means = [v for v, _ in per.values() if v is not None]
            add("abs_mean", "ALL", app, item, _mean(means), sum(n for _, n in per.values()), EQ)
            add("abs_sd", "ALL", app, item, st.stdev(means) if len(means) > 1 else None, len(means), "판정 모델 평균들 사이의 표준편차")

    # 쌍비교 선택 비율
    for item in PAIR_ITEMS:
        per = {}
        for g, rs in groups.items():
            ch = [real(r["parsed"]["pairwise"][item], mapping) for r in ok(rs, "pairwise")]
            for app in ("A", "B", "tie"):
                add("pw_rate", g, app, item, (ch.count(app) / len(ch)) if ch else None, len(ch))
            if g in judges:
                per[g] = ch
        for app in ("A", "B", "tie"):
            add("pw_rate", "ALL", app, item, _mean([c.count(app) / len(c) for c in per.values() if c]),
                sum(len(c) for c in per.values()), EQ)

    # 위치 편향: 같은 판정 모델·같은 회차(=같은 세부 모델)에서 XY와 YX의 선택(실제 앱)이 다른 비율, 먼저 보인 쪽 선택률
    for item in PAIR_ITEMS:
        flips, firsts = {}, {}
        for g, rs in groups.items():
            by = defaultdict(dict)
            for r in ok(rs, "pairwise"):
                by[r["run"]][r["order"]] = real(r["parsed"]["pairwise"][item], mapping)
            pairs = [v for v in by.values() if {"XY", "YX"} <= v.keys()]
            fl = (sum(v["XY"] != v["YX"] for v in pairs) / len(pairs)) if pairs else None
            add("position_flip_rate", g, "", item, fl, len(pairs), "순서만 바꿨을 때 선택이 달라진 비율")
            fs = [r["parsed"]["pairwise"][item] == r["order"][0] for r in ok(rs, "pairwise") if r["parsed"]["pairwise"][item] != "tie"]
            fp = (sum(fs) / len(fs)) if fs else None
            add("first_position_pick_rate", g, "", item, fp, len(fs), "tie 제외, 먼저 보인 쪽을 고른 비율(0.5면 편향 없음)")
            if g in judges:
                flips[g], firsts[g] = (fl, len(pairs)), (fp, len(fs))
        add("position_flip_rate", "ALL", "", item, _mean([v for v, _ in flips.values()]), sum(n for _, n in flips.values()), EQ)
        add("first_position_pick_rate", "ALL", "", item, _mean([v for v, _ in firsts.values()]), sum(n for _, n in firsts.values()), EQ)

    # 판정 모델 간 일치도(Krippendorff's alpha). coder=판정 모델, unit=(앱/순서, 항목, 회차).
    # 회차 수가 다른 판정 모델(Gemini 10회차)은 다른 판정 모델과 겹치는 회차(1~3)만 비교에 들어간다.
    absr = [r for r in recs if r["ok"] and r["mode"] == "absolute"]
    pw = [r for r in recs if r["ok"] and r["mode"] == "pairwise"]
    for item in ITEMS:
        u = defaultdict(list)
        for r in absr:
            u[(real(r["label"], mapping), item, r["run"])].append(r["parsed"]["scores"][item])
        a, n = krippendorff_alpha(u, "interval")
        add("alpha_abs_interval", "ALL", "", item, a, n, "unit=(앱,항목,회차), coder=판정 모델")
    code = {"A": 0, "B": 1, "tie": 2}
    for item in PAIR_ITEMS:
        u = defaultdict(list)
        for r in pw:
            u[(r["order"], item, r["run"])].append(code[real(r["parsed"]["pairwise"][item], mapping)])
        a, n = krippendorff_alpha(u, "nominal")
        add("alpha_pw_nominal", "ALL", "", item, a, n, "unit=(순서,항목,회차), coder=판정 모델")

    # 자기 선호 점검: Claude 판정 − 나머지 판정 모델 평균(동일 가중)
    others = [j for j in judges if j != CLAUDE]
    if CLAUDE in judges and others:
        def abs_mean(j, app, item):
            v = [r["parsed"]["scores"][item] for r in ok(groups[j], "absolute") if real(r["label"], mapping) == app]
            return (st.mean(v) if v else None), len(v)
        for app in ("A", "B"):
            for item in ITEMS:
                c, cn = abs_mean(CLAUDE, app, item)
                o = [abs_mean(j, app, item) for j in others]
                om = _mean([v for v, _ in o])
                add("self_pref_abs_diff", CLAUDE, app, item, (c - om) if c is not None and om is not None else None,
                    f"{cn}/{sum(n for _, n in o)}", "Claude 평균 − 다른 판정 모델 평균(동일 가중)")

        def a_rate(j):
            ch = [real(r["parsed"]["pairwise"]["overall"], mapping) for r in ok(groups[j], "pairwise")]
            return (ch.count("A") / len(ch)) if ch else None, len(ch)
        c, cn = a_rate(CLAUDE)
        o = [a_rate(j) for j in others]
        om = _mean([v for v, _ in o])
        if c is not None and om is not None:
            add("self_pref_pw_A_rate_diff", CLAUDE, "A", "overall", c - om, f"{cn}/{sum(n for _, n in o)}",
                "종합에서 A를 고른 비율 차(Claude − 나머지, 동일 가중)")
    return rows


def objective_rows(path):
    rows = []
    if not Path(path).exists():
        return rows
    with open(path, encoding="utf-8") as f:
        data = list(csv.DictReader(f))
    for app in sorted({d["app"] for d in data}):
        ds = [d for d in data if d["app"] == app]
        for v in sorted({d["verdict"] for d in ds}):
            rows.append({"metric": "objective_count", "judge": "", "app": app, "item": v,
                         "value": sum(d["verdict"] == v for d in ds), "n": len(ds), "note": "objective/results.csv"})
    return rows


# ---------------------------------------------------------------- 쓰기
def write_csv(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "judge", "app", "item", "value", "n", "note"])
        w.writeheader()
        w.writerows(rows)


def report(csv_path, out_path):
    """summary.csv만 읽어 보고서를 만든다. 해석 문장은 쓰지 않고, 사람이 채울 자리를 표시한다."""
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    def get(metric, judge="ALL", app="", item=""):
        for r in rows:
            if (r["metric"], r["judge"], r["app"], r["item"]) == (metric, judge, app, item):
                return r["value"], r["n"]
        return "", ""

    def fmt(v, pct=False):
        if v in ("", None):
            return "—"
        v = float(v)
        return f"{v * 100:.0f}%" if pct else f"{v:.2f}"

    judges = sorted({r["judge"] for r in rows if r["judge"] not in ("", "ALL") and ":" not in r["judge"]})
    submodels = sorted({r["judge"] for r in rows if ":" in r["judge"]})
    L = ["# 판정 결과 보고서", "",
         "> 자동 생성(`scripts/aggregate.py`). 모든 수치는 `analysis/summary.csv`에서 읽었다. "
         "결론은 인과가 아니라 \"이 두 사례에서 관찰된 차이와 그 한계\"로만 적는다.", "",
         "## 요약 (5줄)", ""]
    ta, _ = get("abs_mean", app="A", item="total")
    tb, _ = get("abs_mean", app="B", item="total")
    wa, n = get("pw_rate", app="A", item="overall")
    wb, _ = get("pw_rate", app="B", item="overall")
    wt, _ = get("pw_rate", app="tie", item="overall")
    fl, fn = get("position_flip_rate", item="overall")
    al, _ = get("alpha_pw_nominal", item="overall")
    fr, frn = get("fail_rate")
    L += [f"1. 절대 평가 합계(5항목, 25점 만점) 평균: A {fmt(ta)}, B {fmt(tb)}.",
          f"2. 쌍비교 종합 선택: A {fmt(wa, True)}, B {fmt(wb, True)}, 동률 {fmt(wt, True)} (n={n}).",
          f"3. 순서를 바꿨을 때 종합 선택이 달라진 비율: {fmt(fl, True)} (쌍 {fn}개).",
          f"4. 판정 모델 간 일치도(종합, Krippendorff's alpha nominal): {fmt(al)}.",
          f"5. 판정 실패율(스키마·HTTP): {fmt(fr, True)} (n={frn}). 조건마다 결과물이 1개라 차이의 원인은 가릴 수 없다.", ""]

    L += ["## 1. 절대 평가 (판정 모델별 평균의 평균 ± 판정 모델 간 표준편차, 1~5)", "",
          "판정 모델(공급사)을 동일 가중으로 평균했다. 실패한 판정이 있으면 판정 모델마다 건수가 달라질 수 있어서다.", "",
          "| 항목 | A | B | n |", "|---|---|---|---|"]
    for item in ITEMS + ("total",):
        ma, na = get("abs_mean", app="A", item=item)
        sa, _ = get("abs_sd", app="A", item=item)
        mb, _ = get("abs_mean", app="B", item=item)
        sb, _ = get("abs_sd", app="B", item=item)
        L.append(f"| {item} | {fmt(ma)} ± {fmt(sa)} | {fmt(mb)} ± {fmt(sb)} | {na} |")
    L += ["", "판정 모델별 합계 평균:", "", "| 판정 모델 | A | B |", "|---|---|---|"]
    for j in judges:
        L.append(f"| {j} | {fmt(get('abs_mean', j, 'A', 'total')[0])} | {fmt(get('abs_mean', j, 'B', 'total')[0])} |")

    if submodels:
        L += ["", "한 판정 모델 안의 세부 모델별 합계 평균(ALL에는 판정 모델 단위로만 들어간다):", "",
              "| 세부 모델 | A | B | n(A) |", "|---|---|---|---|"]
        for g in submodels:
            L.append(f"| {g} | {fmt(get('abs_mean', g, 'A', 'total')[0])} | {fmt(get('abs_mean', g, 'B', 'total')[0])} | "
                     f"{get('abs_mean', g, 'A', 'total')[1]} |")
    L += ["", "## 2. 쌍비교 선택 비율", "", "| 항목 | A | B | 동률 | n |", "|---|---|---|---|---|"]
    for item in PAIR_ITEMS:
        a, n = get("pw_rate", app="A", item=item)
        L.append(f"| {item} | {fmt(a, True)} | {fmt(get('pw_rate', app='B', item=item)[0], True)} | "
                 f"{fmt(get('pw_rate', app='tie', item=item)[0], True)} | {n} |")

    L += ["", "## 3. 위치 편향", "", "| 항목 | 순서 교체 시 선택 변경 | 먼저 보인 쪽 선택(동률 제외) |", "|---|---|---|"]
    for item in PAIR_ITEMS:
        L.append(f"| {item} | {fmt(get('position_flip_rate', item=item)[0], True)} | "
                 f"{fmt(get('first_position_pick_rate', item=item)[0], True)} |")

    L += ["", "## 4. 판정 모델 간 일치도 (Krippendorff's alpha)", "", "| 항목 | 절대(interval) | 쌍비교(nominal) |", "|---|---|---|"]
    for item in PAIR_ITEMS:
        L.append(f"| {item} | {fmt(get('alpha_abs_interval', item=item)[0]) if item != 'overall' else '—'} | "
                 f"{fmt(get('alpha_pw_nominal', item=item)[0])} |")
    L.append("\n판정 모델이 3개, 회차가 3번이라 alpha의 표본이 작다. 값의 크기보다 방향만 참고한다.")

    L += ["", "## 5. 자기 선호 점검 (Claude 판정 − 나머지 판정)", "",
          "두 앱 모두 Claude로 만들었으므로 이 차이는 \"Claude가 자기 앱을 편든다\"가 아니라 \"Claude 판정이 다른 판정과 어떻게 다른가\"만 보여 준다.", "",
          "| 항목 | A | B |", "|---|---|---|"]
    for item in ITEMS:
        L.append(f"| {item} | {fmt(get('self_pref_abs_diff', CLAUDE, 'A', item)[0])} | {fmt(get('self_pref_abs_diff', CLAUDE, 'B', item)[0])} |")
    v, n = get("self_pref_pw_A_rate_diff", CLAUDE, "A", "overall")
    L.append(f"\n종합에서 A를 고른 비율 차(Claude − 나머지): {fmt(v, True)} (n={n})")

    L += ["", "## 6. 객관 지표", ""]
    obj = [r for r in rows if r["metric"] == "objective_count"]
    if obj:
        L += ["| 앱 | 판정 | 건수 / 전체 |", "|---|---|---|"] + [f"| {r['app']} | {r['item']} | {r['value']} / {r['n']} |" for r in obj]
        L.append("\n\"기능없음\"은 점수에 넣지 않는다.")
    else:
        L.append("아직 없음(`objective/results.csv`).")

    L += ["", "## 7. 길이 편향 관찰 (정성)", "",
          "<!-- 사람이 채운다: 기능 수(inventory.md)가 많은 쪽이 purpose_fit과 무관하게 이기는지, 근거 문장(rationale)이 기능 개수를 근거로 드는지 -->", "",
          "## 8. 한계", "",
          "- 조건마다 결과물이 1개다. skill 사용 여부의 효과를 추정할 수 없다.",
          "- 교란변수: 기능 범위, 투입 시간(약 20시간 vs 5시간), 제작 순서(A 먼저), 서비스 목적이 다르다.",
          "- LLM 판정의 선호는 사람의 선호와 다를 수 있다(Phase 7 설문은 선택).",
          "- temperature는 API 판정(Gemini, OpenAI API를 쓴 경우)만 고정했다. Claude 하위 에이전트와 수동 판정(ChatGPT 앱·Codex)은 정할 수 없다.",
          "- Claude 하위 에이전트와 수동 판정은 각 도구의 시스템 프롬프트가 붙는다. 하위 에이전트가 패킷 밖의 파일을 읽지 않았다고 완전히 보장할 수 없다.",
          "- 두 앱의 LLM과 Gemini 판정이 같은 계열이다. Gemini 판정 12건은 gemini-3.5-flash-lite 6건(1회차 전체 + 3회차 절대 평가)과 gemini-3.5-flash 6건(2회차 전체 + 3회차 쌍비교)을 섞었다(무료 한도 때문). 두 세부 모델은 절대/쌍비교 비중이 4:2, 2:4로 다르다. 세부 모델별 값은 1절 표에 따로 있다.",
          "- Claude 판정은 두 앱을 만든 모델(Opus 5.5)과 분리하려고 Sonnet(claude-sonnet-5-5) 하위 에이전트로 했다. 같은 Claude 계열이라 계열 편향은 남고, 판정 정교함은 Opus보다 낮을 수 있다.",
          "- OpenAI 판정은 Codex 세션 수동 실행이다. 모델 이름은 화면 표기이고 temperature·시스템 프롬프트를 통제할 수 없다.",
          "- 표본이 작다: 판정 모델 3곳 × 3회차 × 4건 = 36건.", ""]
    Path(out_path).write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default=EVAL / "judges" / "raw")
    ap.add_argument("--mapping", default=EVAL / "packets" / "mapping.secret.json")
    ap.add_argument("--objective", default=EVAL / "objective" / "results.csv")
    ap.add_argument("--out-dir", default=EVAL / "analysis")
    a = ap.parse_args()
    mapping = {k: v for k, v in json.loads(Path(a.mapping).read_text(encoding="utf-8")).items() if k in ("X", "Y")}
    recs = load(a.raw_dir)
    rows = compute(recs, mapping) + objective_rows(a.objective)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(rows, out / "summary.csv")
    report(out / "summary.csv", out / "report.md")
    print(f"레코드 {len(recs)}건 → {out / 'summary.csv'}, {out / 'report.md'}")


if __name__ == "__main__":
    main()
