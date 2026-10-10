"""ASR evaluation: WER/CER against the case scripts and keyword-spot recall.

Two kinds of numbers per ASR configuration (profile + ``--set``):

* **WER / CER vs the gsw script.** The references are Swiss German *dialect spelling* ("Prüefig",
  "Quartalszahle") while most models write Standard German ("Prüfung", "Quartalszahlen"), so this WER
  is inflated for de-output models and only comparable between models with the same output style.
  Optional pseudo-references (``--ref-dir`` with ``<call_id>.txt`` or ``<dialogue_id>.txt``, e.g. a
  Standard German translation) give a second WER/CER, flagged as pseudo.
* **Keyword-spot recall** (the metric that matters for the checks). Every expected-assessment file lists
  its annotated keyword spots (``Keywordstellen: K04 'vor de Meldig' T008 K relevant; ...``). The
  scripts have no timestamps, so a spot counts as found when the keyword check's own matcher (same
  normalization, same ``fuzzy`` setting as the profile) finds that keyword id *anywhere* in the ASR
  transcript: per keyword id ``min(found, annotated) / annotated``. Keyword ids found in the ASR but
  not annotated in the call at all are reported as false hits. The same matcher on the reference
  script gives the ceiling ("ref"): a spot the matcher misses even on the script is not an ASR error.

Transcripts come from :meth:`Pipeline.transcribe` (same ASR cache as every other command);
``cached_only`` looks them up with ``ctx.cache.get`` under the same key (:func:`asr_cache_key`) and skips
calls that are not cached instead of loading Whisper. Speed: ``elapsed_s`` that faster-whisper stores in
``Transcript.meta``, else ``runs/logs/asr_sweep_<tag>.jsonl`` from ``scripts/research/asr_sweep.py``.
Uncertainty: 1000x dialogue-cluster bootstrap (clean + noisy versions of a dialogue resampled together).
"""

from __future__ import annotations

import csv
import json
import logging
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

import jiwer

from callguard.checks.keywords import KeywordCheck
from callguard.checks.textnorm import fold, segment_tokens
from callguard.data import Call, Turn, parse_turns
from callguard.families import load_families
from callguard.types import Family, Segment, Transcript

log = logging.getLogger("callguard.eval_asr")

WER_GSW_LABEL = "WER vs gsw script (dialect spelling, inflated for de-output models)"
CER_GSW_LABEL = "CER vs gsw script (dialect spelling)"

# --------------------------------------------------------------------------------------------
# Keywordstellen
# --------------------------------------------------------------------------------------------

# "K11 'Vollmacht' T007 B relevant": keyword id, quoted phrase as spoken, turn, speaker (B = Beratung,
# K = Kunde/Kundin), relevance (relevant / benign). Entries are ';'-separated; calls without spots say
# "keine registrierte Vollphrase; Kontexttest". finditer tolerates ',' separators and missing tails.
_SPOT_RE = re.compile(r"\b(K\d{2})\s+['‘’\"«](.+?)['‘’\"»]\s+(T\d{3})\b(?:\s+([BK])\b)?(?:\s+([a-zA-Z]+))?")


@dataclass(frozen=True)
class KeywordSpot:
    keyword_id: str  # "K04"
    phrase: str  # "vor de Meldig" (as written in the script)
    turn: str  # "T008"
    speaker: str = ""  # "B" (advisor) / "K" (customer) / "" if not given
    relevance: str = ""  # "relevant" / "benign" / ""


def parse_keyword_spots(text: str | None) -> list[KeywordSpot]:
    """Spots of a ``Keywordstellen:`` value (the line prefix is optional). No spots -> []."""
    if not text:
        return []
    text = text.split("Keywordstellen:", 1)[-1]
    return [KeywordSpot(m.group(1), m.group(2).strip(), m.group(3), m.group(4) or "", m.group(5) or "")
            for m in _SPOT_RE.finditer(text)]


# --------------------------------------------------------------------------------------------
# normalization + WER/CER
# --------------------------------------------------------------------------------------------

_NUMBERS: dict[str, int] = {
    # Standard German (folded: ü -> u, ß -> ss)
    "null": 0, "eins": 1, "zwei": 2, "zwo": 2, "drei": 3, "vier": 4, "funf": 5, "sechs": 6, "sieben": 7,
    "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwolf": 12, "dreizehn": 13, "vierzehn": 14,
    "funfzehn": 15, "sechzehn": 16, "siebzehn": 17, "achtzehn": 18, "neunzehn": 19, "zwanzig": 20,
    "dreissig": 30, "vierzig": 40, "funfzig": 50, "sechzig": 60, "siebzig": 70, "achtzig": 80,
    "neunzig": 90, "hundert": 100, "tausend": 1000,
    # Swiss German spellings. Left out on purpose: "eis"/"ein" (article), "nün" -> "nun" (= now),
    # "zäh" (= tough): mapping them would create more errors than it removes.
    "zwoi": 2, "zwoo": 2, "dru": 3, "foif": 5, "fuf": 5, "fuuf": 5, "sachs": 6, "nuun": 9, "sibe": 7, "sibni": 7, "zwolfi": 12,
    "drizah": 13, "drizehn": 13, "vierzah": 14, "fufzah": 15, "sachzah": 16, "sibezah": 17,
    "achtzah": 18, "nunzah": 19, "zwanzg": 20, "drissg": 30, "drissig": 30, "vierzg": 40, "fufzg": 50,
    "sachzg": 60, "sibezg": 70, "achtzg": 80, "nunzg": 90, "tusig": 1000, "tuusig": 1000,
}
_UNITS = {"ein": 1, "eis": 1, "zwei": 2, "zwoi": 2, "drei": 3, "dru": 3, "vier": 4, "funf": 5, "foif": 5,
          "fuf": 5, "fuuf": 5, "nuun": 9, "sechs": 6, "sachs": 6, "sieben": 7, "sibe": 7, "acht": 8, "neun": 9, "nun": 9}
_TENS = {k: v for k, v in _NUMBERS.items() if v in (20, 30, 40, 50, 60, 70, 80, 90)}
# "einundzwanzig", Swiss "einezwänzg" / "drüezwänzg"
_COMPOUND_RE = re.compile(rf"^({'|'.join(_UNITS)})(?:und|e)({'|'.join(_TENS)})$")
_THOUSANDS_RE = re.compile(r"(?<=\d)['’.  ](?=\d{3}\b)")
_APOSTROPHE_RE = re.compile(r"['’`´]")
_WORD_RE = re.compile(r"[^\W_]+")


def _number(tok: str) -> str:
    if tok in _NUMBERS:
        return str(_NUMBERS[tok])
    m = _COMPOUND_RE.match(tok)
    if m:
        return str(_UNITS[m.group(1)] + _TENS[m.group(2)])
    return tok


def normalize_text(text: str) -> str:
    """WER form: lowercase, umlauts folded (ä -> a, ß -> ss), punctuation dropped, whitespace collapsed,
    number words 0-20 + tens (German and Swiss spellings) as digits, "1'000" -> "1000", "%" -> prozent."""
    text = text.replace("%", " prozent ")
    text = _THOUSANDS_RE.sub("", text)
    text = _APOSTROPHE_RE.sub("", fold(text).lower())  # "geht's" -> "gehts" on both sides
    return " ".join(_number(t) for t in _WORD_RE.findall(text))


@dataclass
class ErrorCounts:
    ref_words: int = 0
    word_errors: int = 0
    subs: int = 0
    dels: int = 0
    ins: int = 0
    ref_chars: int = 0
    char_errors: int = 0

    @property
    def wer(self) -> float | None:
        return self.word_errors / self.ref_words if self.ref_words else None

    @property
    def cer(self) -> float | None:
        return self.char_errors / self.ref_chars if self.ref_chars else None


def error_counts(reference: str, hypothesis: str) -> ErrorCounts:
    """Word and character edit counts on normalized text (corpus WER = sum errors / sum ref words)."""
    ref, hyp = normalize_text(reference), normalize_text(hypothesis)
    if not ref:
        return ErrorCounts()
    w = jiwer.process_words(ref, hyp)
    c = jiwer.process_characters(ref, hyp)
    n_ref_chars = c.hits + c.substitutions + c.deletions
    return ErrorCounts(ref_words=w.hits + w.substitutions + w.deletions,
                       word_errors=w.substitutions + w.deletions + w.insertions,
                       subs=w.substitutions, dels=w.deletions, ins=w.insertions, ref_chars=n_ref_chars,
                       char_errors=c.substitutions + c.deletions + c.insertions)


# --------------------------------------------------------------------------------------------
# keyword spotting
# --------------------------------------------------------------------------------------------


class KeywordSpotter:
    """Counts keyword-id hits with the keyword check's matcher (all segments, negated hits included:
    "nöd protokolliere" is a spot whatever the context). All families and keywords of the keyword
    list count, independent of the profile's ``families`` filter."""

    def __init__(self, check: KeywordCheck, families: list[Family]):
        self.families = [f.model_copy(update={"enabled": True, "keywords": [
            k.model_copy(update={"enabled": True}) for k in f.keywords]}) for f in families]
        self.check = check
        self._phrases: dict[str | None, list[Any]] = {}

    def phrases(self, lang: str | None = None) -> list[Any]:
        """Match patterns for a view language (``Keyword.forms``: gsw/de/unset -> de + gsw forms)."""
        if lang not in self._phrases:
            self._phrases[lang] = self.check.compile(self.families, lang)[0]
        return self._phrases[lang]

    def count(self, segments: Iterable[Segment], lang: str | None = None) -> Counter[str]:
        phrases, cues = self.phrases(lang), self.check.cues_for(lang)
        seen: set[tuple[str, int, int]] = set()  # one keyword id in two families counts once
        for i, seg in enumerate(segments):
            _, toks = segment_tokens(seg)
            for h in self.check.segment_hits(phrases, toks, cues):
                seen.add((h.phrase.keyword.id, i, h.first))
        return Counter(kid for kid, _, _ in seen)


def spotter_for(pipe: Any) -> KeywordSpotter:
    """The profile's keyword check (its fuzzy setting), or a default one if the profile has none."""
    check = next((c for c in pipe.checks if isinstance(c, KeywordCheck)), None) or KeywordCheck(pipe.ctx)
    ctx = pipe.ctx
    return KeywordSpotter(check, load_families(ctx.path("keywords"), ctx.path("criteria")))


@dataclass
class SpotScore:
    annotated: dict[str, int]  # keyword id -> annotated spots in the call
    found: dict[str, int]  # keyword id -> hits in the text
    matched: int  # sum over annotated ids of min(found, annotated)
    false_hit_ids: list[str]  # found but not annotated in this call

    @property
    def n_annotated(self) -> int:
        return sum(self.annotated.values())

    @property
    def recall(self) -> float | None:
        return self.matched / self.n_annotated if self.n_annotated else None


def score_spots(spots: list[KeywordSpot], found: Counter[str] | dict[str, int]) -> SpotScore:
    annotated = Counter(s.keyword_id for s in spots)
    matched = sum(min(found.get(k, 0), n) for k, n in annotated.items())
    false_ids = sorted(k for k, n in found.items() if n and k not in annotated)
    return SpotScore(dict(annotated), {k: n for k, n in sorted(found.items()) if n}, matched, false_ids)


# --------------------------------------------------------------------------------------------
# per call
# --------------------------------------------------------------------------------------------


def turns_as_segments(turns: list[Turn]) -> list[Segment]:
    return [Segment(id=t.id, start=0.0, end=0.0, text=t.text) for t in turns if t.text.strip()]


def load_pseudo_ref(ref_dir: Path | None, call: Call) -> str | None:
    if ref_dir is None:
        return None
    for name in (call.call_id, call.dialogue_id):
        p = Path(ref_dir) / f"{name}.txt"
        if p.exists():
            text = p.read_text(encoding="utf-8")
            turns = parse_turns(text)
            return " ".join(t.text for t in turns) if turns else text
    return None


def _r(x: float | None, nd: int = 4) -> float | None:
    return None if x is None else round(x, nd)


def load_sweep_timing(path: Path | None) -> dict[str, dict[str, float]]:
    """``call_id -> {seconds, audio_s}`` from an ``asr_sweep.py`` log. A call logged twice (a rerun hit
    the cache, ~0 s) keeps its slowest record, i.e. the real decode."""
    out: dict[str, dict[str, float]] = {}
    if not path or not Path(path).exists():
        return out
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
            cid, sec = rec["call_id"], float(rec["seconds"])
        except (ValueError, KeyError, TypeError):
            continue
        if cid not in out or sec > out[cid]["seconds"]:
            out[cid] = {"seconds": sec, "audio_s": float(rec.get("audio_s") or 0.0)}
    return out


def evaluate_call(call: Call, transcript: Transcript, spotter: KeywordSpotter,
                  pseudo_ref: str | None = None, sweep: dict[str, float] | None = None) -> dict[str, Any]:
    ref_text = " ".join(t.text for t in call.turns)
    hyp_text = transcript.text()
    e = error_counts(ref_text, hyp_text)
    spots = parse_keyword_spots(call.expected.keyword_spots if call.expected else "")
    asr = score_spots(spots, spotter.count(transcript.segments, transcript.lang))
    ref = score_spots(spots, spotter.count(turns_as_segments(call.turns)))
    meta = transcript.meta or {}
    duration = transcript.duration or (sweep or {}).get("audio_s") or None
    elapsed, timing = meta.get("elapsed_s"), "meta" if meta.get("elapsed_s") is not None else ""
    if elapsed is None and sweep:
        elapsed, timing = sweep.get("seconds"), "sweep_log"
    row: dict[str, Any] = {
        "call_id": call.call_id, "dialogue_id": call.dialogue_id, "level": call.level,
        "variant": call.variant, "noisy": call.noisy,
        "label": call.expected.label if call.expected else "",
        "family": call.expected.family if call.expected else "",
        "ref_words": e.ref_words, "word_errors": e.word_errors, "subs": e.subs, "dels": e.dels, "ins": e.ins,
        "wer": _r(e.wer), "ref_chars": e.ref_chars, "char_errors": e.char_errors, "cer": _r(e.cer),
        "kw_annotated": asr.n_annotated, "kw_matched": asr.matched, "kw_recall": _r(asr.recall),
        "kw_ref_matched": ref.matched, "kw_ref_recall": _r(ref.recall),
        "kw_missed_ids": ",".join(k for k, n in asr.annotated.items() if asr.found.get(k, 0) < n),
        "kw_false_hits": len(asr.false_hit_ids), "kw_false_hit_ids": ",".join(asr.false_hit_ids),
        "kw_ref_false_hit_ids": ",".join(ref.false_hit_ids),
        "kw_annotated_ids": json.dumps(asr.annotated), "kw_found_ids": json.dumps(asr.found),
        "kw_ref_found_ids": json.dumps(ref.found),
        "duration_s": duration, "asr_elapsed_s": elapsed, "timing_source": timing,
        "rtf": _r(elapsed / duration, 3) if elapsed is not None and duration else None,
        "asr_backend": transcript.asr_backend, "degraded": bool(meta.get("degraded")),
    }
    if pseudo_ref is not None:
        p = error_counts(pseudo_ref, hyp_text)
        row.update({"pseudo_ref_words": p.ref_words, "pseudo_word_errors": p.word_errors,
                    "pseudo_wer": _r(p.wer), "pseudo_ref_chars": p.ref_chars,
                    "pseudo_char_errors": p.char_errors, "pseudo_cer": _r(p.cer)})
    return row


# --------------------------------------------------------------------------------------------
# aggregation
# --------------------------------------------------------------------------------------------


def _ratio(rows: list[dict], num: str, den: str) -> float | None:
    d = sum(r.get(den) or 0 for r in rows)
    return sum(r.get(num) or 0 for r in rows) / d if d else None


STATS: dict[str, Callable[[list[dict]], float | None]] = {
    "wer": lambda rows: _ratio(rows, "word_errors", "ref_words"),
    "cer": lambda rows: _ratio(rows, "char_errors", "ref_chars"),
    "kw_recall": lambda rows: _ratio(rows, "kw_matched", "kw_annotated"),
    "kw_ref_recall": lambda rows: _ratio(rows, "kw_ref_matched", "kw_annotated"),
    "kw_false_hits_per_call": lambda rows: (sum(r["kw_false_hits"] for r in rows) / len(rows)) if rows else None,
    "pseudo_wer": lambda rows: _ratio(rows, "pseudo_word_errors", "pseudo_ref_words"),
    "pseudo_cer": lambda rows: _ratio(rows, "pseudo_char_errors", "pseudo_ref_chars"),
}
CI_STATS = ("wer", "cer", "kw_recall", "kw_false_hits_per_call")


def bootstrap_ci(rows: list[dict], stat: Callable[[list[dict]], float | None], n: int = 1000,
                 seed: int = 0, alpha: float = 0.05) -> tuple[float, float] | None:
    """Percentile CI, resampling whole twin groups (``splits.group_of``: clean + noisy of a dialogue, and
    the Stufe2 twin dialogues, together: they are not independent; a dialogue without a twin is its own
    unit)."""
    from callguard.splits import group_of

    by_unit: dict[str, list[dict]] = {}
    for r in rows:
        by_unit.setdefault(group_of(r["dialogue_id"]), []).append(r)
    groups = list(by_unit.values())
    if len(groups) < 2:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        v = stat([r for g in rng.choices(groups, k=len(groups)) for r in g])
        if v is not None:
            vals.append(v)
    if len(vals) < n // 2:
        return None
    vals.sort()
    return round(vals[int(alpha / 2 * len(vals))], 4), round(vals[min(len(vals) - 1, int((1 - alpha / 2) * len(vals)))], 4)


def summarize_group(rows: list[dict], ci: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {"n_calls": len(rows), "n_dialogues": len({r["dialogue_id"] for r in rows}),
                           "ref_words": sum(r["ref_words"] for r in rows),
                           "kw_spots": sum(r["kw_annotated"] for r in rows),
                           "kw_matched": sum(r["kw_matched"] for r in rows),
                           "kw_ref_matched": sum(r["kw_ref_matched"] for r in rows),
                           "kw_false_hits": sum(r["kw_false_hits"] for r in rows)}
    for name, fn in STATS.items():
        if name.startswith("pseudo") and not any("pseudo_wer" in r for r in rows):
            continue
        v = fn(rows)
        out[name] = _r(v)
        if ci and name in CI_STATS and v is not None:
            out[f"{name}_ci95"] = bootstrap_ci(rows, fn)
    timed = [r for r in rows if r.get("asr_elapsed_s") is not None and r.get("duration_s")]
    audio_s = sum(r["duration_s"] or 0 for r in rows)
    out["audio_min"] = round(audio_s / 60, 2)
    if timed:
        el, du = sum(r["asr_elapsed_s"] for r in timed), sum(r["duration_s"] for r in timed)
        out["rtf"] = round(el / du, 4)
        out["asr_s_per_audio_min"] = round(60 * el / du, 2)
        out["timed_calls"] = len(timed)
    return out


def per_keyword(rows: list[dict]) -> dict[str, dict[str, int]]:
    """Per keyword id over all calls: annotated spots, matched in ASR / in the script, false-hit calls."""
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        ann, found, ref = (json.loads(r[k]) for k in ("kw_annotated_ids", "kw_found_ids", "kw_ref_found_ids"))
        for kid in set(ann) | set(found):
            d = out.setdefault(kid, {"annotated": 0, "matched": 0, "ref_matched": 0, "false_hit_calls": 0})
            n = ann.get(kid, 0)
            d["annotated"] += n
            d["matched"] += min(found.get(kid, 0), n)
            d["ref_matched"] += min(ref.get(kid, 0), n)
            d["false_hit_calls"] += int(n == 0 and found.get(kid, 0) > 0)
    return dict(sorted(out.items()))


def summarize(rows: list[dict], *, ci: bool = True) -> dict[str, Any]:
    groups: dict[str, list[dict]] = {"all": rows,
                                     "clean": [r for r in rows if not r["noisy"]],
                                     "noisy": [r for r in rows if r["noisy"]]}
    for lvl in sorted({r["level"] for r in rows}):
        groups[f"level{lvl}"] = [r for r in rows if r["level"] == lvl]
        for name, noisy in (("clean", False), ("noisy", True)):
            groups[f"level{lvl}_{name}"] = [r for r in rows if r["level"] == lvl and r["noisy"] == noisy]
    return {"groups": {k: summarize_group(v, ci=ci) for k, v in groups.items() if v},
            "per_keyword": per_keyword(rows)}


# --------------------------------------------------------------------------------------------
# run + outputs
# --------------------------------------------------------------------------------------------


def default_tag(asr_spec: dict[str, Any]) -> str:
    """ASR model dir name + compute type, e.g. ``whisper-turbo-gsw-ct2-int8``, ``whisper-large-v3_float16``."""
    model = asr_spec.get("model")
    tag = Path(str(model)).name if model else str(asr_spec.get("type", "asr"))
    ct = asr_spec.get("compute_type")
    if ct and not tag.endswith(str(ct)):
        tag = f"{tag}_{ct}"
    return re.sub(r"[^\w.+-]+", "_", tag)


def asr_cache_key(pipe: Any, audio_path: Path) -> dict[str, Any]:
    """The key :meth:`Pipeline.transcribe` stores transcripts under (pinned by a test). Building the ASR
    plugin is cheap: models load on first decode, which never happens here."""
    return pipe.asr_key(audio_path)


def cached_transcript(pipe: Any, call: Call) -> Transcript | None:
    t = pipe.ctx.cache.get("asr", asr_cache_key(pipe, call.audio_path), Transcript)
    if t is not None:
        t.call_id, t.audio_path = call.call_id, str(call.audio_path)
    return t


def transcript_for(pipe: Any, call: Call, *, cached_only: bool) -> Transcript | None:
    if cached_only:
        return cached_transcript(pipe, call)
    return pipe.transcribe(call.audio_path, call.call_id)


@dataclass
class AsrEvalResult:
    tag: str
    rows: list[dict[str, Any]]
    summary: dict[str, Any]
    skipped: list[str] = field(default_factory=list)
    out_dir: Path | None = None


def run_asr_eval(pipe: Any, calls: list[Call], *, tag: str, cached_only: bool = False,
                 ref_dir: Path | None = None, profile: str = "", overrides: list[str] | None = None,
                 sweep_log: Path | None = None,
                 on_call: Callable[[Call], None] | None = None) -> AsrEvalResult:
    spotter = spotter_for(pipe)
    sweep = load_sweep_timing(sweep_log)
    rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    for call in calls:
        if on_call:
            on_call(call)
        if not call.turns:
            log.warning("asr-eval: %s has no reference script, skipped", call.call_id)
            skipped.append(call.call_id)
            continue
        t = transcript_for(pipe, call, cached_only=cached_only)
        if t is None:
            skipped.append(call.call_id)
            continue
        rows.append(evaluate_call(call, t, spotter, load_pseudo_ref(ref_dir, call), sweep.get(call.call_id)))
    summary = summarize(rows)
    backends = sorted({r["asr_backend"] for r in rows})
    summary["meta"] = {
        "tag": tag, "profile": profile, "overrides": list(overrides or []), "asr": pipe.cfg.asr,
        "asr_backend": backends[0] if len(backends) == 1 else backends,
        "keyword_fuzzy": spotter.check.fuzzy, "cached_only": cached_only,
        "n_evaluated": len(rows), "skipped": skipped, "pseudo_ref_dir": str(ref_dir) if ref_dir else None,
        "sweep_log": str(sweep_log) if sweep else None,
        "timing_sources": dict(Counter(r["timing_source"] or "none" for r in rows)),
        "wer_label": WER_GSW_LABEL, "cer_label": CER_GSW_LABEL,
        "kw_recall_def": "per call and keyword id min(hits in ASR, annotated spots) / annotated spots; "
                         "kw_ref_recall = same matcher on the reference script (ceiling)",
        "ci": "95% percentile bootstrap over twin groups / dialogues (1000x)",
    }
    return AsrEvalResult(tag=tag, rows=rows, summary=summary, skipped=skipped)


def write_outputs(res: AsrEvalResult, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    if res.rows:
        fields = list(dict.fromkeys(k for r in res.rows for k in r))
        with open(out_dir / "per_call.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(res.rows)
    (out_dir / "summary.json").write_text(json.dumps(res.summary, indent=1, ensure_ascii=False, default=str))
    (out_dir / "summary.md").write_text(summary_markdown(res))
    res.out_dir = out_dir
    return out_dir


# --------------------------------------------------------------------------------------------
# markdown
# --------------------------------------------------------------------------------------------


def fmt_pct(x: float | None) -> str:
    return "-" if x is None else f"{100 * x:.1f}%"


def fmt_ci(ci: Any, pct: bool = True) -> str:
    if not ci:
        return ""
    lo, hi = ci
    return f" [{100 * lo:.1f}-{100 * hi:.1f}]" if pct else f" [{lo:.2f}-{hi:.2f}]"


def fmt_num(x: float | None, nd: int = 2) -> str:
    return "-" if x is None else f"{x:.{nd}f}"


GROUP_COLUMNS = ("group", "calls", "WER gsw", "CER gsw", "kw recall", "kw recall (script)", "kw spots",
                 "false hits/call", "RTF", "s/audio-min")


def group_cells(name: str, g: dict[str, Any]) -> list[str]:
    return [name, str(g["n_calls"]), fmt_pct(g.get("wer")) + fmt_ci(g.get("wer_ci95")),
            fmt_pct(g.get("cer")) + fmt_ci(g.get("cer_ci95")),
            fmt_pct(g.get("kw_recall")) + fmt_ci(g.get("kw_recall_ci95")), fmt_pct(g.get("kw_ref_recall")),
            f"{g['kw_matched']}/{g['kw_spots']}",
            fmt_num(g.get("kw_false_hits_per_call")) + fmt_ci(g.get("kw_false_hits_per_call_ci95"), pct=False),
            fmt_num(g.get("rtf"), 3), fmt_num(g.get("asr_s_per_audio_min"), 1)]


def _md_table(header: Iterable[str], rows: Iterable[Iterable[str]]) -> str:
    header = list(header)
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def summary_markdown(res: AsrEvalResult) -> str:
    s, m = res.summary, res.summary.get("meta", {})
    parts = [f"# ASR eval `{res.tag}`", "",
             f"- profile `{m.get('profile')}` {' '.join(f'`--set {o}`' for o in m.get('overrides', []))}",
             f"- backend `{m.get('asr_backend')}`, keyword matcher fuzzy={m.get('keyword_fuzzy')}",
             f"- {m.get('n_evaluated')} calls evaluated, {len(res.skipped)} skipped"
             + (" (not cached)" if m.get("cached_only") else ""),
             f"- **{WER_GSW_LABEL}**",
             f"- kw recall: {m.get('kw_recall_def')}",
             f"- brackets: {m.get('ci')}; 30 dialogues: small differences are noise",
             f"- speed (RTF = ASR seconds / audio seconds) from: {m.get('timing_sources')}", "",
             "## Groups", "",
             _md_table(GROUP_COLUMNS, (group_cells(k, g) for k, g in s["groups"].items()))]
    if any("pseudo_wer" in g for g in s["groups"].values()):
        parts += ["", "Pseudo-reference (not the official script):", "",
                  _md_table(("group", "pseudo WER", "pseudo CER"),
                            ((k, fmt_pct(g.get("pseudo_wer")), fmt_pct(g.get("pseudo_cer")))
                             for k, g in s["groups"].items()))]
    parts += ["", "## Per keyword", "",
              _md_table(("keyword", "spots", "found in ASR", "found in script", "calls with false hits"),
                        ((k, d["annotated"], d["matched"], d["ref_matched"], d["false_hit_calls"])
                         for k, d in s["per_keyword"].items())),
              "", "## Per call", "",
              _md_table(("call", "WER", "CER", "kw", "missed", "false hits", "RTF"),
                        ((r["call_id"], fmt_pct(r["wer"]), fmt_pct(r["cer"]),
                          f"{r['kw_matched']}/{r['kw_annotated']}", r["kw_missed_ids"] or "-",
                          r["kw_false_hit_ids"] or "-", fmt_num(r["rtf"], 3)) for r in res.rows))]
    if res.skipped:
        parts += ["", f"Skipped: {', '.join(res.skipped)}"]
    return "\n".join(parts) + "\n"


COMPARE_COLUMNS = ("tag", "calls", "WER gsw", "WER clean", "WER noisy", "CER gsw", "kw recall",
                   "kw clean", "kw noisy", "kw (script)", "false hits/call", "s/audio-min", "RTF")


def compare(tags: list[str], root: Path = Path("runs/asr_eval")) -> str:
    """Side-by-side markdown table of several ``asr-eval`` runs (tag = dir under ``root`` or a path)."""
    rows = []
    for tag in tags:
        p = Path(tag) if Path(tag).is_dir() else Path(root) / tag
        f = p / "summary.json"
        if not f.exists():
            rows.append([tag, "missing"] + [""] * (len(COMPARE_COLUMNS) - 2))
            continue
        g = json.loads(f.read_text())["groups"]
        a, c, n = g.get("all", {}), g.get("clean", {}), g.get("noisy", {})
        rows.append([p.name, str(a.get("n_calls", 0)), fmt_pct(a.get("wer")) + fmt_ci(a.get("wer_ci95")),
                     fmt_pct(c.get("wer")), fmt_pct(n.get("wer")), fmt_pct(a.get("cer")),
                     fmt_pct(a.get("kw_recall")) + fmt_ci(a.get("kw_recall_ci95")), fmt_pct(c.get("kw_recall")),
                     fmt_pct(n.get("kw_recall")), fmt_pct(a.get("kw_ref_recall")),
                     fmt_num(a.get("kw_false_hits_per_call")), fmt_num(a.get("asr_s_per_audio_min"), 1),
                     fmt_num(a.get("rtf"), 3)])
    note = (f"\nWER/CER: {WER_GSW_LABEL}. kw recall: annotated keyword spots the keyword matcher finds in "
            "the ASR output; 'kw (script)' = same matcher on the reference script (ceiling). "
            "Brackets: 95% dialogue bootstrap CI. Only compare runs over the same calls.\n")
    return _md_table(COMPARE_COLUMNS, rows) + "\n" + note


__all__ = ["KeywordSpot", "parse_keyword_spots", "normalize_text", "error_counts", "ErrorCounts",
           "KeywordSpotter", "score_spots", "SpotScore", "evaluate_call", "summarize", "run_asr_eval",
           "write_outputs", "compare", "default_tag", "asr_cache_key", "cached_transcript",
           "load_sweep_timing"]
