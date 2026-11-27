// 한 턴 복기 화면. 시안(docs/designs/prototype/review-tab.html, 2026-10-23 디자인 반영판)의 화면 코드를 그대로 옮기고
// 예시 데이터 자리를 실제 API(server/app.py)로 바꿨다. 계산·판정은 서버가 한다(agent.md 1.2).
"use strict";

const U7 = "혹시 상대방이 신속/마하펀치와 같은 선공기를 사용했나요? 그렇다면 우선도에 따라 선공 여부가 달라질 수 있습니다.";

// ---- 상태 ----
// ask: 서버가 "값은 있지만 다시 봐야 한다"고 한 칸. 화면 칩 이름으로 바꿔 둔다(move_key → move)
const st = { me: null, opp: null, move: null, actor: "opp", ask: [], notes: [], extractionId: null, controller: null, quota: null, reviewId: null, lastArgs: null };
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const att = () => st.actor === "me" ? st.me : st.opp;
const def = () => st.actor === "me" ? st.opp : st.me;
const announce = t => { $("live").textContent = ""; setTimeout(() => $("live").textContent = t, 30); };
function josa(word, withBatchim, without) {
  const c = word.charCodeAt(word.length - 1);
  if (c < 0xac00 || c > 0xd7a3) return without;
  return (c - 0xac00) % 28 ? withBatchim : without;
}
const who = p => p === st.opp ? "상대 " + p.name_ko : "내 " + p.name_ko;
const actualVal = () => (document.querySelector("input[name=actual]:checked") || {}).value;
const bandVal = () => (document.querySelector("input[name=hp_band]:checked") || {}).value;
const setActual = v => { const r = document.querySelector(`input[name=actual][value="${v}"]`); if (r) { r.checked = true; r.dispatchEvent(new Event("change")); } };
const session = (() => { try { let s = sessionStorage.getItem("sid"); if (!s) { s = Math.random().toString(36).slice(2); sessionStorage.setItem("sid", s); } return s; } catch { return null; } })();
// 화면의 HP 칸 값과 서버 값: 화면 "-25" ↔ 서버 "<25"
const BAND_TO_SERVER = { "-25": "<25" }, BAND_FROM_SERVER = { "<25": "-25" };
const ASK_FROM_SERVER = { move_key: "move", my_form_key: "me", opp_form_key: "opp" };

// ---- 서버 호출 ----
class ApiError extends Error { constructor(status, code, message) { super(message); this.status = status; this.code = code; } }
async function api(path, body, signal) {
  const opts = body === undefined ? { signal } : { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body), signal };
  const r = await fetch(path, { credentials: "same-origin", ...opts });
  if (r.ok) return r;
  let detail = {};
  try { detail = (await r.json()).detail || {}; } catch { /* 본문 없음 */ }
  if (r.status === 403) showGate();  // 어느 API에서 와도 초대 안내 전체 화면(E5 ③)
  // 422는 code가 없다(FastAPI 기본 형식). HTTP 상태로 고른다(E5 ①)
  const code = r.status === 422 ? "http_422" : (detail && detail.code) || String(r.status);
  throw new ApiError(r.status, code, (detail && detail.message) || "");
}
const getJSON = async path => (await api(path)).json();
function showGate() {
  ["askView", "resultView"].forEach(id => $(id).classList.add("hidden"));
  $("gateView").classList.remove("hidden");
}

// ---- combobox: 보이는 label + ↑↓ Enter Esc (DR13), 폰에서는 전체 화면 시트 (DR12). source는 Promise를 돌려준다 ----
function combo(rootId, inputId, label, source, onPick, needQuery = false) {  // needQuery: 글자를 쳤을 때만 목록을 연다(디자인 W2)
  const root = $(rootId), listId = inputId + "List";
  root.innerHTML = `<div class="sheet-head"><b>${label}</b><button type="button" class="link" data-close>닫기</button></div>
    <input type="text" id="${inputId}" role="combobox" aria-expanded="false" aria-controls="${listId}" aria-autocomplete="list" autocomplete="off" placeholder="한글 이름으로 찾기">
    <ul id="${listId}" role="listbox" class="hidden"></ul>`;
  const input = $(inputId), list = $(listId);
  let items = [], active = -1, seq = 0, timer;
  const close = () => { list.classList.add("hidden"); root.classList.remove("open"); input.setAttribute("aria-expanded", "false"); input.removeAttribute("aria-activedescendant"); };
  const render = async () => {
    const mine = ++seq;
    list.innerHTML = `<li class="empty">불러오는 중…</li>`; items = [];
    let r;
    try { r = await source(input.value.trim()); } catch { r = { state: "error" }; }
    if (mine !== seq) return;  // 늦게 온 응답은 버린다
    if (r.state === "error") { list.innerHTML = `<li class="empty">목록을 못 불러왔어요</li>`; return; }
    items = r.items; active = items.length ? 0 : -1;
    list.innerHTML = items.length
      ? items.map((it, i) => `<li role="option" id="${listId}-${i}" aria-selected="${i === active}">${esc(it.label)} <span class="t">${esc(it.sub || "")}</span></li>`).join("")
      : `<li class="empty">'${esc(input.value)}'와 맞는 항목이 없어요. 한글 이름으로 찾아보세요${r.fallback ? ` · <button type="button" class="link" data-all>전체 기술에서 찾기</button>` : ""}</li>`;
    if (active >= 0) input.setAttribute("aria-activedescendant", `${listId}-0`);
  };
  const open = () => { if (input.disabled) return; if (needQuery && !input.value.trim()) { close(); return; } render(); list.classList.remove("hidden"); input.setAttribute("aria-expanded", "true"); if (matchMedia("(max-width: 599px)").matches) root.classList.add("open"); };
  const pick = i => { const it = items[i]; if (!it) return; input.value = it.label; close(); onPick(it.value); };
  const move = d => {
    if (!items.length) return;
    active = (active + d + items.length) % items.length;
    [...list.children].forEach((li, i) => li.setAttribute("aria-selected", i === active));
    input.setAttribute("aria-activedescendant", `${listId}-${active}`);
    list.children[active].scrollIntoView({ block: "nearest" });
  };
  input.addEventListener("focus", open);
  input.addEventListener("input", () => { onPick(null); clearTimeout(timer); timer = setTimeout(open, 150); });
  input.addEventListener("keydown", e => {
    if (e.key === "ArrowDown") { e.preventDefault(); list.classList.contains("hidden") ? open() : move(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
    else if (e.key === "Enter" && !list.classList.contains("hidden")) { e.preventDefault(); pick(active); }
    else if (e.key === "Escape") close();
  });
  list.addEventListener("mousedown", e => {
    // 버튼만 본다: 전체 찾기 상태에선 묶음(root)에도 data-all이 붙어 있어 "[data-all]"이면 옵션 클릭까지 잡힌다
    if (e.target.closest("button[data-all]")) { e.preventDefault(); root.dataset.all = "1"; render(); return; }
    const li = e.target.closest("[role=option]"); if (li) { e.preventDefault(); pick([...list.children].indexOf(li)); }
  });
  root.querySelector("[data-close]").addEventListener("click", close);
  input.addEventListener("blur", () => setTimeout(() => { if (!root.contains(document.activeElement)) close(); }, 120));
  return { input, set(v) { input.value = v; }, close };
}
const pokeSource = async q => q
  ? { items: (await getJSON("/api/pokemon?q=" + encodeURIComponent(q))).map(p => ({ value: p, label: p.name_ko, sub: p.types.join("·") })) }
  : { items: [] };
const meC = combo("meCombo", "meInput", "내 포켓몬", pokeSource, p => { st.me = p; refresh(); }, true);
const oppC = combo("oppCombo", "oppInput", "상대 포켓몬", pokeSource, p => { st.opp = p; refresh(); }, true);
// GET /api/moves?form_key= (DR14): 공격 측이 배우는 물리·특수 기술. 「전체 기술에서 찾기」는 ?q=
const moveC = combo("moveCombo", "moveInput", "기술", async q => {
  const a = att(); if (!a) return { items: [] };
  const all = $("moveCombo").dataset.all;
  if (all && !q) return { items: [] };
  const url = all ? "/api/moves?q=" + encodeURIComponent(q) : `/api/moves?form_key=${encodeURIComponent(a.form_key)}&q=${encodeURIComponent(q)}`;
  return { fallback: !all, items: (await getJSON(url)).map(m => ({ value: m, label: m.name_ko, sub: `${m.type} · ${m.category} · 위력 ${m.power ?? "-"}` })) };
}, m => { st.move = m; refreshConfirm(); });
function clearMove() { st.move = null; moveC.set(""); delete $("moveCombo").dataset.all; }

function refresh() {
  const meName = st.me ? st.me.name_ko : "내 포켓몬", oppName = st.opp ? "상대 " + st.opp.name_ko : "상대";
  const defName = st.actor === "me" ? oppName : meName;
  $("meRole").innerHTML = `<b>${st.actor === "me" ? "공격" : "방어"}</b>`;
  $("oppRole").innerHTML = `<b>${st.actor === "opp" ? "공격" : "방어"}</b>`;
  $("swapBtn").setAttribute("aria-label", `공격 측 바꾸기, 지금: ${st.actor === "opp" ? "상대가" : "내가"} 공격`);
  document.querySelector("[data-t=ko]").textContent = `${defName}${josa(defName, "이", "가")} 한 방에 쓰러졌어요`;
  document.querySelector("[data-t=survived]").textContent = `${defName}${josa(defName, "이", "가")} 버텼어요`;
  document.querySelector("[data-t=outsped]").textContent = `${oppName}${josa(oppName, "이", "가")} 먼저 움직였어요`;
  document.querySelector("[data-t=slower]").textContent = "내가 먼저 움직였어요";
  document.querySelector("[data-t=mySpLabel]").textContent = `${meName} SP`;
  document.querySelector("[data-t=oppSpLabel]").textContent = `${oppName} SP`;
  moveC.input.disabled = !att();
  $("moveHint").classList.toggle("hidden", !!att());
  refreshConfirm();
}
// DR22: 결과 종류에 맞는 묶음만 보이고, 체크된 칸은 언제나 보인다
function refreshFlags() {
  const v = actualVal(), order = v === "outsped" || v === "slower";
  const visible = { status: !order, field: !order, order };
  document.querySelectorAll("[data-flag]").forEach(l => {
    const g = l.closest("[data-group]").dataset.group, checked = l.querySelector("input").checked;
    l.classList.toggle("hidden", !(visible[g] || checked || (order && l.dataset.flag === "stat_stage")));
  });
  document.querySelectorAll("[data-group]").forEach(g => g.classList.toggle("hidden", ![...g.querySelectorAll("[data-flag]")].some(l => !l.classList.contains("hidden"))));
}
$("swapBtn").addEventListener("click", () => { st.actor = st.actor === "opp" ? "me" : "opp"; clearMove(); refresh(); });
// 확인 단계의 공격 측 바꾸기(E6): 기술은 그대로 둔다. 서버가 읽은 기술은 맞고 "누가 썼는지"만 불확실한 경우라서
$("confirmSwap").addEventListener("click", () => {
  st.ask = st.ask.filter(f => f !== "actor"); st.actor = st.actor === "opp" ? "me" : "opp"; refresh();
  announce(`공격 측을 바꿨어요. 지금: ${st.actor === "opp" ? "상대가" : "내가"} 공격`);
});
document.querySelectorAll("input[name=actual]").forEach(r => r.addEventListener("change", () => {
  $("hpChips").classList.toggle("hidden", actualVal() !== "survived"); refreshFlags(); refreshConfirm();
}));
document.querySelectorAll("input[name=flags], input[name=hp_band]").forEach(c => c.addEventListener("change", () => { refreshFlags(); refreshConfirm(); }));

// ---- SP 표기: 화면은 형식만 미리 알려 주고, 판정은 서버(check_sp)가 한다 ----
const LETTER = { H: "hp", A: "atk", B: "def", C: "spa", D: "spd", S: "spe" };
const SP_LETTER = Object.fromEntries(Object.entries(LETTER).map(([k, v]) => [v, k]));
function spCheck(s) {
  if (!s.trim()) return null;
  const sp = {};
  for (const p of s.trim().toUpperCase().split(/[\s,]+/)) {
    const m = /^([HABCDS])(\d{1,2})$/.exec(p);
    if (!m) return { err: `'${p}'를 읽지 못했어요. 예: A20 S32` };
    if (+m[2] > 32) return { err: `${m[1]}${m[2]}: 스탯당 최대 32예요` };
    sp[LETTER[m[1]]] = +m[2];
  }
  const sum = Object.values(sp).reduce((a, b) => a + b, 0);
  return sum > 66 ? { err: `합계 ${sum}: 66 이하로 적어 주세요` } : { sp };
}
const spText = sp => Object.entries(sp || {}).map(([k, v]) => SP_LETTER[k] + v).join(" ");
function fieldErr(input, errEl, msg) { input.setAttribute("aria-invalid", msg ? "true" : "false"); errEl.textContent = msg || ""; errEl.classList.toggle("hidden", !msg); }

// ---- 문장 읽기 결과 → 칸 채우기 (C1-1) ----
function applyExtraction(x) {
  const f = x.fields, L = x.labels || {};
  st.me = L.my || null; st.opp = L.opp || null; st.actor = f.actor || "opp";
  meC.set(st.me ? st.me.name_ko : ""); oppC.set(st.opp ? st.opp.name_ko : "");
  st.move = L.move || null; moveC.set(st.move ? st.move.name_ko : "");
  document.querySelectorAll("input[name=actual], input[name=hp_band]").forEach(r => r.checked = false);
  if (f.actual) {
    setActual(f.actual.kind);
    const b = f.actual.hp_band && document.querySelector(`input[name=hp_band][value="${BAND_FROM_SERVER[f.actual.hp_band] || f.actual.hp_band}"]`);
    if (b) b.checked = true;
  }
  document.querySelectorAll("input[name=flags]").forEach(c => c.checked = (f.flags || []).includes(c.value));
  $("mySp").value = spText(f.my_build && f.my_build.sp); $("oppSp").value = spText(f.opp_sp);
  if (f.my_build && f.my_build.nature) $("myNature").value = f.my_build.nature;
  $("hpChips").classList.toggle("hidden", actualVal() !== "survived");
  st.ask = (x.ask || []).map(a => ASK_FROM_SERVER[a] || a); st.notes = x.notes || []; st.extractionId = x.extraction_id;
  refreshFlags(); refresh();
}

// ---- 확인 단계 (C1-1) ----
const KIND_TXT = { ko: "한 방에 쓰러짐", survived: "버팀", outsped: "상대가 먼저 움직임", slower: "내가 먼저 움직임" };
const FLAG_TXT = { crit: "급소", burn: "화상", stat_stage: "능력 변화", tera: "테라스탈", weather: "날씨", terrain: "필드", reflect: "리플렉터", light_screen: "빛의장막", trick_room: "트릭룸", tailwind: "순풍" };
function refreshConfirm() {
  if ($("confirmView").classList.contains("hidden")) return;
  const a = att(), d = def(), k = actualVal(), band = bandVal();
  // 빈 칸 = missing(오류 점선, 버튼 막음). 값은 있지만 다시 봐야 하는 칸(서버 ask) = check(경고 실선 + "· 확인", 버튼은 막지 않음)
  const chip = (txt, field, ok) => {
    const check = ok && (st.ask.includes(field) || (st.ask.includes("actor") && field === st.actor));  // actor 확인은 공격한 포켓몬 칩에
    return `<button type="button" class="chip ${ok ? "" : "missing"}${check ? " check" : ""}" data-edit="${field}">${esc(txt)}${check ? `<span class="chip-tag"> · 확인</span>` : ""}</button>`;
  };
  const seg = (sep, html) => `<span class="seg"><span class="arrow" aria-hidden="true">${sep}</span>${html}</span>`;
  $("sentence").innerHTML = [
    chip(d ? who(d) : "맞은 포켓몬", st.actor === "opp" ? "me" : "opp", !!d),
    seg("←", chip(st.move ? st.move.name_ko : "기술", "move", !!st.move)),
    seg("←", chip(a ? who(a) : "공격한 포켓몬", st.actor === "opp" ? "opp" : "me", !!a)),
    seg("·", chip(k ? KIND_TXT[k] + (k === "survived" ? (band ? ` (${band.replace("-25", "25% 미만").replace("75+", "75% 이상")})` : " · 남은 HP?") : "") : "결과", "actual", !!k && (k !== "survived" || !!band))),
  ].join("");
  const flags = [...document.querySelectorAll("input[name=flags]:checked")].map(c => c.value);
  $("flagChips").innerHTML = flags.length ? `<span class="small muted">특수 상황:</span>` + flags.map(f => `<button type="button" class="chip flag" data-edit="flags">${FLAG_TXT[f]} · 참고용</button>`).join("") : "";
  const why = !d ? "맞은 포켓몬을 골라 주세요" : !a ? "공격한 포켓몬을 골라 주세요" : !st.move ? "기술을 골라 주세요"
    : !k ? "실제 결과를 골라 주세요" : k === "survived" && !band ? "남은 HP 구간을 골라 주세요" : "";
  $("goBtn").disabled = !!why;
  $("goReason").textContent = why;
  $("extractNotes").innerHTML = st.notes.map(n => `<li>${esc(n)}</li>`).join("");
  $("swapRow").classList.toggle("hidden", !st.ask.includes("actor"));
  $("sourceQuote").textContent = $("nlInput").value.trim() ? `원문: "${$("nlInput").value.trim()}"` : "";
}
function showConfirm() {
  $("ruleView").classList.add("hidden"); $("confirmView").classList.remove("hidden");
  refreshConfirm(); $("confirmTitle").focus?.(); announce("이렇게 이해했어요. 확인해 주세요");
}
document.addEventListener("click", e => {
  const ch = e.target.closest("[data-edit]");
  if (!ch) return;
  $("moreBox").open = true;
  const f = ch.dataset.edit;
  const seen = st.ask.filter(x => x !== f && !(x === "actor" && f === st.actor));  // 눌러서 본 칸은 "확인" 표시를 지운다
  if (seen.length !== st.ask.length) { st.ask = seen; refreshConfirm(); }
  const target = f === "me" ? meC.input : f === "opp" ? oppC.input : f === "move" ? moveC.input : f === "flags" ? document.querySelector("[data-flag]:not(.hidden) input") : document.querySelector("input[name=actual]");
  target && target.focus();
});
$("moreBtn").addEventListener("click", () => { $("moreBox").open = true; meC.input.focus(); });

// 화면 문구는 서버 code로 고른다. 서버 message는 이 표에 없는 code일 때만 그대로 쓴다
const MSG = {
  empty_input: "무슨 일이 있었는지 한 줄 적어 주세요",
  llm_unavailable: "지금은 문장을 읽을 수 없어요. 아래 칸을 직접 채워 주세요",
  not_understood: "문장을 이해하지 못했어요. 아래 칸을 직접 채워 주세요", // empty · broken_json · refusal
  token_limit: "오늘 복기 횟수를 다 썼어요. 내일 다시 이용해 주세요. 입력한 내용은 그대로 있어요",
  token_limit_extract: "오늘 이용 횟수를 다 썼어요. 내일 다시 이용해 주세요. 입력한 내용은 그대로 있어요",  // 문장 읽기 한도는 따로라 "복기 횟수"가 아니다(E5 ②)
  feedback_failed: "기록하지 못했어요. 결과는 그대로 볼 수 있어요",
  server_limit: "오늘은 서버 사용량이 다 차서 복기할 수 없어요. 내 횟수와는 관계없어요. 내일 다시 이용해 주세요",
  http_422: "입력한 조건을 처리하지 못했어요. 조건을 고쳐 주세요",
  bad_input: "입력한 조건으로는 계산할 수 없어요. 조건을 고쳐 주세요",
  internal: "계산 중 문제가 생겼어요. 잠시 뒤 다시 시도해 주세요",
  disconnect: "연결이 끊겼어요. 입력한 조건은 그대로 있어요",
};
const msgFor = (code, fallback) => MSG[code] || fallback || MSG.internal;
function status(msg, tone) { $("nlStatus").textContent = msg; $("nlStatus").className = "hint" + (tone ? " " + tone : ""); if (msg) announce(msg); }
function quotaLine() { const n = st.quota && st.quota.review; $("quotaLine").textContent = n != null && n <= 5 && n > 0 ? `오늘 남은 복기 ${n}번` : ""; }  // 5번 이하일 때만
async function refreshQuota() {
  try { st.quota = (await getJSON("/api/quota")).remaining; } catch { /* 403이면 api()가 초대 안내를 띄운다 */ }
  quotaLine();
}

$("askForm").addEventListener("submit", async e => {
  e.preventDefault();
  const text = $("nlInput").value.trim();
  if (!text && !$("moreBox").open) { status(MSG.empty_input, "danger"); $("nlInput").focus(); return; }
  if (!text) { st.ask = []; st.notes = []; st.extractionId = null; showConfirm(); return; }
  status("문장을 읽는 중…"); $("askBtn").disabled = true;
  try {
    const x = await (await api("/api/feature/review/extract", { text })).json();
    status("");
    if (x.type === "rule") return showRule();
    if (x.type === "fail") return extractFailed(x.reason === "llm_unavailable" ? MSG.llm_unavailable : x.reason === "empty_input" ? MSG.empty_input : MSG.not_understood);
    applyExtraction(x); showConfirm();
  } catch (err) {
    if (err.status === 403) return;
    if (err.status === 429) return status(msgFor(err.code === "token_limit" ? "token_limit_extract" : err.code, err.message), "warn");
    extractFailed(err.status === 422 ? MSG.http_422 : MSG.llm_unavailable);
  } finally { $("askBtn").disabled = false; }
});
function extractFailed(msg) {
  $("confirmView").classList.add("hidden"); $("ruleView").classList.add("hidden");
  status(msg, "warn"); $("moreBox").open = true; meC.input.focus();
}
$("goBtn").addEventListener("click", () => {
  const my = spCheck($("mySp").value), op = spCheck($("oppSp").value);
  fieldErr($("mySp"), $("mySpErr"), my && my.err); fieldErr($("oppSp"), $("oppSpErr"), op && op.err);
  if ((my && my.err) || (op && op.err)) { $("moreBox").open = true; (my && my.err ? $("mySp") : $("oppSp")).focus(); return; }
  run(my && my.sp, op && op.sp);
});
$("toReview").addEventListener("click", () => { $("moreBox").open = true; showConfirm(); });

// ---- 규칙 질문 (DR21, /api/chat 없음) ----
function showRule() {
  $("confirmView").classList.add("hidden"); $("ruleView").classList.remove("hidden");
  announce("규칙 질문으로 이해했어요. 답변은 준비 중이에요");
}

// ---- 복기 실행 (SSE) ----
function requestBody(mySp, oppSp) {
  const k = actualVal(), band = bandVal(), body = {
    session_id: session, extraction_id: st.extractionId, my_form_key: st.me.form_key, opp_form_key: st.opp.form_key,
    actor: st.actor, move_key: st.move.move_key, actual: { kind: k, ...(k === "survived" ? { hp_band: BAND_TO_SERVER[band] || band } : {}) },
    flags: [...document.querySelectorAll("input[name=flags]:checked")].map(c => c.value),
  };
  const build = {};
  if (mySp) build.sp = mySp;
  if ($("myNature").value) build.nature = $("myNature").value;
  if ($("myItem").value) build.item = $("myItem").value === "none" ? "" : $("myItem").value;
  if (Object.keys(build).length) body.my_build = build;
  if (oppSp) body.opp_sp = oppSp;
  if ($("preHp").value) body.pre_hit_hp = +$("preHp").value;
  return body;
}
async function* sse(response) {
  const reader = response.body.getReader(), dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, i); buf = buf.slice(i + 2);
      const ev = /^event: (.*)$/m.exec(block), data = /^data: (.*)$/m.exec(block);
      if (ev && data) yield { event: ev[1], data: JSON.parse(data[1]) };
    }
  }
}
function turnText() {
  const k = actualVal(), band = bandVal();
  const hp = k === "survived" && band ? ` (${band.replace("-25", "25% 미만").replace("75+", "75% 이상").replace("50-75", "50–75%").replace("25-50", "25–50%")})` : "";
  return `${who(def())} ← ${st.move.name_ko} ← ${who(att())} · ${KIND_TXT[k]}${hp}`;
}
function showResultFrame(turn) {
  $("askView").classList.add("hidden"); $("resultView").classList.remove("hidden");
  $("turnText").textContent = turn;
}
// 재제출하면 이전 스트림을 끊어 늦은 응답이 새 결과를 덮지 않게 한다(DR7). 서버는 status(computing) 한 번 뒤 answer를 보낸다
async function run(mySp, oppSp) {
  if (st.controller) st.controller.abort();
  const ctl = st.controller = new AbortController();
  const body = requestBody(mySp, oppSp);
  st.lastArgs = [mySp, oppSp];
  showResultFrame(turnText());
  $("resultBody").innerHTML = `<p class="progress" role="status">계산하는 중…</p>`;
  announce("계산하는 중");
  try {
    const r = await api("/api/feature/review", body, ctl.signal);
    let got = false;
    for await (const { event, data } of sse(r)) {
      if (ctl !== st.controller) return;
      if (event === "answer") { got = true; renderAnswer({ ...data, kind: body.actual.kind }); }
      if (event === "error") { got = true; renderError(data.code); }
    }
    if (!got && ctl === st.controller) renderError("disconnect");
  } catch (err) {
    if (err.name === "AbortError" || err.status === 403) return;
    renderError(err.status === 429 || err.status === 422 ? err.code : err instanceof ApiError ? "internal" : "disconnect");
  } finally { refreshQuota(); }
}
function renderError(code) {
  const limit = code === "token_limit" || code === "server_limit", fix = code === "bad_input" || code === "http_422";
  // 오류 문구가 이 화면의 결론이라 h1(제목 크기 22px)로 둔다
  $("resultBody").innerHTML = `<h1 class="notice ${limit ? "warn" : "danger"}" role="alert">${esc(msgFor(code))}</h1>`
    + (limit ? "" : `<div class="row-actions"><button type="button" class="primary" data-act="${fix ? "edit" : "retry"}">${fix ? "조건 고치기" : "다시 복기"}</button></div>`);
  announce(msgFor(code));
}

const BASIS_NAME = { pokedb: "실제 랭크배틀 기준", smogon: "Showdown 시뮬레이터 기준" };
// 난수 띠(DESIGN.md): 16칸 중 k칸 채움, 같은 글자 표기를 옆에 항상 둔다
const strip = k => `<span class="rolls" role="img" aria-label="16번 중 ${k}번 실제 결과와 같음">${Array.from({ length: 16 }, (_, i) => `<i class="${i < k ? "on" : ""}" style="--i:${i}"></i>`).join("")}</span>`;
// 통계표에는 청록을 칠하지 않는다(청록은 결론이 가리키는 계산표 줄에만, 디자인 W3). 도구로 구분 불가면 순위 없이 나열한다
function basisBlock(name, b, primary, lead = "") {
  const flat = b.undetermined;
  const rows = b.causes.map(c => `<li>${flat ? "" : `<span class="rank">${c.rank}</span>`}<span class="item">${esc(c.label)}</span>${c.rolls_k != null ? `<span class="rollcell">${strip(c.rolls_k)}<span class="rolltxt">16번 중 ${c.rolls_k}번</span></span>` : ""}<span class="spread">${esc(c.conditions[0])}${c.conditions.length > 1 ? ` 외 ${c.conditions.length - 1}개` : ""}</span></li>`).join("");
  return `<section class="basis${primary ? "" : " sub"}" aria-labelledby="basis-${name}">
    <h3 class="basis-head" id="basis-${name}">${BASIS_NAME[name]}${primary ? "" : " (참고)"}</h3>
    <p class="basis-src">${esc(b.source.label)}</p>
    ${b.source.note ? `<p class="basis-src">${esc(b.source.note)} · <a href="${esc(b.source.url)}" target="_blank" rel="noopener noreferrer">출처</a></p>` : ""}
    ${lead}
    ${b.zero_match ? `<p class="causes-cap">이 기준에서는 결과와 맞는 후보가 없어요</p>`
      : `<p class="causes-cap">${flat ? "상대 도구로는 구분하기 어려워요. 아래 후보 모두 이 결과와 맞아요" : "이 결과와 맞는 상대 도구 후보 · 가능성 높은 순"}</p><ol class="causes${flat ? " flat" : ""}">${rows}</ol>`}
    ${Math.round(b.excluded_share * 100) > 0 ? `<p class="excluded">상대 도구 중 채용률 ${Math.round(b.excluded_share * 100)}%는 계산할 수 없어 빼고 비교했어요</p>` : ""}
  </section>`;
}
// 계산표(P0): 상대 빌드 한 줄 = 데미지 범위(굵게) + 난수 띠 + 계산기식 결과, 아래 작은 글씨로 통계·같은 결과 도구.
// 챔피언스에 없는 도구 줄은 흐리지 않고 아래에 따로 묶는다(그 줄이 결과를 설명할 수 있어서)
const pct = n => `${+n.toFixed(1)}%`;
function calcResult(r, kind) {
  if (r.speed) { const { opp, me } = r.speed; return [`상대 ${opp} · 나 ${me}`, opp > me ? "상대가 먼저" : opp < me ? "내가 먼저" : "동속(먼저 움직이는 쪽은 무작위)"]; }
  const dmg = `${r.damage[0]}~${r.damage[1]}%`;
  if (kind === "survived") return [dmg, `16번 중 ${r.k}번 이 HP로 버팀 (${pct(r.pct)})`];
  return [dmg, r.k === 16 ? "확정 1타" : r.k === 0 ? "1타 불가" : `난수 1타 · 16번 중 ${r.k}번 (${pct(r.pct)})`];
}
function calcRow(r, kind, lead) {
  const [main, res] = calcResult(r, kind);
  const meta = [...r.usage, ...(r.same_items.length ? [`같은 결과: ${r.same_items.join("·")}`] : [])];
  return `<li${lead && r.k != null ? ' class="lead"' : ""}><p class="calc-label">${esc(r.label)}</p>
    <p class="calc-line"><span class="calc-main">${esc(main)}</span>${r.k != null ? strip(r.k) : ""}<span class="calc-res">${esc(res)}</span></p>
    ${meta.length ? `<p class="calc-meta">${esc(meta.join(" · "))}</p>` : ""}</li>`;
}
function calcBlock(c, kind) {
  if (!c) return "";
  const rows = c.rows.length ? c.rows : c.near, inC = rows.filter(r => r.in_champions), outC = rows.filter(r => !r.in_champions);
  const leadRow = c.rows.length && c.headline_row != null ? c.rows[c.headline_row] : null;  // 결론이 가리키는 줄(서버 headline_row). near·스피드는 청록 없음
  const row = r => calcRow(r, kind, r === leadRow);
  return `<section class="calc" aria-labelledby="calcTitle">
    <h2 class="section-title" id="calcTitle">계산 결과 · 상대 빌드별</h2>
    <p class="basis-src">내 빌드 ${esc(c.my_build)} · ${esc(c.assumed)}</p>
    ${c.rows.length ? "" : `<p class="calc-empty">이 결과가 나오는 상대 빌드가 없어요. 가장 가까운 빌드를 보여 드려요</p>`}
    ${inC.length ? `<ol class="calc-rows">${inC.slice(0, 3).map(row).join("")}</ol>` : ""}
    ${inC.length > 3 ? `<details class="fold calc-fold"><summary>빌드 ${inC.length - 3}개 더 보기</summary><ol class="calc-rows">${inC.slice(3).map(row).join("")}</ol></details>` : ""}
    ${outC.length ? `<h3 class="calc-group">챔피언스에 없는 도구 <span class="badge">참고</span></h3><p class="basis-src">지금 챔피언스에서는 쓸 수 없는 도구예요. 상대 빌드를 잘못 짐작했을 수 있다는 신호로 보세요</p><ol class="calc-rows">${outC.map(row).join("")}</ol>` : ""}
    ${c.more ? `<p class="basis-src calc-more">결과가 비슷한 빌드 ${c.more}개는 생략했어요</p>` : ""}
  </section>`;
}
function renderAnswer(a) {
  st.reviewId = a.review_id;
  const B = a.bases, names = ["pokedb", "smogon"].filter(n => B[n]);
  const hasRolls = names.some(n => B[n].causes.some(c => c.rolls_k != null));
  // 좌우 배열은 differs일 때 화면이 붙이는 .bases.two로 판단한다(E8: :has() 대신)
  const bases = !names.length ? ""
    : a.differs ? `<div class="bases two">${basisBlock("pokedb", B.pokedb, true)}${B.smogon ? basisBlock("smogon", B.smogon, false, `<p class="diff-note">이 기준에서는 결과가 달라요. 데이터를 모은 곳과 내 빌드 가정이 달라서일 수 있어요</p>`) : ""}</div>`
    : `<div class="bases one">${basisBlock("pokedb", B.pokedb, true)}</div>
        ${B.smogon ? `<details class="fold other-basis"><summary>다른 기준(Showdown 시뮬레이터)으로 보기</summary>${basisBlock("smogon", B.smogon, false)}</details>` : ""}`;
  const assumptions = [...a.assumptions, ...names.flatMap(n => B[n].notes.map(t => `${BASIS_NAME[n]}: ${t}`))];
  const sources = names.map(n => `<li>${BASIS_NAME[n]} · ${esc(B[n].source.label)}${B[n].source.url ? ` · <a href="${esc(B[n].source.url)}" target="_blank" rel="noopener noreferrer">원문</a>` : ""}</li>`).join("");
  $("resultBody").innerHTML = `<div class="appear">
    <h1 class="conclusion">${esc((a.headline || a.summary).replace(/\.$/, ""))}${a.reference_only && names.length ? `<span class="badge">참고용</span>` : ""}</h1>
    ${a.reference_only ? `<p class="small" style="color:var(--warn)">${esc(a.unsupported.join(" · "))}</p>` : ""}
    ${a.assumptions.length ? `<p class="assume">${esc(a.assumptions.join(" · "))} · <button type="button" class="link" data-act="edit">조건 고치기</button></p>`
      : `<div class="row-actions"><button type="button" class="primary" data-act="edit">조건 고치기</button></div>`}
    ${calcBlock(a.calc, a.kind)}
    ${bases && a.calc ? `<h2 class="section-title">통계로 보면</h2><p class="basis-src">상위 사용자들이 실제로 많이 쓰는 빌드로 좁혀 본 원인이에요</p>` : ""}
    ${bases}
    ${hasRolls ? `<p class="roll-legend">통계의 띠는 가장 그럴듯한 조건에서 난수 16번 중 실제 결과와 같게 나온 횟수예요</p>` : ""}
    ${names.length ? `<p class="u7">${U7}</p>
    <details class="fold" id="fold">
      <summary>가정 · 계산하지 않은 것 · 출처</summary>
      <h3>가정</h3><ul>${assumptions.map(t => `<li>${esc(t)}</li>`).join("")}</ul>
      <h3>계산하지 않은 것</h3><ul>${a.unsupported.map(t => `<li>${esc(t)}</li>`).join("") || "<li>없음</li>"}</ul>
      <h3>출처</h3><ul>${sources}</ul>
    </details>
    <div class="feedback" id="feedback">이 턴이 실제로 진 이유였나요?
      <div class="btns"><button type="button" data-fb="yes">예</button><button type="button" data-fb="no">아니요</button><button type="button" data-fb="unsure">모르겠어요</button></div>
      <p class="hint warn" id="fbStatus" role="status"></p>
    </div>` : ""}
  </div>`;
  announce("복기 결과가 나왔어요");
}

document.addEventListener("click", async e => {
  const fb = e.target.closest("[data-fb]");
  if (fb && st.reviewId) {
    let ok = false;
    try { ok = (await (await api(`/api/feature/review/${encodeURIComponent(st.reviewId)}/feedback`, { answer: fb.dataset.fb })).json()).ok; } catch (err) { if (err.status === 403) return; }
    // 기록 실패면 답한 버튼은 그대로 두고 문구만 바꾼다(다시 누를 수 있게, E5 ④)
    if (ok) { $("feedback").innerHTML = `<span class="muted">답해 주셔서 고마워요. 기록했어요.</span>`; announce("기록했어요"); }
    else { $("fbStatus").textContent = MSG.feedback_failed; announce(MSG.feedback_failed); }
  }
  const act = e.target.closest("[data-act]");
  if (act) { if (act.dataset.act === "edit") editForm(); else run(...(st.lastArgs || [])); }
});
$("deleteReq").addEventListener("click", async () => {
  if (!confirm("지금까지의 복기 기록을 모두 지울까요? 되돌릴 수 없어요.")) return;
  try { status(`기록 ${(await (await api("/api/feature/review/delete", {})).json()).deleted}건을 지웠어요`); }
  catch (err) { if (err.status !== 403) status(MSG.internal, "warn"); }
});
function editForm() { if (st.controller) st.controller.abort(); $("resultView").classList.add("hidden"); $("askView").classList.remove("hidden"); $("moreBox").open = true; showConfirm(); }
$("editBtn").addEventListener("click", editForm);
function reset() {
  if (st.controller) st.controller.abort();
  st.ask = []; st.notes = []; st.extractionId = null; st.reviewId = null;
  $("askForm").reset(); st.me = st.opp = null; st.actor = "opp"; clearMove(); meC.set(""); oppC.set("");
  $("hpChips").classList.add("hidden"); $("moreBox").open = false; status("");
  $("confirmView").classList.add("hidden"); $("ruleView").classList.add("hidden");
  $("askView").classList.remove("hidden"); $("resultView").classList.add("hidden");
  refreshFlags(); refresh(); quotaLine();
}
$("newBtn").addEventListener("click", () => { reset(); $("nlInput").focus(); });
document.querySelectorAll("[data-ex]").forEach(b => b.addEventListener("click", () => { $("nlInput").value = b.dataset.ex; $("nlInput").focus(); }));

refreshFlags(); refresh(); refreshQuota();
