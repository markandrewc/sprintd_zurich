"""Results made on the GPU host carry that host's absolute paths; the UI re-roots them onto this checkout."""
from pathlib import Path

from callguard.ui.backend import reroot


def test_reroot_finds_trailing_part_under_base(tmp_path: Path) -> None:
    wav = tmp_path / "data_upstream" / "case" / "Audio" / "a.wav"
    wav.parent.mkdir(parents=True)
    wav.write_bytes(b"RIFF")
    foreign = "/home/other/repos/sprintd/data_upstream/case/Audio/a.wav"
    assert reroot(foreign, base=tmp_path) == str(wav)


def test_reroot_keeps_existing_and_unknown_paths(tmp_path: Path) -> None:
    here = tmp_path / "x.wav"
    here.write_bytes(b"RIFF")
    assert reroot(str(here), base=tmp_path) == str(here)
    assert reroot("/nowhere/at/all.wav", base=tmp_path) == "/nowhere/at/all.wav"
    assert reroot(None) is None
