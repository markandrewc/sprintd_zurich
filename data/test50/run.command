#!/bin/bash
# Double-click start for the sprintd test50 build (FHNW STT4SG TTS, non-commercial test data).
# Runs make_calls.py in this folder; caffeinate keeps the Mac awake. Safe to rerun: everything is cached.
cd "$(dirname "$0")" || exit 1
echo "sprintd test50 – FHNW TTS build – $(date)"
echo "Log: logs/progress.log  ·  stop with Ctrl+C, rerun to resume"
echo
caffeinate -i python3 make_calls.py --wait-review "$@"
status=$?
echo
echo "Fertig (Exit $status). 0 = alles gebaut, 3 = Sätze warten auf needs_review.csv, 2 = API-Fehler."
read -n 1 -s -r -p "Taste drücken zum Schliessen …"
echo
