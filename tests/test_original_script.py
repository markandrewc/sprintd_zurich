"""The Swiss German original script in the demo player: DISPLAY ONLY (CLAUDE.md rule 2).

* loaders: test50's timed script (times from the test data), the case script timed by alignment to the ASR
  segments (monotonic, covers the call), new calls without a script;
* label hygiene: the loader reads ``Transkript*/`` only, never ``Skript_mit_Sollbewertung/``; the alignment
  module reads no labels; the demo / pipeline never import the label-reading evidence evaluation;
* the switch: both views rendered and synchronised by the same rules, the disabled state, deep link view;
* the pipeline never reads these files (a whole offline chain with the script folders made unreadable).
"""

from __future__ import annotations

import builtins
import importlib.util
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from streamlit.testing.v1 import AppTest
from ui_fixtures import ALARM_ID, HARMLESS_ID, write_fixture_env

from callguard import audio as audio_mod
from callguard import registry
from callguard.config import load_config
from callguard.demo import original_script as osc
from callguard.demo.transcript import VIEW_CH, VIEW_DE, player_html
from callguard.pipeline import Pipeline
from callguard.plugins import ASRBackend
from callguard.types import Passage, Segment, Transcript
from callguard.ui import backend as be

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "src" / "callguard" / "demo" / "app.py"

CASE_SCRIPT = """T001 · Beratung
Grüezi Frau Aebi, da isch d Claudia Frei. Sie händ um en Rückruf wäge Ihrem Wertschriftedepot bätte.

T002 · Kundin
Öppe achttuusig Franke. Mini Schwöschter schaffet det i de Finanzabteilig. D Quartalszahle sind no nöd publiziert.

T003 · Beratung
Sie händ das direkt vo Ihrer Schwöschter, nöd us ere öffentliche Meldig?

T004 · Kundin
Grad drum möcht ich d Aktie jetzt chaufe, vor de Meldig.

T005 · Beratung
De Uftrag nimm ich so nöd entgäge. Ich gib de Vorgang intern zur Klärig wiiter.
"""

SEGMENTS = [
    Segment(id="S001", start=0.4, end=6.0, role="advisor",
            text="Grüezi Frau Aebi, hier ist Claudia Frei. Sie haben um einen Rückruf wegen Ihres Wertschriftendepots gebeten."),
    Segment(id="S002", start=6.5, end=11.0, role="customer", text="Etwa achttausend Franken."),
    Segment(id="S003", start=11.2, end=19.0, role="customer",
            text="Meine Schwester arbeitet in der Finanzabteilung. Die Quartalszahlen sind noch nicht publiziert."),
    Segment(id="S004", start=19.5, end=24.0, role="advisor",
            text="Sie haben das direkt von Ihrer Schwester, nicht aus einer öffentlichen Meldung?"),
    Segment(id="S005", start=24.5, end=30.0, role="customer", text="Gerade darum möchte ich die Aktie jetzt kaufen, vor der Meldung."),
    Segment(id="S006", start=30.5, end=37.0, role="advisor",
            text="Den Auftrag nehme ich so nicht entgegen. Ich gebe den Vorgang intern zur Klärung weiter."),
]

TIMED = {"timing": "test_data", "turns": [
    {"id": "T002", "speaker": "Kundin", "start": 7.1, "end": 13.8, "text": "Jo, guete Daag. D Zahlig bliibt hange."},
    {"id": "T001", "speaker": "Beratung", "start": 0.25, "end": 6.49, "text": "Güeten Tag Fröi Marti."},
    {"id": "T003", "speaker": "Beratung", "start": 14.6, "end": 16.3, "text": "Was gsehnt Ier de ufum Bildschirm?"},
]}


def _wav(path: Path, seconds: float = 40.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(seconds * audio_mod.SR)) / audio_mod.SR
    sf.write(str(path), (0.05 * np.sin(2 * np.pi * 200 * t)).astype(np.float32), audio_mod.SR, subtype="PCM_16")
    return path


def _dataset(root: Path, dialogue: str = "Stufe1_D02", timed: bool = False) -> Path:
    data = root / "data"
    _wav(data / "Audio" / f"{dialogue}-K1.wav")
    (data / "Transkript").mkdir(parents=True, exist_ok=True)
    (data / "Transkript" / f"{dialogue}.txt").write_text(CASE_SCRIPT, encoding="utf-8")
    if timed:
        (data / "Transkript_CH_timed").mkdir(parents=True, exist_ok=True)
        (data / "Transkript_CH_timed" / f"{dialogue}.json").write_text(json.dumps(TIMED), encoding="utf-8")
    lab = data / "Skript_mit_Sollbewertung" / f"{dialogue}.txt"
    lab.parent.mkdir(parents=True, exist_ok=True)
    lab.write_text("Testziel: trade\nBearbeitung: alarm\nBelege: T002, T004\n\n" + CASE_SCRIPT, encoding="utf-8")
    return data


def _transcript(audio: Path | None = None) -> Transcript:
    return Transcript(call_id="Stufe1_D02-K1", audio_path=str(audio) if audio else None, duration=38.0,
                      segments=[s.model_copy() for s in SEGMENTS])


@pytest.fixture
def reads(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every path opened through open / io.open / Path.open while the test runs."""
    seen: list[str] = []
    real_open, real_path_open = builtins.open, Path.open

    def spy_open(file, *a, **k):
        seen.append(str(file))
        return real_open(file, *a, **k)

    def spy_path_open(self, *a, **k):
        seen.append(str(self))
        return real_path_open(self, *a, **k)

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(io, "open", spy_open)
    monkeypatch.setattr(Path, "open", spy_path_open)
    return seen


# --------------------------------------------------------------------------------------------
# loaders
# --------------------------------------------------------------------------------------------


def test_test50_timed_script_wins_and_keeps_the_test_data_times(tmp_path: Path, reads: list[str]):
    data = _dataset(tmp_path, "T50-access-01-A", timed=True)
    k2 = _wav(data / "Audio" / "T50-access-01-A-K2.wav")  # the noisy twin shares the clean one's script
    reads.clear()
    for audio in (data / "Audio" / "T50-access-01-A-K1.wav", k2):
        s = osc.load(audio.stem, str(audio), _transcript(audio))
        assert s is not None and s.timing == "test_data" and s.dialogue_id == "T50-access-01-A"
        assert [t.id for t in s.turns] == ["T001", "T002", "T003"]  # sorted by start
        assert (s.turns[0].start, s.turns[0].end, s.turns[0].role) == (0.25, 6.49, "advisor")
        assert s.turns[1].role == "customer" and "Zeiten: aus den Testdaten" in s.note
        assert "nicht von Sherlock Phones erzeugt und nicht von der KI ausgewertet" in s.note
    assert not [p for p in reads if "Skript_mit_Sollbewertung" in p]


def test_import_copies_only_text_and_times_of_the_test50_json():
    spec = importlib.util.spec_from_file_location("import_test50", ROOT / "scripts" / "data" / "import_test50.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    meta = {"expected": "alarm", "facts": {"x": 1}, "belege": ["T001"], "turns": [
        {"id": "T001", "speaker": "Beratung", "dialect": "Valais", "de": "Guten Tag", "ch_auto": "Guete Tag",
         "ch_final": "Güeten Tag", "decisive": True, "start": 0.25, "end": 6.4861,
         "sentences": [{"de": "Guten Tag", "ch_final": "Güeten Tag", "key": True, "start": 0.25, "end": 6.4861}]}]}
    out = mod.timed_turns(meta)
    assert set(out) == {"source", "timing", "turns"}
    assert out["turns"] == [{"id": "T001", "speaker": "Beratung", "dialect": "Valais", "start": 0.25, "end": 6.486,
                             "text": "Güeten Tag", "sentences": [{"start": 0.25, "end": 6.486, "text": "Güeten Tag"}]}]


def test_case_script_is_timed_by_monotonic_alignment_that_covers_the_call(tmp_path: Path, reads: list[str]):
    data = _dataset(tmp_path)
    audio = data / "Audio" / "Stufe1_D02-K1.wav"
    reads.clear()
    s = osc.load("Stufe1_D02-K1", str(audio), _transcript(audio))
    assert s is not None and s.timing == "aligned" and "±1 Satz" in s.note
    assert [t.id for t in s.turns] == ["T001", "T002", "T003", "T004", "T005"]
    starts = [t.start for t in s.turns]
    assert starts == sorted(starts) and all(t.end >= t.start for t in s.turns)
    assert s.turns[0].start == SEGMENTS[0].start and s.turns[-1].end == SEGMENTS[-1].end  # covers the call
    by = {t.id: t for t in s.turns}
    assert (by["T002"].start, by["T002"].end) == (6.5, 19.0)  # both customer segments
    assert (by["T004"].start, by["T004"].end) == (24.5, 30.0)
    assert not [p for p in reads if "Skript_mit_Sollbewertung" in p]
    assert any(p.endswith("Transkript/Stufe1_D02.txt") for p in reads)


def test_new_call_has_no_original_script(tmp_path: Path):
    data = _dataset(tmp_path)
    upload = _wav(tmp_path / "runs" / "uploads" / "Stufe1_D02-K1.wav")  # same name, but not a test recording
    assert osc.load("Stufe1_D02-K1", str(upload), _transcript(upload), [data]) is None
    assert osc.load("anruf-2026-10-10", None, _transcript(), [data]) is None
    # recording not on this machine (results from the GPU host): the configured data folder is tried
    assert osc.load("Stufe1_D02-K1", "/elsewhere/Audio/Stufe1_D02-K1.wav", _transcript(), [data]).timing == "aligned"
    assert osc.load("../../etc/passwd", None, _transcript(), [data]) is None


def test_label_hygiene_of_the_loader_and_the_alignment_module():
    for mod in ("align.py", "normalize.py", "demo/original_script.py"):
        src = (ROOT / "src" / "callguard" / mod).read_text(encoding="utf-8")
        code = src.split('"""', 2)[-1]  # the docstring may name what is NOT read
        assert not re.search(r"Skript_mit_Sollbewertung|parse_expected|load_calls|\.expected\b|evidence_turns|"
                             r"eval_evidence|eval_asr", code), mod
    # importing the demo's player (and the call page's helpers) never loads the label-reading evaluation
    probe = ("import sys, callguard.demo.transcript, callguard.demo.original_script, callguard.pipeline;"
             "print('callguard.eval_evidence' in sys.modules, 'callguard.eval_asr' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, check=True).stdout.split()
    assert out == ["False", "False"]


# --------------------------------------------------------------------------------------------
# the switch
# --------------------------------------------------------------------------------------------


def _script() -> osc.OriginalScript:
    return osc.OriginalScript("Stufe1_D02", [
        osc.DialectTurn("T001", "Beratung", "advisor", 0.4, 6.0, "Grüezi <b>Frau</b> Aebi"),
        osc.DialectTurn("T002", "Kundin", "customer", 6.5, 19.0, "Öppe achttuusig Franke."),
        osc.DialectTurn("T003", "Beratung", "advisor", 19.5, 24.0, "Sie händ das direkt?", aligned=False),
        osc.DialectTurn("T004", "Kundin", "customer", 24.5, 30.0, "Grad drum möcht ich chaufe."),
    ], "aligned", "x")


def test_switch_renders_both_views_synchronised_with_passages():
    passages = [Passage(family="trade", family_label="Insiderhandel", start=24.5, end=30.0, segment_ids=["S005"],
                        score=0.9)]
    doc = player_html(_transcript(), passages, audio_src="data:audio/mpeg;base64,AAAA", colors={"trade": "#d64a2a"},
                      labels={"trade": "Insiderhandel"}, start_at=11.1, original=_script())
    assert VIEW_DE in doc and VIEW_CH in doc and "disabled" not in doc.split("<script>")[0].split("cg-views")[2]
    assert re.findall(r'id="ch-(T\d+)"', doc) == ["T001", "T002", "T003", "T004"]
    assert re.findall(r'id="seg-(S\d+)"', doc) == [s.id for s in SEGMENTS]
    # same highlight rule in both panes: 11.1 s is the S002/S003 pause -> S003; in the script T002
    assert re.search(r'class="[^"]*is-current[^"]*" id="seg-S003"', doc)
    assert re.search(r'class="[^"]*is-current[^"]*" id="ch-T002"', doc)
    # passage marker on the overlapping script turn only
    assert re.search(r'id="ch-T004"[^>]*--fam:#d64a2a', doc) and not re.search(r'id="ch-T002"[^>]*--fam', doc)
    assert re.search(r'id="ch-T004".*?Passage 1 · Insiderhandel', doc, re.S)
    assert 'data-start="24.50"' in doc and "Zeit geschätzt" in doc
    # honest label, escaped text, ASR pane shown first, the dialect pane hidden
    assert "nicht von der KI ausgewertet" in doc and "per Ausrichtung an das KI-Transkript, ±1 Satz" in doc
    assert "&lt;b&gt;Frau&lt;/b&gt;" in doc and "<b>Frau</b>" not in doc
    assert re.search(r'class="cg-transcript" data-view="ch" hidden', doc)
    assert re.search(r'id="cg-transcript" data-view="de">', doc) and 'id="cg-orignote" hidden' in doc
    cfg = json.loads(re.search(r'data-config="([^"]*)"', doc).group(1).replace("&quot;", '"'))
    assert cfg["view"] == "de" and cfg["hasOriginal"] is True
    # deep link ?ansicht=ch: the script pane first
    doc = player_html(_transcript(), passages, audio_src=None, original=_script(), view="ch")
    assert re.search(r'id="cg-transcript" data-view="de" hidden>', doc) and 'id="cg-orignote">' in doc
    assert re.search(r'class="cg-view is-on" data-view="ch"', doc)


def test_switch_without_script_is_disabled_and_says_why():
    doc = player_html(_transcript(), [], audio_src=None, original=None, view="ch")
    assert re.search(r'data-view="ch" disabled aria-disabled="true"', doc)
    body = doc.split("<body>")[1].split("<script>")[0]
    assert osc.NO_SCRIPT_DE in body and 'class="cg-transcript" data-view="ch"' not in body and "cg-orignote" not in body
    assert re.search(r'class="cg-view is-on" data-view="de"', doc)
    cfg = json.loads(re.search(r'data-config="([^"]*)"', doc).group(1).replace("&quot;", '"'))
    assert cfg["view"] == "de" and cfg["hasOriginal"] is False


def test_turns_in_maps_passages_by_time():
    turns = _script().turns
    assert osc.turns_in(turns, 7.0, 20.0) == ["T002", "T003"]
    assert osc.turns_in(turns, 6.0, 6.5) == ["T001"]  # touching only -> the nearest one
    assert osc.turns_in([], 1, 2) == []


def _iframes(at: AppTest) -> list[str]:
    out, stack = [], list(at.main)
    while stack:
        node = stack.pop()
        proto = getattr(node, "proto", None)
        if proto is not None and getattr(proto, "srcdoc", "") and proto.srcdoc not in out:
            out.append(proto.srcdoc)
        children = getattr(node, "children", None)
        if isinstance(children, dict):
            stack += list(children.values())
    return out


def test_call_page_offers_the_script_for_test_calls_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env = write_fixture_env(tmp_path)
    (env.data_dir / "Transkript" / f"{ALARM_ID.split('-K')[0]}.txt").write_text(CASE_SCRIPT, encoding="utf-8")
    monkeypatch.setenv(be.ENV_ARGS, env.args)
    for cid, available in ((ALARM_ID, True), (HARMLESS_ID, False)):
        at = AppTest.from_file(str(APP), default_timeout=120)
        at.query_params["call"] = cid
        at.query_params["ansicht"] = "ch"
        at.run()
        assert not at.exception, [e.message for e in at.exception]
        docs = [d for d in _iframes(at) if "cg-views" in d]
        assert len(docs) == 1, cid
        doc = docs[0]
        if available:
            assert re.search(r'class="cg-view is-on" data-view="ch"', doc) and 'id="ch-T001"' in doc
            assert "Zeiten: per Ausrichtung an das KI-Transkript" in doc
        else:
            assert 'disabled aria-disabled="true"' in doc and osc.NO_SCRIPT_DE in doc and 'id="ch-' not in doc


# --------------------------------------------------------------------------------------------
# the pipeline never reads the scripts
# --------------------------------------------------------------------------------------------


@registry.register("asr", "test_origscript_asr")
class _FixedASR(ASRBackend):
    def transcribe(self, audio_path: Path, call_id: str) -> Transcript:
        return Transcript(call_id=call_id, audio_path=str(audio_path), duration=38.0,
                          segments=[s.model_copy() for s in SEGMENTS], asr_backend="test")


def test_pipeline_never_reads_the_original_scripts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reads: list[str]):
    data = _dataset(tmp_path, timed=True)
    cfg = load_config("demo-offline", [f"paths.runs_dir={tmp_path}/runs", f"paths.cache_dir={tmp_path}/cache",
                                       f"paths.data_dir={data}", "asr.type=test_origscript_asr", "diarizer.type=none"])
    forbidden = ("Transkript", "Skript_mit_Sollbewertung")
    real_read_text = Path.read_text

    def guarded_read_text(self, *a, **k):
        if any(f in Path(self).parts or any(p.startswith(f) for p in Path(self).parts) for f in forbidden):
            raise PermissionError(f"pipeline must not read {self}")
        return real_read_text(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    reads.clear()
    r = Pipeline(cfg).process(data / "Audio" / "Stufe1_D02-K1.wav", "Stufe1_D02-K1")
    assert r.transcript.asr_backend == "test" and r.decision.label in ("alarm", "review", "no_alert")
    assert set(r.checks) >= {"keywords", "patterns", "llm_judge", "geval"}
    assert not any(c.meta.get("error") for c in r.checks.values())
    touched = [p for p in reads if any(f in p for f in forbidden)]
    assert touched == []
    blob = r.model_dump_json()
    assert "achttuusig" not in blob and "Schwöschter" not in blob  # no dialect text in the result
