#!/usr/bin/env bash
# Run a command after a marker line appears in a file. Usage: after.sh <file> <marker> <command...>
f=$1; m=$2; shift 2
until grep -q "$m" "$f" 2>/dev/null; do sleep 10; done
exec "$@"
