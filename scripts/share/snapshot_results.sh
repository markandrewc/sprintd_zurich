#!/usr/bin/env bash
# Copy a runs/ tree into a shareable results snapshot: every summary / rows / metrics / meta / spec as is,
# results.jsonl gzipped, per-call result.json of profile runs, no audio (wav/ogg/mp3), no caches, no models.
# Usage: scripts/share/snapshot_results.sh <runs_dir> <out_dir>      (run once per machine, same <out_dir> merges)
set -euo pipefail
SRC="$1"; OUT="$2"
mkdir -p "$OUT"
cd "$SRC"
find . -type f \( -name "*.json" -o -name "*.md" -o -name "*.yaml" -o -name "*.csv" -o -name "*.jsonl" -o -name "*.txt" -o -name "*.png" \) \
  ! -path "*/snippets/*" ! -name "*.wav" ! -path "./logs/*" -print0 |
while IFS= read -r -d '' f; do
  mkdir -p "$OUT/$(dirname "$f")"
  case "$f" in
    *results.jsonl) gzip -9c "$f" > "$OUT/$f.gz" ;;
    *) cp -p "$f" "$OUT/$f" ;;
  esac
done
echo "snapshot of $SRC -> $OUT: $(du -sh "$OUT" | cut -f1)"
