"""
Delta-Finetuning von Kev-4B auf unseren Daten mit kev.train aus github.com/jaredpalmer/kev (im .venv installiert, siehe
requirements.txt). Startet vom fertigen jaredpalmer/kev-4b (LoRA + Pointer-Head) und trainiert auf
outputs/finetuning/kev_train.jsonl weiter, damit Kev sein allgemeines Können behält und unsere Fakten dazulernt.

  python -m finetuning.train                        # Daten bauen und trainieren -> outputs/finetuning/runs/<zeit>
  python -m finetuning.train --epochs 3 --name v1   # eigene Einstellungen
  python -m finetuning.train --max_steps 2          # Kurztest: läuft es, passt es in den Speicher?

Danach vergleichen: python -m finetuning.evaluate outputs/finetuning/runs/<name>
Im Einsatz verwenden: den Fraud-Dienst mit KEV_MODEL=outputs/finetuning/runs/<name> starten.

Speicher: Für eine 12-GB-Karte läuft das Basismodell in bf16 (--weights_dtype bf16) mit Gradient-Checkpointing, einem
Beispiel pro Schritt und höchstens --row_budget Tokens pro Durchlauf. Die GPU muss dafür frei sein (keine Prüfung im
Dashboard während des Trainings).
"""
import argparse
import os
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "outputs" / "finetuning" / "runs"
INIT = "jaredpalmer/kev-4b"


def windows_stubs():
    """kev.train importiert resource und fcntl (gibt es nur unter Linux/macOS). Sie dienen dort nur der Statistik am Ende
    (Speicherspitze) und einer Dateisperre für Suites, die wir nicht nutzen; unter Windows reichen Platzhalter."""
    if os.name != "nt": return
    if "resource" not in sys.modules:
        r = types.ModuleType("resource")
        r.RUSAGE_SELF, r.RLIMIT_CORE = 0, 4
        r.getrusage = lambda who: types.SimpleNamespace(ru_maxrss=0)
        r.setrlimit = lambda *a: None
        sys.modules["resource"] = r
    if "fcntl" not in sys.modules:
        f = types.ModuleType("fcntl")
        f.LOCK_EX, f.LOCK_UN = 2, 8
        f.flock = lambda *a: None
        sys.modules["fcntl"] = f


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default=time.strftime("%Y%m%d-%H%M"), help="Name des Laufs (Ordner unter outputs/finetuning/runs)")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--lr", type=float, default=2e-5, help="Lernrate (Kevs Empfehlung fürs Delta-Training: 2e-5)")
    ap.add_argument("--accum", type=int, default=8, help="Beispiele pro Optimierungsschritt")
    ap.add_argument("--max_state", type=int, default=2048, help="Tokens pro Gespräch; längere Gespräche werden übersprungen")
    ap.add_argument("--row_budget", type=int, default=2048, help="Tokens pro Vorwärts-/Rückwärtsdurchlauf: Kev rechnet die "
                    "Fragen eines Gesprächs in Gruppen statt alle auf einmal (alle 15 zusammen sprengen 12 GB)")
    ap.add_argument("--max_steps", type=int, default=0, help="nach so vielen Schritten aufhören (0 = alle Epochen)")
    ap.add_argument("--skip_build", action="store_true", help="vorhandene outputs/finetuning/kev_train.jsonl verwenden")
    a = ap.parse_args()

    from finetuning.build_dataset import OUT, build
    train_file = OUT / "kev_train.jsonl" if a.skip_build else build()[0]
    out = RUNS / a.name
    windows_stubs()
    from kev.checkpoint import Checkpoint
    from kev import train
    meta = Checkpoint(INIT).meta   # Architektur des Warmstarts: muss exakt passen, sonst bricht kev.train ab
    sys.argv = ["kev.train", "--data", str(train_file), "--init_from", INIT, "--out", str(out),
                "--base", meta.base, "--base_revision", meta.base_revision, "--lora", str(meta.lora), "--lora_targets", "all",
                "--head_dim", str(meta.head_dim), "--lr", str(a.lr), "--epochs", str(a.epochs), "--batch", "1",
                "--accum", str(a.accum), "--dtype", "bf16", "--weights_dtype", "bf16", "--checkpointing", "1",
                "--max_state", str(a.max_state), "--row_budget", str(a.row_budget), "--max_steps", str(a.max_steps), "--device", "cuda",
                # keine automatischen Zusatz- oder Störoptionen: unsere Fragen sind Ja/Nein und sollen so bleiben
                "--p_none", "0", "--p_none_distract", "0", "--p_distract", "0"]
    print("kev.train " + " ".join(sys.argv[1:]), flush=True)
    train.main()
    print(f"\nFertig: {out}\nVergleichen: python -m finetuning.evaluate {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
