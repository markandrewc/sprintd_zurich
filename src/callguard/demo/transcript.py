"""Audio + transcript, synchronised: one self-contained HTML document for ``st.components.v1.html``.

Everything is rendered here, server side and escaped (``html.escape``): the segments with speaker role and
timestamp, the suspicious passages tinted in their family colour with a label, «möglicherweise verhört»
marks, keyword hits, and jump buttons «Passage 1 · 00:37» that start ``link_pad`` seconds early and pause
``link_pad`` seconds after the passage. A small inline script (no CDN, no network) only adds behaviour:

* ``timeupdate`` highlights the segment being spoken and scrolls it into view smoothly, unless the reader
  scrolled by hand in the last seconds (then a «Zur aktuellen Stelle» button appears instead);
* clicking a segment seeks there and plays; clicking the passage strip above seeks to that point;
* ``start_at`` (deep link ``?t=``) positions the recording and the transcript there on load.

Without audio (recording not on this machine) the transcript still renders, with a note. Pure Python, no
Streamlit import: unit-tested directly (tests/test_demo.py).
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from callguard.misheard import passage_segments
from callguard.types import CallResult, Passage, Transcript, fmt_ts

ROLE_DE = {"advisor": "Beratung", "customer": "Kunde"}
MISHEARD_DE = "möglicherweise verhört"
DEFAULT_ACCENT = "#2a78d6"
FALLBACK_COLOR = "#6b7a8f"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _color(value: str | None, fallback: str = FALLBACK_COLOR) -> str:
    return value if value and _HEX.match(value) else fallback


def _rgba(hex_color: str, alpha: float) -> str:
    h = _color(hex_color).lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.2f})"


def _num(x: float) -> str:
    """A float for an HTML attribute (plain, locale-free)."""
    return f"{float(x):.2f}"


def mark_terms(text: str, terms: Iterable[str]) -> str:
    """``text`` escaped, every (case-insensitive) occurrence of a term wrapped in ``<mark>``."""
    low = text.lower()
    spans: list[list[int]] = []
    for term in {t.strip().lower() for t in terms if t and t.strip()}:
        start = 0
        while (i := low.find(term, start)) >= 0:
            spans.append([i, i + len(term)])
            start = i + len(term)
    if not spans:
        return html.escape(text)
    spans.sort()
    merged = [spans[0]]
    for a, b in spans[1:]:
        if a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out, pos = [], 0
    for a, b in merged:
        out.append(html.escape(text[pos:a]))
        out.append(f'<mark class="cg-kw">{html.escape(text[a:b])}</mark>')
        pos = b
    out.append(html.escape(text[pos:]))
    return "".join(out)


def keyword_terms(result: CallResult) -> dict[str, list[str]]:
    """Matched keyword text per segment id (keyword / pattern findings), for the ``<mark>`` highlight."""
    out: dict[str, list[str]] = {}
    for cr in result.checks.values():
        if cr.type != "keywords":
            continue
        for f in cr.findings:
            d = f.detail if isinstance(f.detail, dict) else {}
            matched = d.get("matched_text") or d.get("phrase")
            if matched and isinstance(matched, str) and not d.get("negated"):
                for sid in f.segment_ids:
                    out.setdefault(sid, []).append(matched)
    return out


@dataclass
class Mark:
    """A passage as the player shows it."""

    number: int  # 1-based, as in «Passage 1»
    family: str
    label: str  # short family label
    start: float
    end: float
    color: str
    seek: float  # where the jump button starts (start - link_pad, >= 0)
    stop: float  # where it pauses again (end + link_pad)
    segment_ids: list[str]
    misheard: bool


def passage_marks(transcript: Transcript, passages: Sequence[Passage], colors: Mapping[str, str],
                  labels: Mapping[str, str], link_pad: float = 10.0) -> list[Mark]:
    out = []
    for i, p in enumerate(passages):
        segs = passage_segments(transcript, p)
        label = labels.get(p.family) or (p.family_label or p.family).split(" (")[0]
        out.append(Mark(number=i + 1, family=p.family, label=label, start=float(p.start), end=float(p.end),
                        color=_color(colors.get(p.family)), seek=max(0.0, float(p.start) - link_pad),
                        stop=float(p.end) + link_pad, segment_ids=[s.id for s in segs], misheard=bool(p.misheard)))
    return out


def start_segment(transcript: Transcript, t: float | None) -> str | None:
    """Id of the segment that contains ``t`` (the last one starting at or before it); in a pause between two
    segments the next one (about to be spoken); None without ``t``. The player's script uses the same rule."""
    if t is None or not transcript.segments:
        return None
    segs = transcript.segments
    i = 0
    for k, s in enumerate(segs):
        if s.start <= t + 1e-3:
            i = k
        else:
            break
    if t > segs[i].end + 1e-3 and i + 1 < len(segs):
        i += 1
    return segs[i].id


def player_html(transcript: Transcript, passages: Sequence[Passage], *, audio_src: str | None,
                colors: Mapping[str, str] | None = None, labels: Mapping[str, str] | None = None,
                start_at: float | None = None, link_pad: float = 10.0, misheard_below: float | None = None,
                terms: Mapping[str, list[str]] | None = None, height: int = 660, accent: str = DEFAULT_ACCENT,
                audio_note: str = "", autoplay: bool = False, nonce: int = 0) -> str:
    """The whole component document. ``audio_src``: a data URI or URL, None = no recording here
    (``audio_note`` says why). ``start_at``: deep-link time in seconds. ``height``: iframe height in px."""
    colors, labels, terms = colors or {}, labels or {}, terms or {}
    accent = _color(accent, DEFAULT_ACCENT)
    marks = passage_marks(transcript, passages, colors, labels, link_pad)
    seg_mark: dict[str, Mark] = {}
    first_of: dict[str, Mark] = {}
    for m in marks:
        for sid in m.segment_ids:
            seg_mark.setdefault(sid, m)  # a segment in two passages takes the first (highest-ranked) one
        if m.segment_ids and m.segment_ids[0] not in first_of:
            first_of[m.segment_ids[0]] = m
    duration = max([float(transcript.duration or 0.0)] + [s.end for s in transcript.segments] + [0.0])
    current = start_segment(transcript, start_at)

    rows = []
    for s in transcript.segments:
        m = seg_mark.get(s.id)
        role = ROLE_DE.get(s.role or "") or (s.speaker or "Sprecher")
        role_cls = s.role if s.role in ROLE_DE else "other"
        tags = []
        head = first_of.get(s.id)
        if head is not None:
            tags.append(f'<span class="cg-tag" style="background:{head.color}">Passage {head.number} · '
                        f'{html.escape(head.label)}</span>')
        low = (misheard_below is not None and s.confidence is not None and s.confidence < misheard_below)
        if low:
            tags.append(f'<span class="cg-misheard" title="Die Spracherkennung war hier unsicher '
                        f'(Konfidenz {s.confidence:.2f}): bitte anhören.">{MISHEARD_DE}</span>')
        style = (f' style="--fam:{m.color};background:{_rgba(m.color, 0.10)}"' if m is not None else "")
        cls = ["cg-seg", f"role-{role_cls}"] + (["in-passage"] if m is not None else []) \
            + (["is-low"] if low else []) + (["is-current"] if s.id == current else [])
        rows.append(
            f'<div class="{" ".join(cls)}" id="seg-{html.escape(s.id)}" data-start="{_num(s.start)}" '
            f'data-end="{_num(s.end)}"{style} title="Klicken: Aufnahme springt hierher">'
            f'<div class="cg-meta"><span class="cg-time">{fmt_ts(s.start)}</span>'
            f'<span class="cg-role">{html.escape(role)}</span>{"".join(tags)}</div>'
            f'<div class="cg-text">{mark_terms(s.text.strip(), terms.get(s.id, []))}</div></div>')
    if not rows:
        rows.append('<p class="cg-empty">Kein Transkript vorhanden (Stille, oder die Spracherkennung ist '
                    'fehlgeschlagen).</p>')

    jumps = "".join(
        f'<button type="button" class="cg-jump" data-seek="{_num(m.seek)}" data-stop="{_num(m.stop)}" '
        f'data-seg="{html.escape(m.segment_ids[0]) if m.segment_ids else ""}" '
        f'title="Spielt ab {fmt_ts(m.seek)} ({link_pad:.0f} s vor der Passage) bis {fmt_ts(m.stop)} '
        f'({link_pad:.0f} s danach)"><span class="cg-dot" style="background:{m.color}"></span>'
        f'Passage {m.number} ({fmt_ts(m.start)}) · {html.escape(m.label)}'
        f'{" · " + MISHEARD_DE if m.misheard else ""}</button>'
        for m in marks)
    strip = "".join(
        f'<div class="cg-band" style="left:{100 * m.start / duration:.3f}%;'
        f'width:{max(0.6, 100 * (m.end - m.start) / duration):.3f}%;background:{m.color}" '
        f'title="Passage {m.number} · {html.escape(m.label)} · {fmt_ts(m.start)}–{fmt_ts(m.end)}"></div>'
        for m in marks if duration > 0)
    if audio_src:
        player = (f'<audio id="cg-audio" controls preload="auto" src="{html.escape(audio_src, quote=True)}">'
                  f'</audio>')
    else:
        player = (f'<div class="cg-noaudio">Aufnahme auf diesem Rechner nicht verfügbar'
                  f'{": " + html.escape(audio_note) if audio_note else ""}. Das Transkript bleibt lesbar.</div>')
    hint = (f"Passagen: {len(marks)} · Klick auf einen Abschnitt spielt ihn ab" if marks
            else "Keine verdächtige Passage · Klick auf einen Abschnitt spielt ihn ab")
    config = json.dumps({"startAt": start_at, "duration": duration, "hasAudio": bool(audio_src),
                         "autoplay": bool(autoplay), "nonce": int(nonce)})
    slots = {"HEIGHT": str(int(height)), "ACCENT": accent, "ACCENT_SOFT": _rgba(accent, 0.16), "PLAYER": player,
             "JUMPS": jumps, "STRIP": strip, "HINT": html.escape(hint), "ROWS": "\n".join(rows),
             "CONFIG": html.escape(config, quote=True)}
    # one pass: text that happens to contain a slot name is never substituted a second time
    return _SLOT.sub(lambda m: slots[m.group(1)], _TEMPLATE)


_SLOT = re.compile(r"__(HEIGHT|ACCENT_SOFT|ACCENT|PLAYER|JUMPS|STRIP|HINT|ROWS|CONFIG)__")


_TEMPLATE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<style>
  :root { --accent: __ACCENT__; --accent-soft: __ACCENT_SOFT__; --ink: #1b1f24; --muted: #5f6670;
          --line: #e3e5e8; --surface: #ffffff; --plane: #f6f7f9; }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; background: var(--surface); color: var(--ink);
               font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
  .cg-root { height: __HEIGHT__px; display: flex; flex-direction: column; border: 1px solid var(--line);
             border-radius: 12px; overflow: hidden; }
  .cg-top { padding: 14px 16px 10px; border-bottom: 1px solid var(--line); background: var(--plane); }
  audio { width: 100%; height: 40px; }
  .cg-noaudio { padding: 10px 12px; border-radius: 8px; background: #fff; border: 1px dashed var(--line);
                color: var(--muted); font-size: 14px; }
  .cg-track { position: relative; height: 10px; margin: 10px 2px 2px; border-radius: 5px; background: #e9ecef;
              cursor: pointer; }
  .cg-band { position: absolute; top: 0; height: 10px; border-radius: 5px; opacity: .85; }
  .cg-head { position: absolute; top: -3px; width: 2px; height: 16px; background: var(--ink); left: 0;
             border-radius: 1px; pointer-events: none; }
  .cg-jumps { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
  .cg-jump { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--line);
             background: #fff; color: var(--ink); border-radius: 999px; padding: 4px 12px; font: inherit;
             font-size: 13px; cursor: pointer; }
  .cg-jump:hover, .cg-jump:focus-visible { border-color: var(--accent); outline: none; }
  .cg-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
  .cg-bar { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 6px 16px;
            border-bottom: 1px solid var(--line); font-size: 12.5px; color: var(--muted); }
  .cg-bar label { display: inline-flex; gap: 6px; align-items: center; cursor: pointer; }
  .cg-now { border: 0; background: var(--accent); color: #fff; border-radius: 999px; padding: 3px 12px;
            font: inherit; font-size: 12.5px; cursor: pointer; visibility: hidden; }
  .cg-now.show { visibility: visible; }
  .cg-transcript { position: relative; flex: 1; overflow-y: auto; padding: 8px 10px 40vh; scroll-behavior: auto; }
  .cg-seg { padding: 8px 12px 9px; margin: 2px 0; border-radius: 8px; cursor: pointer;
            border-left: 3px solid transparent; transition: box-shadow .15s ease; }
  .cg-seg:hover { background: var(--plane); }
  .cg-seg.in-passage { border-left-color: var(--fam); }
  .cg-seg.is-current { box-shadow: inset 0 0 0 2px var(--ink); }
  .cg-seg.is-current .cg-time { color: var(--ink); font-weight: 700; }
  .cg-seg.is-current .cg-time::before { content: "▶"; font-size: 9px; margin-right: 5px; vertical-align: 1px; }
  .cg-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 12.5px; color: var(--muted); }
  .cg-time { font-variant-numeric: tabular-nums; }
  .cg-role { font-weight: 600; color: var(--ink); }
  .role-customer .cg-role { color: #34495e; }
  .cg-tag { color: #fff; border-radius: 999px; padding: 0 9px; font-size: 11.5px; font-weight: 600; }
  .cg-misheard { border: 1px solid #c98500; color: #7a4d00; background: #fff6e0; border-radius: 999px;
                 padding: 0 8px; font-size: 11.5px; }
  .cg-text { margin-top: 2px; }
  mark.cg-kw { background: none; font-weight: 700; text-decoration: underline; text-decoration-color: var(--accent);
               text-decoration-thickness: 2px; text-underline-offset: 3px; color: inherit; }
  .cg-empty { color: var(--muted); padding: 16px; }
</style></head>
<body>
<div class="cg-root" id="cg-root" data-config="__CONFIG__">
  <div class="cg-top">
    __PLAYER__
    <div class="cg-track" id="cg-track" title="Klicken: an diese Stelle springen">__STRIP__<div class="cg-head" id="cg-head"></div></div>
    <div class="cg-jumps">__JUMPS__</div>
  </div>
  <div class="cg-bar"><span>__HINT__</span>
    <span><button type="button" class="cg-now" id="cg-now">Zur aktuellen Stelle</button>
    <label><input type="checkbox" id="cg-follow" checked> Mitlaufen</label></span></div>
  <div class="cg-transcript" id="cg-transcript">
__ROWS__
  </div>
</div>
<script>
(function () {
  var root = document.getElementById("cg-root");
  var cfg = JSON.parse(root.getAttribute("data-config"));
  var audio = document.getElementById("cg-audio");
  var box = document.getElementById("cg-transcript");
  var follow = document.getElementById("cg-follow");
  var nowBtn = document.getElementById("cg-now");
  var head = document.getElementById("cg-head");
  var track = document.getElementById("cg-track");
  var segs = Array.prototype.slice.call(document.querySelectorAll(".cg-seg"));
  var starts = segs.map(function (s) { return parseFloat(s.getAttribute("data-start")); });
  var ends = segs.map(function (s) { return parseFloat(s.getAttribute("data-end")); });
  var current = -1, userScrollAt = 0, stopAt = null, ours = false;
  var duration = cfg.duration || 0;

  function indexAt(t) {
    var lo = 0, hi = starts.length - 1, best = -1;
    while (lo <= hi) { var mid = (lo + hi) >> 1; if (starts[mid] <= t + 1e-3) { best = mid; lo = mid + 1; } else { hi = mid - 1; } }
    if (best < 0) return starts.length ? 0 : -1;
    if (t > ends[best] + 1e-3 && best + 1 < starts.length) return best + 1;  // pause: the next one is coming
    return best;
  }
  function inView(el) {
    var top = el.offsetTop - box.scrollTop, h = box.clientHeight;
    return top > h * 0.08 && top + Math.min(el.offsetHeight, h * 0.5) < h * 0.75;
  }
  function scrollTo(el, smooth) {
    var top = Math.max(0, el.offsetTop - box.clientHeight * 0.25);
    try { box.scrollTo({ top: top, behavior: smooth ? "smooth" : "auto" }); } catch (e) { box.scrollTop = top; }
  }
  function setCurrent(i, force) {
    if (i === current && !force) return;
    if (current >= 0 && segs[current]) segs[current].classList.remove("is-current");
    current = i;
    if (i < 0 || !segs[i]) return;
    segs[i].classList.add("is-current");
    var reading = Date.now() - userScrollAt < 6000;
    if (force || (follow.checked && !reading)) {
      if (force || !inView(segs[i])) scrollTo(segs[i], !force);
      nowBtn.classList.remove("show");
    } else if (!inView(segs[i])) {
      nowBtn.classList.add("show");
    }
  }
  function moveHead(t) {
    var d = (audio && isFinite(audio.duration) && audio.duration > 0) ? audio.duration : duration;
    if (d > 0) head.style.left = Math.min(100, 100 * t / d) + "%";
  }
  function seek(t, stop) {
    t = Math.max(0, t);
    stopAt = (stop === undefined) ? null : stop;
    userScrollAt = 0;
    setCurrent(indexAt(t), true);
    moveHead(t);
    if (!audio) return;
    ours = true;
    audio.currentTime = t;
    var p = audio.play(); if (p && p.catch) p.catch(function () {});
  }

  ["wheel", "touchmove"].forEach(function (ev) {
    box.addEventListener(ev, function () { userScrollAt = Date.now(); }, { passive: true });
  });
  box.addEventListener("keydown", function () { userScrollAt = Date.now(); });
  nowBtn.addEventListener("click", function () { userScrollAt = 0; if (current >= 0) setCurrent(current, true); });
  follow.addEventListener("change", function () { if (follow.checked) { userScrollAt = 0; if (current >= 0) setCurrent(current, true); } });
  segs.forEach(function (el, i) { el.addEventListener("click", function () { seek(starts[i]); }); });
  Array.prototype.forEach.call(document.querySelectorAll(".cg-jump"), function (b) {
    b.addEventListener("click", function () { seek(parseFloat(b.getAttribute("data-seek")), parseFloat(b.getAttribute("data-stop"))); });
  });
  track.addEventListener("click", function (e) {
    var r = track.getBoundingClientRect();
    var d = (audio && isFinite(audio.duration) && audio.duration > 0) ? audio.duration : duration;
    if (d > 0 && r.width > 0) seek(d * (e.clientX - r.left) / r.width);
  });

  if (audio) {
    audio.addEventListener("timeupdate", function () {
      var t = audio.currentTime;
      moveHead(t);
      setCurrent(indexAt(t), false);
      if (stopAt !== null && t >= stopAt) { stopAt = null; audio.pause(); }
    });
    audio.addEventListener("seeking", function () {
      if (!ours) { stopAt = null; setCurrent(indexAt(audio.currentTime), false); }
      ours = false;
    });
    if (cfg.startAt !== null && cfg.startAt !== undefined) {
      var place = function () {
        ours = true; audio.currentTime = Math.max(0, cfg.startAt); moveHead(cfg.startAt);
        if (cfg.autoplay) { var pp = audio.play(); if (pp && pp.catch) pp.catch(function () {}); }
      };
      if (audio.readyState >= 1) { place(); } else { audio.addEventListener("loadedmetadata", place, { once: true }); }
    }
  }
  var first = document.querySelector(".cg-seg.is-current");
  if (first) { current = segs.indexOf(first); scrollTo(first, false); if (cfg.startAt) moveHead(cfg.startAt); }
})();
</script>
</body></html>
"""
