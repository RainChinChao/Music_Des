#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT/data/gui.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "GenAI MIDI Studio is not running (no PID file)."
  sleep 2
  exit 0
fi

PID="$(tr -cd '0-9' < "$PID_FILE")"
if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  for _ in {1..20}; do
    kill -0 "$PID" 2>/dev/null || break
    sleep 0.25
  done
  echo "GenAI MIDI Studio stopped."
else
  echo "GenAI MIDI Studio was already stopped."
fi
rm -f "$PID_FILE"
sleep 2
