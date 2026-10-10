#!/usr/bin/env bash
# Startet die App (Linux, macOS; auch Git Bash unter Windows): Transkription, Fraud-Analyse, Dashboard.
#   ./start.sh             # Dashboard auf http://localhost:7860
#   ./start.sh --analyse   # zusätzlich die Entwickler-Oberfläche auf http://localhost:7861
# Die eigentliche Logik steht in start.py; Ctrl+C beendet alle Teile.
cd "$(dirname "$0")" || exit 1
for py in .venv/bin/python .venv/Scripts/python.exe python3 python; do
    if command -v "$py" >/dev/null 2>&1 || [ -x "$py" ]; then exec "$py" start.py "$@"; fi
done
echo "Kein Python gefunden. Bitte zuerst die Installation aus README.md ausführen." >&2
exit 1
