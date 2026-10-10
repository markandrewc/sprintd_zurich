// Sherlock Phones · Dashboard (ohne Framework). Spricht mit der JSON-API in dashboard/app.py.
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const main = $("#main");

const VERDICT = { alarm: "Alarm", ok: "Kein Alarm", busy: "In Arbeit", error: "Fehler", stale: "Neu prüfen" };
const REVIEW = { fraud: "Verstoss bestätigt", no_fraud: "Kein Verstoss", unclear: "Unklar" };
const ICON = {
  check: '<svg viewBox="0 0 16 16" class="ic"><path d="M3.5 8.5l3 3 6-7"/></svg>',
  cross: '<svg viewBox="0 0 16 16" class="ic"><path d="M4.5 4.5l7 7m0-7l-7 7"/></svg>',
  play: '<svg viewBox="0 0 10 10"><path d="M2 1.2v7.6L8.6 5z"/></svg>',
  chev: '<svg viewBox="0 0 16 16" class="ic chev"><path d="M6 3.5L10.5 8 6 12.5"/></svg>',
  refresh: '<svg viewBox="0 0 20 20" class="ic"><path d="M16 10a6 6 0 1 1-1.8-4.3M16 3.5v3.2h-3.2"/></svg>',
  trash: '<svg viewBox="0 0 20 20" class="ic"><path d="M4.5 6h11M8 6V4.5h4V6m-6 0l.7 9.5h6.6L14 6"/></svg>',
  plus: '<svg viewBox="0 0 20 20" class="ic"><path d="M10 4.5v11M4.5 10h11"/></svg>',
};

const state = { view: null, calls: [], counts: {}, filter: "all", selected: null, detail: null, cfg: null,
                listKey: "", detailKey: "", workerBusy: false };

// ------------------------------------------------------------------ Hilfen

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function api(path, opts = {}) {
  const init = { ...opts, headers: { ...(opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {}), ...opts.headers } };
  if (init.body && !(init.body instanceof FormData) && typeof init.body !== "string") init.body = JSON.stringify(init.body);
  const r = await fetch(path, init);
  const data = r.headers.get("content-type")?.includes("json") ? await r.json() : null;
  if (!r.ok) {
    const d = data?.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map(x => x.msg).join("; ") : `Fehler ${r.status}`);
  }
  return data;
}

function toast(msg, err = false) {
  const el = document.createElement("div");
  el.className = "toast" + (err ? " err" : "");
  el.textContent = msg;
  $("#toasts").append(el);
  setTimeout(() => el.remove(), err ? 6000 : 3000);
}

const clock = s => s == null ? "--:--" : `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const pct = p => `${Math.round(p * 100)}%`;
const when = iso => {
  if (!iso) return "";
  const d = new Date(iso), now = new Date();
  const time = d.toLocaleTimeString("de-CH", { hour: "2-digit", minute: "2-digit" });
  return d.toDateString() === now.toDateString() ? `heute ${time}` : `${d.toLocaleDateString("de-CH", { day: "2-digit", month: "2-digit", year: "2-digit" })} ${time}`;
};
const slug = s => s.toLowerCase().replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/[^a-z0-9]+/g, "_")
  .replace(/^[^a-z]+|_+$/g, "").slice(0, 40);
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

// ------------------------------------------------------------------ Routing

function route() {
  const [, view = "anrufe", id, sub] = location.hash.split("/");
  $$("#tabs a").forEach(a => a.classList.toggle("active", a.dataset.view === view));
  if (view === "regeln") return showRules(id, sub && decodeURIComponent(sub));   // #/regeln/regel/<id> bzw. #/regeln/fakt/<id> öffnet den Editor
  if (view === "einstellungen") return showSettings();
  showCalls(id ? Number(id) : null);
}
window.addEventListener("hashchange", route);

// ------------------------------------------------------------------ Status (alle 3 s)

async function pollStatus() {
  try {
    const s = await api("/api/status");
    const svc = (name, st) => `<span class="svc"><span class="dot ${st}"></span>${name}</span>`;
    const w = s.worker;
    $("#status").innerHTML = (w.busy ? `<span class="job"><span class="spinner"></span>${esc(w.step || "In Warteschlange …")}</span>` : "")
      + svc("Transkription", s.transcription) + svc("Analyse", s.analysis);
    const wasBusy = state.workerBusy;
    state.workerBusy = w.busy;
    if (state.view === "anrufe" && (w.busy || wasBusy)) { await loadCalls(); if (state.selected) await loadDetail(state.selected, true); }
  } catch { $("#status").innerHTML = '<span class="svc"><span class="dot offline"></span>Dashboard nicht erreichbar</span>'; }
}
setInterval(pollStatus, 3000);
setInterval(() => { if (state.view === "anrufe" && document.visibilityState === "visible") loadCalls(); }, 10000);

// ------------------------------------------------------------------ Anrufe

function showCalls(id) {
  const fresh = state.view !== "anrufe";
  if (fresh) {
    state.view = "anrufe"; state.listKey = ""; state.detailKey = ""; state.detail = null;
    main.innerHTML = `<div class="calls">
      <section class="list-pane">
        <div class="list-head"><h1>Anrufe</h1><div class="seg" id="filter"></div></div>
        <div class="list" id="list"></div>
      </section>
      <section class="detail-pane" id="detail-pane"></section></div>`;
  }
  loadCalls().then(() => {
    const pick = id ?? state.selected ?? state.calls[0]?.id ?? null;
    if (fresh || pick !== state.selected || !state.detail) select(pick, false);
  });
}

async function loadCalls() {
  try {
    const data = await api("/api/calls");
    state.calls = data.calls; state.counts = data.counts;
    renderList();
  } catch (e) { toast(e.message, true); }
}

function filtered() {
  if (state.filter === "alarm") return state.calls.filter(c => c.verdict === "alarm");
  if (state.filter === "open") return state.calls.filter(c => c.status === "fertig" && !c.label);
  return state.calls;
}

function renderList() {
  const key = JSON.stringify([state.calls, state.filter, state.selected]);
  if (key === state.listKey || state.view !== "anrufe") return;
  state.listKey = key;
  const n = state.counts;
  $("#filter").innerHTML = [["all", "Alle", n.all], ["alarm", "Alarme", n.alarm], ["open", "Nicht beurteilt", n.open]]
    .map(([k, l, c]) => `<button data-f="${k}" class="${state.filter === k ? "on" : ""}">${l}<span class="n">${c ?? 0}</span></button>`).join("");
  const rows = filtered();
  $("#list").innerHTML = rows.length ? rows.map(c => `
    <div class="row ${c.id === state.selected ? "sel" : ""}" data-id="${c.id}">
      <span class="vdot ${c.verdict}"></span>
      <span class="name" title="${esc(c.filename)}">${esc(c.filename)}</span>
      <span class="badge ${c.verdict}">${VERDICT[c.verdict]}</span>
      <div class="meta"><span>Nr. ${c.id}</span><span>·</span><span>${when(c.created_at)}</span>
        ${c.status === "fertig" ? `<span>·</span><span>${c.label ? REVIEW[c.label] : "nicht beurteilt"}</span>` : ""}</div>
      ${c.rules.length ? `<div class="rules-line"><span class="chip no">${esc(c.rules[0])}</span>${c.rules.length > 1 ? `<span class="more-n">+${c.rules.length - 1}</span>` : ""}</div>` : ""}
    </div>`).join("") : `<div class="empty"><b>${state.calls.length ? "Keine Anrufe in dieser Ansicht" : "Noch keine Anrufe"}</b>
      ${state.calls.length ? "" : "Laden Sie Aufnahmen über „Anrufe hochladen“ hoch oder ziehen Sie sie ins Fenster."}</div>`;
}

$("#main").addEventListener("click", e => {
  const f = e.target.closest("#filter button");
  if (f) { state.filter = f.dataset.f; renderList(); return; }
  const row = e.target.closest(".row[data-id]");
  if (row) select(Number(row.dataset.id));
});

function select(id, push = true) {
  state.selected = id;
  if (push && id != null) history.replaceState(null, "", `#/anrufe/${id}`);
  renderList();
  if (id == null) { $("#detail-pane").innerHTML = `<div class="empty" style="padding-top:120px"><b>Kein Anruf ausgewählt</b></div>`; return; }
  loadDetail(id);
}

async function loadDetail(id, quiet = false) {
  try {
    const d = await api(`/api/calls/${id}`);
    if (id !== state.selected) return;
    state.detail = d;
    const key = JSON.stringify(d);
    if (quiet && key === state.detailKey) return;
    state.detailKey = key;
    renderDetail(d);
  } catch (e) {
    if (!quiet) { state.detail = null; $("#detail-pane").innerHTML = `<div class="empty"><b>${esc(e.message)}</b></div>`; }
  }
}

function condRow(c, th) {
  return `<div class="cond" title="${esc(c.question)}">
    <span class="mark ${c.met ? "ok" : "no"}">${c.met ? ICON.check : ICON.cross}</span>
    <span class="lbl">${esc(c.label)}</span>
    <span>${c.region ? `<span class="time" data-region="${c.region}">${ICON.play}Stelle ${c.region}</span>` : ""}</span>
    <span class="want">verlangt ${c.want} · ist ${c.yes ? "ja" : "nein"}</span>
    <span class="bar"><i class="${c.yes ? "yes" : ""}" style="width:${pct(c.p)}"></i><span class="th" style="left:${pct(th)}"></span></span>
    <span class="pct">${pct(c.p)}</span></div>`;
}

function ruleBlock(r, th) {
  return `<div class="rule"><div class="rule-h">${esc(r.name)}${r.fired ? '<span class="badge alarm">löst aus</span>' : ""}</div>
    ${r.conditions.map(c => condRow(c, th)).join("")}</div>`;
}

function renderDetail(d) {
  const fired = d.rules.filter(r => r.fired), rest = d.rules.filter(r => !r.fired);
  const canReanalyze = d.status !== "in_arbeit" && d.transcript;
  const notice = d.verdict === "busy" ? `<div class="notice"><span class="spinner"></span>Wird transkribiert und geprüft. Das Ergebnis erscheint hier von selbst.</div>`
    : d.verdict === "error" ? `<div class="notice err">${esc(d.error || "Unbekannter Fehler")}</div>`
    : d.verdict === "stale" ? `<div class="notice">Dieser Anruf wurde mit den früheren Prüfpunkten analysiert.<button class="btn sm" data-act="reanalyze" style="margin-left:auto">${ICON.refresh}Jetzt neu prüfen</button></div>` : "";
  const rulesCard = d.verdict === "alarm" || d.verdict === "ok" ? `<div class="card">
      <div class="card-h"><h3>${fired.length ? "Ausgelöste Regeln" : "Keine Regel ausgelöst"}</h3><span class="count">${fired.length} von ${d.rules.length}</span>
        <span class="muted" style="margin-left:auto;font-size:12px">Ein Fakt gilt ab ${pct(d.threshold)} als ja</span></div>
      ${fired.map(r => ruleBlock(r, d.threshold)).join("")}
      ${rest.length ? `<details class="more"><summary>${ICON.chev}${fired.length ? "Weitere" : "Alle"} ${rest.length} Regeln</summary>${rest.map(r => ruleBlock(r, d.threshold)).join("")}</details>` : ""}
    </div>` : "";
  const regionsCard = d.regions.length ? `<div class="card"><div class="card-h"><h3>Fundstellen</h3><span class="count">${d.regions.length}</span></div>
      ${d.regions.map(r => `<div class="region"><div class="region-h"><b>Stelle ${r.n}</b>
        ${r.start != null ? `<span class="time" data-region="${r.n}">${ICON.play}${clock(r.start)}–${clock(r.end)}</span>` : '<span class="muted">ohne Zeitangabe</span>'}
        ${r.facts.map(f => `<span class="chip yes">${esc(f)}</span>`).join("")}</div>
        <div class="quote">${r.lines.map(l => `<p>${l.speaker ? `<span class="spk">${esc(l.speaker)}:</span>` : ""}${esc(l.text)}</p>`).join("")}</div></div>`).join("")}
    </div>` : "";
  const hit = new Set(d.highlight);
  const transcriptCard = d.transcript ? `<div class="card"><div class="card-h"><h3>Transkript</h3>
      <span class="muted" style="margin-left:auto;font-size:12px">Klick auf eine Zeile spielt sie ab</span></div>
      <div class="transcript" id="transcript">${d.segments.length ? d.segments.map((s, i) => `
        <div class="seg-line ${hit.has(i) ? "hit" : ""}" data-seek="${s.start ?? ""}" data-i="${i}">
          <span class="t">${clock(s.start)}</span><span>${s.speaker ? `<span class="spk">${esc(s.speaker)}:</span>` : ""}${esc(s.text)}</span></div>`).join("")
        : `<div class="card-b">${esc(d.transcript)}</div>`}</div></div>` : "";

  $("#detail-pane").innerHTML = `<div class="detail">
    <div class="dhead"><div><h2>${esc(d.filename)}</h2>
        <div class="sub"><span class="badge ${d.verdict}">${VERDICT[d.verdict]}</span><span>Nr. ${d.id}</span><span>${when(d.created_at)}</span></div></div>
      <div class="actions">
        ${canReanalyze ? `<button class="btn sm" data-act="reanalyze">${ICON.refresh}Neu prüfen</button>` : ""}
        <button class="btn sm ghost danger" data-act="delete">${ICON.trash}Löschen</button></div></div>
    ${d.audio ? `<div class="player"><audio controls preload="metadata" id="audio" src="/api/calls/${d.id}/audio"></audio></div>` : ""}
    <div class="dgrid"><div class="stack">${notice}${rulesCard}${regionsCard}${transcriptCard}</div>
      ${d.status === "fertig" && d.verdict !== "stale" ? reviewCard(d) : "<div></div>"}</div></div>`;
  bindAudio(d);
}

// ---------- Abspielen: ganze Aufnahme, Fundstelle (mit 10 s davor und danach), Zeile im Transkript

let stopAt = null;
function bindAudio(d) {
  const audio = $("#audio");
  if (!audio) return;
  audio.addEventListener("timeupdate", () => {
    if (stopAt != null && audio.currentTime >= stopAt) { audio.pause(); stopAt = null; }
    const t = audio.currentTime;
    let now = -1;
    d.segments.forEach((s, i) => { if (s.start != null && s.start <= t && t < s.end) now = i; });
    $$(".seg-line.now").forEach(el => { if (Number(el.dataset.i) !== now) el.classList.remove("now"); });
    if (now >= 0 && !audio.paused) $(`.seg-line[data-i="${now}"]`)?.classList.add("now");
  });
}

function playFrom(start, end = null) {
  const audio = $("#audio");
  if (!audio || start == null) return;
  audio.currentTime = Math.max(0, start);
  stopAt = end;
  audio.play();
}

$("#main").addEventListener("click", e => {
  const t = e.target.closest("[data-region]");
  if (t && state.detail) {
    const r = state.detail.regions.find(x => x.n === Number(t.dataset.region));
    if (r?.start != null) playFrom(r.start - 10, r.end + 10);
    return;
  }
  const line = e.target.closest(".seg-line[data-seek]");
  if (line && line.dataset.seek !== "") playFrom(Number(line.dataset.seek));
  const act = e.target.closest("[data-act]")?.dataset.act;
  if (act === "reanalyze") reanalyze();
  if (act === "delete") confirmDelete();
  if (act === "save-review") saveReview();
});

async function reanalyze() {
  try { await api(`/api/calls/${state.selected}/reanalyze`, { method: "POST" }); toast("Wird neu geprüft …"); await loadCalls(); await loadDetail(state.selected); pollStatus(); }
  catch (e) { toast(e.message, true); }
}

function confirmDelete() {
  const d = state.detail;
  openModal(`<div class="modal"><div class="modal-h"><h3>Anruf löschen?</h3></div>
    <div class="modal-b"><div><b>${esc(d.filename)}</b> (Nr. ${d.id}) wird endgültig gelöscht, mit Aufnahme, Ergebnis und Beurteilung.</div></div>
    <div class="modal-f"><span class="spacer"></span><button class="btn" data-close>Abbrechen</button>
      <button class="btn danger solid" id="do-delete">Löschen</button></div></div>`);
  $("#do-delete").onclick = async () => {
    try {
      await api(`/api/calls/${d.id}`, { method: "DELETE" });
      closeModal(); toast("Anruf gelöscht");
      const i = filtered().findIndex(c => c.id === d.id);
      await loadCalls();
      const next = filtered()[Math.min(i, filtered().length - 1)]?.id ?? null;
      select(next);
    } catch (e) { toast(e.message, true); }
  };
}

// ---------- Beurteilung

function reviewCard(d) {
  const rv = d.review;
  const names = Object.values(state.cfg?.rules || {}).map(r => r.name);
  const reviewer = rv.labeled_by || localStorage.getItem("reviewer") || "";
  return `<aside class="card review" id="review"><div class="card-h"><h3>Ihre Beurteilung</h3></div><div class="card-b">
    <div><div class="label" style="margin-bottom:6px">Liegt ein Verstoss vor?</div><div class="opts">
      ${Object.entries(REVIEW).map(([k, l]) => `<label class="opt ${rv.label === k ? "on" : ""}"><input type="radio" name="rv-label" value="${k}" ${rv.label === k ? "checked" : ""}>${l}</label>`).join("")}</div></div>
    ${d.findings.length ? `<div><div class="label" style="margin-bottom:6px">Stimmen diese Fakten? <span class="muted" style="font-weight:400">(nicht angehakt = stimmt nicht)</span></div><div class="opts">
      ${d.findings.map(f => `<label class="opt ${rv.checks[f.id] ? "on" : ""}"><input type="checkbox" name="rv-check" value="${esc(f.id)}" ${rv.checks[f.id] ? "checked" : ""}>
        <span style="flex:1">${esc(f.label)}</span>${f.region ? `<span class="muted num" style="font-size:12px">Stelle ${f.region}</span>` : ""}</label>`).join("")}</div></div>` : ""}
    <div><div class="label" style="margin-bottom:6px">Übersehene Regeln <span class="muted" style="font-weight:400">(Verstoss ohne Alarm)</span></div>
      <div class="chips">${names.map(n => `<span class="chip btn-chip ${rv.missed.includes(n) ? "on" : ""}" data-missed="${esc(n)}">${esc(n)}</span>`).join("")}</div></div>
    <div class="field"><label for="rv-comment">Kommentar</label><textarea class="input" id="rv-comment" rows="3">${esc(rv.comment)}</textarea></div>
    <div class="field"><label for="rv-name">Ihr Name</label><input class="input" id="rv-name" value="${esc(reviewer)}"></div>
    <button class="btn primary" data-act="save-review" style="width:100%;justify-content:center">Beurteilung speichern</button>
    ${rv.labeled_at ? `<div class="saved">Zuletzt gespeichert von ${esc(rv.labeled_by)}, ${when(rv.labeled_at)}</div>` : ""}
  </div></aside>`;
}

$("#main").addEventListener("change", e => {
  const opt = e.target.closest(".opt");
  if (!opt) return;
  if (e.target.type === "radio") $$(".opt", opt.parentElement).forEach(o => o.classList.toggle("on", $("input", o).checked));
  else opt.classList.toggle("on", e.target.checked);
});
$("#main").addEventListener("click", e => {
  const chip = e.target.closest("[data-missed]");
  if (chip) chip.classList.toggle("on");
});

async function saveReview() {
  const box = $("#review");
  const label = $("input[name=rv-label]:checked", box)?.value;
  const name = $("#rv-name").value.trim();
  if (!label) return toast("Bitte wählen Sie, ob ein Verstoss vorliegt.", true);
  if (!name) return toast("Bitte geben Sie Ihren Namen an.", true);
  const checks = Object.fromEntries($$("input[name=rv-check]", box).map(i => [i.value, i.checked]));
  const missed = $$(".chip.on[data-missed]", box).map(c => c.dataset.missed);
  try {
    await api(`/api/calls/${state.selected}/review`, { method: "PUT", body: { label, checks, missed, comment: $("#rv-comment").value, name } });
    localStorage.setItem("reviewer", name);
    toast("Beurteilung gespeichert");
    await loadCalls(); await loadDetail(state.selected);
  } catch (e) { toast(e.message, true); }
}

// Pfeiltasten: vorheriger / nächster Anruf
document.addEventListener("keydown", e => {
  if (e.key === "Escape") return closeModal();
  if (state.view !== "anrufe" || !$("#modal").hidden || /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName)) return;
  if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
  const rows = filtered(), i = rows.findIndex(c => c.id === state.selected);
  const next = rows[Math.max(0, Math.min(rows.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)))];
  if (next && next.id !== state.selected) { e.preventDefault(); select(next.id); $(`.row[data-id="${next.id}"]`)?.scrollIntoView({ block: "nearest" }); }
});

// ------------------------------------------------------------------ Fakten und Regeln

async function loadConfig() { state.cfg = await api("/api/config"); return state.cfg; }

async function showRules(kind, id) {
  state.view = "regeln";
  main.innerHTML = `<div class="page"><div class="page-h"><div><h1>Fakten &amp; Regeln</h1></div></div>
    <p class="lead">Zuerst die <b>Grundfakten</b>: Ja/Nein-Fragen, die das Modell zu jedem Anruf beantwortet. Daraus die <b>Regeln</b>:
      Jede Regel legt pro Fakt fest, ob er ja, nein oder egal sein muss. Sind alle Bedingungen erfüllt, löst die Regel aus;
      löst mindestens eine aus, gibt es einen Alarm.</p><div id="rules-body"></div></div>`;
  try { await loadConfig(); renderRules(); } catch (e) { return toast(e.message, true); }
  if (kind === "regel" && id in state.cfg.rules) ruleModal(id);
  if (kind === "fakt" && id in state.cfg.facts) factModal(id);
}

function usage(fid) { return Object.values(state.cfg.rules).filter(r => fid in r.conditions); }

function renderRules(q = $("#fact-search")?.value || "") {
  const { facts, rules } = state.cfg;
  const needle = q.trim().toLowerCase();
  const shown = Object.entries(facts).filter(([id, f]) => !needle || `${id} ${f.label} ${f.instructions}`.toLowerCase().includes(needle));
  $("#rules-body").innerHTML = `
    <div class="section-h"><h2>Grundfakten <span class="muted" style="font-weight:500">${Object.keys(facts).length}</span></h2>
      <input class="input search" id="fact-search" placeholder="Fakten durchsuchen …" value="${esc(q)}">
      <button class="btn" data-new="fact">${ICON.plus}Neuer Fakt</button></div>
    <div class="card items">${shown.map(([id, f]) => {
      const n = usage(id).length;
      return `<div class="item" data-fact="${esc(id)}"><span class="title">${esc(f.label)}</span>
        <span class="side">${n ? `in ${n} Regel${n > 1 ? "n" : ""}` : "in keiner Regel"}</span>
        <span class="desc">${esc(f.instructions)}</span></div>`;
    }).join("") || '<div class="empty">Keine Fakten gefunden</div>'}</div>
    <div class="section-h"><h2>Regeln <span class="muted" style="font-weight:500">${Object.keys(rules).length}</span></h2>
      <button class="btn" data-new="rule">${ICON.plus}Neue Regel</button></div>
    <div class="card items">${Object.entries(rules).map(([id, r]) => {
      const c = Object.entries(r.conditions);
      return `<div class="item" data-rule="${esc(id)}"><span class="title">${esc(r.name)}</span>
        <span class="side">${c.filter(x => x[1] === "ja").length} ja · ${c.filter(x => x[1] === "nein").length} nein</span>
        <div class="conds">${c.map(([f, v]) => `<span class="chip ${v === "ja" ? "yes" : "no"}">${v === "nein" ? "nicht: " : ""}${esc(facts[f]?.label ?? f)}</span>`).join("")}</div></div>`;
    }).join("") || '<div class="empty">Noch keine Regeln</div>'}</div>`;
  const search = $("#fact-search");
  search.oninput = debounce(() => { const pos = search.selectionStart; renderRules(search.value); const s = $("#fact-search"); s.focus(); s.setSelectionRange(pos, pos); }, 120);
}

$("#main").addEventListener("click", e => {
  if (state.view !== "regeln") return;
  const f = e.target.closest("[data-fact]"), r = e.target.closest("[data-rule]"), n = e.target.closest("[data-new]");
  if (f) factModal(f.dataset.fact);
  else if (r) ruleModal(r.dataset.rule);
  else if (n) n.dataset.new === "fact" ? factModal(null) : ruleModal(null);
});

async function saveConfig(facts, rules) {
  await api("/api/config", { method: "PUT", body: { facts, rules } });
  await loadConfig();
  renderRules();
}

function factModal(id) {
  const f = id ? state.cfg.facts[id] : { label: "", instructions: "" };
  const used = id ? usage(id) : [];
  openModal(`<div class="modal"><div class="modal-h"><h3>${id ? "Fakt bearbeiten" : "Neuer Fakt"}</h3></div>
    <div class="modal-b">
      <div class="two"><div class="field"><label>Bezeichnung</label><input class="input" id="f-label" value="${esc(f.label)}" placeholder="z.B. Kauf- oder Verkaufswunsch"></div>
        <div class="field"><label>ID</label><input class="input mono" id="f-id" value="${esc(id || "")}" placeholder="z.B. trade_wish"></div></div>
      <div class="field"><label>Frage an das Modell (Ja/Nein)</label><textarea class="input" id="f-q" rows="4" placeholder="Englisch funktioniert am besten, z.B. Does someone express their own wish to buy or sell a financial instrument?">${esc(f.instructions)}</textarea></div>
      ${used.length ? `<div class="muted" style="font-size:13px">Verwendet in: ${used.map(r => esc(r.name)).join(", ")}</div>` : ""}
      <div class="muted" style="font-size:12px">Eine neue oder geänderte Frage gilt für neu geprüfte Anrufe (beim Anruf „Neu prüfen“).</div>
      <div id="m-err"></div></div>
    <div class="modal-f">${id ? `<button class="btn ghost danger" id="f-del">${ICON.trash}Löschen</button>` : ""}<span class="spacer"></span>
      <button class="btn" data-close>Abbrechen</button><button class="btn primary" id="f-save">Speichern</button></div></div>`);
  const label = $("#f-label"), idIn = $("#f-id");
  if (!id) label.oninput = () => { if (!idIn.dataset.touched) idIn.value = slug(label.value); };
  idIn.oninput = () => { idIn.dataset.touched = "1"; };
  label.focus();
  $("#f-save").onclick = async () => {
    const nid = idIn.value.trim();
    const entry = { type: "noul", label: label.value.trim(), instructions: $("#f-q").value.trim() };
    if (!entry.label) return modalError("Bitte eine Bezeichnung angeben.");
    if (!entry.instructions) return modalError("Bitte die Frage angeben.");
    if (nid !== id && nid in state.cfg.facts) return modalError(`Die ID „${nid}“ gibt es schon.`);
    const facts = {}, rules = {};
    if (id) for (const [k, v] of Object.entries(state.cfg.facts)) facts[k === id ? nid : k] = k === id ? entry : v;
    else Object.assign(facts, state.cfg.facts, { [nid]: entry });
    for (const [rid, r] of Object.entries(state.cfg.rules))
      rules[rid] = { ...r, conditions: Object.fromEntries(Object.entries(r.conditions).map(([k, v]) => [k === id ? nid : k, v])) };
    try { await saveConfig(facts, rules); closeModal(); toast("Fakt gespeichert"); } catch (e) { modalError(e.message); }
  };
  if (id) $("#f-del").onclick = async () => {
    if (used.length) return modalError(`Der Fakt wird noch verwendet in: ${used.map(r => r.name).join(", ")}. Erst dort auf „egal“ setzen.`);
    const facts = { ...state.cfg.facts }; delete facts[id];
    try { await saveConfig(facts, state.cfg.rules); closeModal(); toast("Fakt gelöscht"); } catch (e) { modalError(e.message); }
  };
}

function ruleModal(id) {
  const r = id ? state.cfg.rules[id] : { name: "", conditions: {} };
  const cond = { ...r.conditions };
  const facts = state.cfg.facts;
  openModal(`<div class="modal wide"><div class="modal-h"><h3>${id ? "Regel bearbeiten" : "Neue Regel"}</h3></div>
    <div class="modal-b">
      <div class="two"><div class="field"><label>Name der Regel</label><input class="input" id="r-name" value="${esc(r.name)}" placeholder="z.B. Insiderhandel"></div>
        <div class="field"><label>ID</label><input class="input mono" id="r-id" value="${esc(id || "")}" placeholder="z.B. insider_trading"></div></div>
      <div style="display:flex;align-items:center;gap:12px"><span class="label">Bedingungen pro Fakt</span><span class="muted" id="r-sum" style="font-size:12px"></span>
        <input class="input search" id="r-search" placeholder="Fakten filtern …" style="margin-left:auto;height:32px"></div>
      <div class="facts-pick" id="r-facts">${Object.entries(facts).map(([fid, f]) => `
        <div class="pick" data-fid="${esc(fid)}"><div style="min-width:0"><div>${esc(f.label)}</div><div class="q" title="${esc(f.instructions)}">${esc(f.instructions)}</div></div>
          <div class="tri">${["ja", "egal", "nein"].map(v => `<button data-v="${v}" class="${v} ${(cond[fid] || "egal") === v ? "on" : ""}">${v}</button>`).join("")}</div></div>`).join("")}</div>
      <div id="m-err"></div></div>
    <div class="modal-f">${id ? `<button class="btn ghost danger" id="r-del">${ICON.trash}Löschen</button>` : ""}<span class="spacer"></span>
      <button class="btn" data-close>Abbrechen</button><button class="btn primary" id="r-save">Speichern</button></div></div>`);
  const sum = () => {
    const v = Object.values(cond);
    $("#r-sum").textContent = `${v.filter(x => x === "ja").length} ja · ${v.filter(x => x === "nein").length} nein · übrige egal`;
  };
  sum();
  $("#r-facts").onclick = e => {
    const b = e.target.closest(".tri button");
    if (!b) return;
    const fid = b.closest(".pick").dataset.fid;
    if (b.dataset.v === "egal") delete cond[fid]; else cond[fid] = b.dataset.v;
    $$("button", b.parentElement).forEach(x => x.classList.toggle("on", x === b));
    sum();
  };
  $("#r-search").oninput = e => {
    const q = e.target.value.trim().toLowerCase();
    $$(".pick", $("#r-facts")).forEach(p => { p.style.display = !q || p.textContent.toLowerCase().includes(q) ? "" : "none"; });
  };
  const name = $("#r-name"), idIn = $("#r-id");
  if (!id) name.oninput = () => { if (!idIn.dataset.touched) idIn.value = slug(name.value); };
  idIn.oninput = () => { idIn.dataset.touched = "1"; };
  name.focus();
  $("#r-save").onclick = async () => {
    const nid = idIn.value.trim();
    if (!name.value.trim()) return modalError("Bitte einen Namen angeben.");
    if (!Object.keys(cond).length) return modalError("Mindestens ein Fakt muss ja oder nein sein.");
    if (nid !== id && nid in state.cfg.rules) return modalError(`Die ID „${nid}“ gibt es schon.`);
    const entry = { name: name.value.trim(), conditions: Object.fromEntries(Object.keys(facts).filter(f => f in cond).map(f => [f, cond[f]])) };
    const rules = {};
    if (id) for (const [k, v] of Object.entries(state.cfg.rules)) rules[k === id ? nid : k] = k === id ? entry : v;
    else Object.assign(rules, state.cfg.rules, { [nid]: entry });
    try { await saveConfig(state.cfg.facts, rules); closeModal(); toast("Regel gespeichert. Gilt sofort für alle Anrufe."); } catch (e) { modalError(e.message); }
  };
  if (id) $("#r-del").onclick = async () => {
    const rules = { ...state.cfg.rules }; delete rules[id];
    try { await saveConfig(state.cfg.facts, rules); closeModal(); toast("Regel gelöscht"); } catch (e) { modalError(e.message); }
  };
}

// ------------------------------------------------------------------ Einstellungen

async function showSettings() {
  state.view = "einstellungen";
  main.innerHTML = `<div class="page"><div class="page-h"><h1>Einstellungen</h1></div><p class="lead">Gilt für alle, die dieses Dashboard verwenden.</p>
    <div class="card" id="settings"></div></div>`;
  let cfg;
  try { cfg = await loadConfig(); } catch (e) { return toast(e.message, true); }
  $("#settings").innerHTML = `
    <div class="setting"><h3>Schwelle</h3><p>Ab welchem Wert des Modells ein Fakt als ja gilt, für alle Fakten gleich. Tiefer = mehr Alarme, weniger übersehene Fälle; höher = weniger Fehlalarme. Gilt sofort für alle Anrufe.</p>
      <div class="slider-row"><input type="range" min="0" max="1" step="0.01" id="s-th" value="${cfg.threshold}"><span class="slider-val" id="s-th-v">${pct(cfg.threshold)}</span>
        <button class="btn primary" id="s-th-save">Speichern</button></div><div class="preview" id="s-th-prev"></div></div>
    <div class="setting"><h3>Länge der Fundstelle</h3><p>Wie viel Text als Fundstelle angezeigt wird. Beim Abspielen kommen 10 Sekunden davor und danach dazu. Gilt für neu geprüfte Anrufe.</p>
      <div class="slider-row"><input type="range" min="5" max="100" step="1" id="s-pw" value="${cfg.passage_words}"><span class="slider-val" id="s-pw-v">${cfg.passage_words} W.</span>
        <button class="btn primary" id="s-pw-save">Speichern</button></div></div>`;
  const th = $("#s-th"), pw = $("#s-pw");
  const preview = debounce(async v => {
    try { const p = await api(`/api/preview?threshold=${v}`); $("#s-th-prev").textContent = `Mit dieser Schwelle hätten ${p.alarms} von ${p.done} geprüften Anrufen einen Alarm.`; } catch { /* ignorieren */ }
  }, 120);
  th.oninput = () => { $("#s-th-v").textContent = pct(Number(th.value)); preview(th.value); };
  pw.oninput = () => { $("#s-pw-v").textContent = `${pw.value} W.`; };
  preview(th.value);
  $("#s-th-save").onclick = async () => { try { await api("/api/settings", { method: "PUT", body: { threshold: Number(th.value) } }); toast(`Schwelle ${pct(Number(th.value))} gespeichert`); } catch (e) { toast(e.message, true); } };
  $("#s-pw-save").onclick = async () => { try { await api("/api/settings", { method: "PUT", body: { passage_words: Number(pw.value) } }); toast(`${pw.value} Wörter pro Fundstelle gespeichert`); } catch (e) { toast(e.message, true); } };
}

// ------------------------------------------------------------------ Modal

function openModal(html) {
  const m = $("#modal");
  m.innerHTML = html; m.hidden = false;
  m.onclick = e => { if (e.target === m || e.target.closest("[data-close]")) closeModal(); };
}
function closeModal() { const m = $("#modal"); m.hidden = true; m.innerHTML = ""; }
function modalError(msg) { $("#m-err").innerHTML = `<div class="err-msg">${esc(msg)}</div>`; }

// ------------------------------------------------------------------ Hochladen (Knopf oder ins Fenster ziehen)

async function upload(files) {
  files = [...files].filter(f => f.type.startsWith("audio/") || /\.(wav|mp3|m4a|flac|ogg|opus|webm|aac)$/i.test(f.name));
  if (!files.length) return toast("Keine Audiodateien erkannt.", true);
  const form = new FormData();
  files.forEach(f => form.append("files", f));
  try {
    const r = await api("/api/calls", { method: "POST", body: form });
    toast(`${r.ids.length} Aufnahme${r.ids.length > 1 ? "n" : ""} hochgeladen, Prüfung läuft`);
    if (state.view !== "anrufe") location.hash = `#/anrufe/${r.ids[0]}`;
    else { await loadCalls(); select(r.ids[0]); }
    pollStatus();
  } catch (e) { toast(e.message, true); }
}
$("#upload-btn").onclick = () => $("#upload-input").click();
$("#upload-input").onchange = e => { upload(e.target.files); e.target.value = ""; };
let dragDepth = 0;
window.addEventListener("dragenter", e => { if (e.dataTransfer?.types.includes("Files")) { dragDepth++; $("#dropzone").classList.add("on"); } });
window.addEventListener("dragleave", () => { if (--dragDepth <= 0) { dragDepth = 0; $("#dropzone").classList.remove("on"); } });
window.addEventListener("dragover", e => e.preventDefault());
window.addEventListener("drop", e => { e.preventDefault(); dragDepth = 0; $("#dropzone").classList.remove("on"); if (e.dataTransfer?.files.length) upload(e.dataTransfer.files); });

// ------------------------------------------------------------------ Start

loadConfig().catch(() => {}).finally(route);
pollStatus();
