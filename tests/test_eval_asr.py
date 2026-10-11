"""callguard asr-eval: normalization, Keywordstellen parsing, keyword-spot recall, cache reuse, CLI."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from typer.testing import CliRunner

from callguard import eval_asr as ea
from callguard.checks.keywords import KeywordCheck
from callguard.config import load_config
from callguard.context import Context
from callguard.data import load_calls
from callguard.pipeline import Pipeline
from callguard.types import Family, Keyword, Segment, Transcript

# real header lines from Skript_mit_Sollbewertung/
LINE_D05 = ("Keywordstellen: K10 'PIN' T003 B benign; K10 'Passwort' T003 B benign; "
            "K10 'Bestätigungscode' T006 K relevant; K10 'TAN' T008 K relevant")
LINE_D02 = ("Keywordstellen: K01 'no nöd publiziert' T004 K relevant; K02 'Finanzabteilig' T004 K relevant; "
            "K03 'Quartalszahle' T004 K relevant; K03 'Quartalszahle' T008 K relevant; "
            "K04 'vor de Meldig' T008 K relevant; K05 'vertraulich' T006 K relevant; K05 'under eus' T006 K relevant")
LINE_NONE = "Keywordstellen: keine registrierte Vollphrase; Kontexttest"


# -- normalization ------------------------------------------------------------------------------


@pytest.mark.parametrize("raw, expected", [
    ("Grüezi, Frau Müller!", "gruezi frau muller"),
    ("Straße  «Prüefig»", "strasse pruefig"),
    ("Er hat zwölf Aktien, nicht 12.", "er hat 12 aktien nicht 12"),
    ("drü, eins, nüün, füüf", "3 1 9 5"),
    ("sibeundzwänzg Sekunde", "27 sekunde"),
    ("einundzwanzig und dreissig", "21 und 30"),
    ("1'000 Franken, 50 %", "1000 franken 50 prozent"),
    ("geht's", "gehts"),
    ("nün", "nun"),  # Swiss "nün" (= now / nine) is ambiguous: left alone
])
def test_normalize_text(raw: str, expected: str) -> None:
    assert ea.normalize_text(raw) == expected


def test_error_counts_after_normalization() -> None:
    e = ea.error_counts("Grüezi, d'Prüefig isch zwölf.", "gruezi d prüefig isch 12")
    # "d'Prüefig" -> "dpruefig" vs "d pruefig": 1 substitution + 1 insertion, the rest matches
    assert (e.ref_words, e.subs, e.ins, e.dels) == (4, 1, 1, 0)
    assert e.wer == pytest.approx(0.5)
    perfect = ea.error_counts("Sie müend mir kei PIN säge.", "sie muend mir kei pin säge")
    assert perfect.wer == 0 and perfect.cer == 0
    assert ea.error_counts("", "irgendwas").wer is None


# -- Keywordstellen -----------------------------------------------------------------------------


def test_parse_keyword_spots_real_lines() -> None:
    spots = ea.parse_keyword_spots(LINE_D05)
    assert [(s.keyword_id, s.phrase, s.turn, s.speaker, s.relevance) for s in spots] == [
        ("K10", "PIN", "T003", "B", "benign"), ("K10", "Passwort", "T003", "B", "benign"),
        ("K10", "Bestätigungscode", "T006", "K", "relevant"), ("K10", "TAN", "T008", "K", "relevant")]
    d02 = ea.parse_keyword_spots(LINE_D02)
    assert len(d02) == 7 and Counter(s.keyword_id for s in d02) == {"K03": 2, "K05": 2, "K01": 1, "K02": 1, "K04": 1}
    assert d02[0].phrase == "no nöd publiziert"
    assert ea.parse_keyword_spots(LINE_NONE) == []
    assert ea.parse_keyword_spots("") == ea.parse_keyword_spots(None) == []
    # value without the prefix (as stored in Expected.keyword_spots)
    assert len(ea.parse_keyword_spots(LINE_D05.split(":", 1)[1])) == 4


CASE_DIR = Path(__file__).resolve().parents[1] / "data_upstream" / "inventx-case-study" / "data"


@pytest.mark.skipif(not (CASE_DIR / "Skript_mit_Sollbewertung").is_dir(), reason="case data not present")
def test_parse_keyword_spots_every_case_file() -> None:
    """Every ';'-separated Kxx entry of every real header parses, with speaker and relevance."""
    import re
    total = 0
    for f in sorted((CASE_DIR / "Skript_mit_Sollbewertung").glob("*.txt")):
        line = next(ln for ln in f.read_text(encoding="utf-8").splitlines() if ln.startswith("Keywordstellen:"))
        entries = [e for e in line.split(":", 1)[1].split(";") if re.match(r"\s*K\d{2}\s", e)]
        spots = ea.parse_keyword_spots(line)
        assert len(spots) == len(entries), f.name
        assert all(s.speaker in ("B", "K") and s.relevance in ("relevant", "benign") for s in spots), f.name
        total += len(spots)
    assert total > 0


# -- keyword-spot recall --------------------------------------------------------------------------


def test_score_spots_caps_per_keyword_and_reports_false_hits() -> None:
    spots = ea.parse_keyword_spots(LINE_D05)  # K10 x4
    s = ea.score_spots(spots, Counter({"K10": 2, "K09": 3}))
    assert (s.n_annotated, s.matched, s.recall, s.false_hit_ids) == (4, 2, 0.5, ["K09"])
    over = ea.score_spots(spots, {"K10": 9})  # repeating a word does not buy more than the annotated spots
    assert over.recall == 1.0 and over.false_hit_ids == []
    assert ea.score_spots([], {"K01": 1}).recall is None


def _spotter(fuzzy: float = 90) -> ea.KeywordSpotter:
    ctx = Context(load_config("base", []), use_cache=False)
    fams = [
        Family(id="access", label="Zugang", keywords=[
            Keyword(id="K10", label="Zugangsdaten", de=["PIN", "Passwort", "Bestätigungscode", "TAN"]),
        ]),
        Family(id="trade", label="Insider", keywords=[
            Keyword(id="K03", label="Quartalszahlen", de=["Quartalszahlen"], gsw=["Quartalszahle"], enabled=False),
            Keyword(id="K04", label="vor der Meldung", de=["vor der Meldung"], gsw=["vor de Meldig"],
                    en=["before the announcement"]),
        ], enabled=False),
    ]
    return ea.KeywordSpotter(KeywordCheck(ctx, fuzzy=fuzzy), fams)


def seg(i: int, text: str) -> Segment:
    return Segment(id=f"S{i:03d}", start=float(i), end=float(i) + 1, text=text)


def test_spotter_uses_keyword_matcher_forms_and_fuzzy() -> None:
    sp = _spotter()
    segs = [seg(1, "Sie müend mir kei PIN und kei Passwort säge."),  # negated hits still count as spots
            seg(2, "Die Quartalszahle chömed vor de Meldig."),  # disabled keyword/family counted anyway
            seg(3, "Ich bi uf de Pinnwand und mini Tante"),  # whole tokens / acronyms: no PIN, no TAN
            seg(4, "Der neue Bestätigungskode gilt.")]  # fuzzy near-miss
    assert sp.count(segs) == Counter({"K10": 3, "K03": 1, "K04": 1})
    assert _spotter(fuzzy=100).count(segs)["K10"] == 2
    # English view: only the English forms
    assert sp.count([seg(1, "buy before the announcement, vor der Meldung")], lang="en") == Counter({"K04": 1})


def test_evaluate_call_recall_ceiling_and_timing(tmp_path: Path) -> None:
    calls = load_calls(_case(tmp_path))
    call = calls[0]
    t = Transcript(call_id=call.call_id, duration=100.0, meta={"elapsed_s": 2.0}, segments=[
        seg(1, "Grüezi, Sie müend mir kei PIN säge."), seg(2, "Ich säg Ihne d TAN: 7 3 1.")])
    row = ea.evaluate_call(call, t, _spotter())
    assert (row["kw_annotated"], row["kw_matched"], row["kw_recall"]) == (4, 2, 0.5)
    assert row["kw_ref_recall"] == 1.0  # the matcher finds all four on the script itself
    assert row["kw_missed_ids"] == "K10" and row["kw_false_hits"] == 0
    assert row["rtf"] == 0.02 and row["timing_source"] == "meta"
    t.meta = {}
    row = ea.evaluate_call(call, t, _spotter(), sweep={"seconds": 5.0, "audio_s": 99.0})
    assert row["rtf"] == 0.05 and row["timing_source"] == "sweep_log"


def test_load_sweep_timing_keeps_slowest(tmp_path: Path) -> None:
    log = tmp_path / "asr_sweep_x.jsonl"
    log.write_text("\n".join(json.dumps(r) for r in [
        {"call_id": "A", "seconds": 4.0, "audio_s": 100.0}, {"call_id": "A", "seconds": 0.01, "audio_s": 100.0},
        {"call_id": "B", "seconds": 1.0}]) + "\nnot json\n")
    assert ea.load_sweep_timing(log) == {"A": {"seconds": 4.0, "audio_s": 100.0}, "B": {"seconds": 1.0, "audio_s": 0.0}}
    assert ea.load_sweep_timing(tmp_path / "missing.jsonl") == {}


def test_summarize_groups_and_bootstrap() -> None:
    def row(dlg: str, noisy: bool, level: int, err: int, matched: int) -> dict:
        return {"dialogue_id": dlg, "noisy": noisy, "level": level, "ref_words": 10, "word_errors": err,
                "ref_chars": 50, "char_errors": err, "kw_annotated": 2, "kw_matched": matched, "kw_ref_matched": 2,
                "kw_false_hits": 0, "kw_annotated_ids": '{"K01": 2}', "kw_found_ids": json.dumps({"K01": matched}),
                "kw_ref_found_ids": '{"K01": 2}', "duration_s": 60.0, "asr_elapsed_s": 1.2}
    rows = [row("D1", False, 1, 1, 2), row("D1", True, 1, 3, 1), row("D2", False, 2, 2, 2), row("D2", True, 2, 4, 0)]
    s = ea.summarize(rows)
    g = s["groups"]
    assert g["all"]["wer"] == 0.25 and g["clean"]["wer"] == 0.15 and g["noisy"]["wer"] == 0.35
    assert g["clean"]["kw_recall"] == 1.0 and g["noisy"]["kw_recall"] == 0.25
    assert g["level1_noisy"]["n_calls"] == 1 and g["all"]["rtf"] == 0.02
    lo, hi = g["all"]["wer_ci95"]
    assert 0.15 <= lo <= 0.25 <= hi <= 0.35
    assert s["per_keyword"]["K01"] == {"annotated": 8, "matched": 5, "ref_matched": 8, "false_hit_calls": 0}


# -- cache reuse + CLI ----------------------------------------------------------------------------

HEADER = """D02 · Test
Testziel: access
Ereignis: present
Bearbeitung: alarm
Begründung: test
Offen: keine
Prüfpräfix bis T004; Belege: T004
{spots}

"""
SCRIPT = """T001 · Beratung
Grüezi. Sie müend mir kei PIN und kei Passwort säge.

T002 · Kundin
Da staht, de neu Bestätigungscode isch gültig.

T003 · Kundin
Ich säg Ihne die TAN grad: sibe, drü, eins.
"""


def _case(root: Path) -> Path:
    d = root / "data"
    for sub in ("Audio", "Transkript", "Skript_mit_Sollbewertung"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    for v, sec in ((1, 2.0), (2, 2.5)):
        sf.write(str(d / "Audio" / f"Stufe1_D02-K{v}.wav"), np.zeros(int(16000 * sec), dtype=np.float32), 16000)
    (d / "Transkript" / "Stufe1_D02.txt").write_text(SCRIPT, encoding="utf-8")
    (d / "Skript_mit_Sollbewertung" / "Stufe1_D02.txt").write_text(HEADER.format(spots=LINE_D05) + SCRIPT,
                                                                    encoding="utf-8")
    return d


def _overrides(tmp_path: Path) -> list[str]:
    return [f"paths.data_dir={_case(tmp_path)}", f"paths.cache_dir={tmp_path / 'cache'}",
            f"paths.runs_dir={tmp_path / 'runs'}", "llms.default.type=fake"]


def test_cached_lookup_uses_pipeline_transcribe_key(tmp_path: Path) -> None:
    """``--cached-only`` must find exactly what Pipeline.transcribe stored (pins the duplicated key)."""
    pipe = Pipeline(load_config("oracle", _overrides(tmp_path)))
    k1, k2 = load_calls(pipe.ctx.data_dir)
    assert ea.cached_transcript(pipe, k1) is None
    stored = pipe.transcribe(k1.audio_path, k1.call_id)
    hit = ea.cached_transcript(pipe, k1)
    assert hit is not None and hit.segments == stored.segments and hit.call_id == k1.call_id
    assert ea.transcript_for(pipe, k2, cached_only=True) is None


def test_cli_asr_eval_and_compare(tmp_path: Path) -> None:
    from callguard import cli  # here, not at module level: the other tests don't need the CLI
    sets = [x for o in _overrides(tmp_path) for x in ("--set", o)]
    pipe = Pipeline(load_config("oracle", _overrides(tmp_path)))
    k1 = load_calls(pipe.ctx.data_dir)[0]
    pipe.transcribe(k1.audio_path, k1.call_id)  # only K1 is cached
    runner = CliRunner()
    r = runner.invoke(cli.app, ["asr-eval", "-c", "oracle", *sets, "--cached-only", "--tag", "ora"])
    assert r.exit_code == 0, r.output
    out = tmp_path / "runs" / "asr_eval" / "ora"
    summary = json.loads((out / "summary.json").read_text())
    assert summary["meta"]["n_evaluated"] == 1 and summary["meta"]["skipped"] == ["Stufe1_D02-K2"]
    g = summary["groups"]["all"]
    assert g["wer"] == 0 and g["kw_recall"] == 1.0 and g["kw_spots"] == 4  # oracle ASR = the script
    assert "WER vs gsw script" in (out / "summary.md").read_text()
    assert (out / "per_call.csv").read_text().startswith("call_id,")

    r = runner.invoke(cli.app, ["asr-eval-compare", "ora", "nope", "--root", str(tmp_path / "runs" / "asr_eval")])
    assert r.exit_code == 0, r.output
    assert "| ora | 1 | 0.0%" in r.output and "| nope | missing" in r.output
