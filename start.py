"""Startet die App auf Windows, Linux und macOS: Transkriptions-Dienst, Fraud-Analyse-Dienst und Dashboard.

  python start.py             # Dashboard auf http://localhost:7860
  python start.py --analyse   # zusätzlich die Entwickler-Oberfläche auf http://localhost:7861

Erkennt das Betriebssystem und nimmt das Python aus .venv (Windows: .venv\\Scripts\\python.exe, sonst .venv/bin/python),
sonst das Python, mit dem dieses Skript läuft. Alle Teile laufen in diesem Terminal, jede Zeile mit dem Namen des Teils
davor. Ctrl+C beendet alle. Nur Standardbibliothek: läuft auch mit einem Python ohne die Projektpakete.
Bequemer: .\\start.ps1 (Windows) bzw. ./start.sh (Linux, macOS) rufen dieses Skript auf.
"""
import argparse
import os
import platform
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTS = [  # (Name, Modul, URL zum Prüfen, ob er läuft)
    ("transkription", "transcription.api", "http://127.0.0.1:8001/health"),
    ("fraud-analyse", "fraud_analysis.api", "http://127.0.0.1:8002/health"),
    ("dashboard", "dashboard.app", "http://127.0.0.1:7860/"),
]
ANALYSE = ("analyse-ui", "misc.analysis_ui.app", "http://127.0.0.1:7861/")
WINDOWS = platform.system() == "Windows"


def venv_python():
    """Python aus .venv passend zum Betriebssystem, sonst das aktuelle."""
    candidate = ROOT / ".venv" / ("Scripts/python.exe" if WINDOWS else "bin/python")
    return str(candidate) if candidate.is_file() else sys.executable


def relay(name, proc):
    """Gibt die Ausgabe eines Teils zeilenweise mit Namen davor aus."""
    for line in iter(proc.stdout.readline, ""):
        print(f"[{name:<13}] {line.rstrip()}", flush=True)


def up(url):
    try:
        with urllib.request.urlopen(url, timeout=2):
            return True
    except Exception:
        return False


def main():
    if WINDOWS: sys.stdout.reconfigure(encoding="utf-8")   # Umlaute in der Windows-Konsole, auch in --help
    ap = argparse.ArgumentParser(description="Startet Transkription, Fraud-Analyse und Dashboard.")
    ap.add_argument("--analyse", action="store_true", help="zusätzlich die Entwickler-Oberfläche (Port 7861) starten")
    args = ap.parse_args()

    python = venv_python()
    parts = PARTS + ([ANALYSE] if args.analyse else [])
    print(f"System: {platform.system()} {platform.machine()} · Python: {python}", flush=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    procs = []
    for name, module, _ in parts:
        p = subprocess.Popen([python, "-m", module], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace",
                             # eigene Prozessgruppe: Ctrl+C beendet die Teile kontrolliert über stop()
                             **({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if WINDOWS else {"start_new_session": True}))
        threading.Thread(target=relay, args=(name, p), daemon=True).start()
        procs.append((name, p))

    def stop(*_):
        print("\nBeende alle Teile …", flush=True)
        for _, p in procs:
            if p.poll() is None: p.terminate()
        for _, p in procs:
            try: p.wait(timeout=10)
            except subprocess.TimeoutExpired: p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGBREAK if WINDOWS else signal.SIGTERM, stop)   # Ctrl+Break bzw. kill

    pending = {name: url for name, _, url in parts}
    deadline = time.time() + 180
    while pending and time.time() < deadline:
        for name, p in procs:
            if p.poll() is not None:
                print(f"\n[{name}] ist beendet (Code {p.returncode}). Siehe Ausgabe oben.", flush=True)
                stop()
        for name in [n for n, url in pending.items() if up(url)]:
            pending.pop(name)
        time.sleep(1)
    if pending:
        print(f"\nNoch nicht erreichbar nach 3 min: {', '.join(pending)}. Siehe Ausgabe oben.", flush=True)
    else:
        print("\n" + "=" * 60 + "\nBereit. Dashboard: http://localhost:7860"
              + ("\nAnalyse-UI:  http://localhost:7861" if args.analyse else "")
              + "\nDie Modelle laden bei der ersten Prüfung. Beenden: Ctrl+C\n" + "=" * 60, flush=True)
    while True:   # wartet, bis Ctrl+C kommt oder ein Teil abstürzt
        for name, p in procs:
            if p.poll() is not None:
                print(f"\n[{name}] ist beendet (Code {p.returncode}).", flush=True)
                stop()
        time.sleep(1)


if __name__ == "__main__":
    main()
