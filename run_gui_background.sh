#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/data"
PID_FILE="$ROOT/data/gui.pid"
GUI_LOG="$ROOT/data/gui_background.log"

for candidate in /opt/homebrew/bin /usr/local/bin /opt/anaconda3/bin \
                 "$HOME/anaconda3/bin" "$HOME/miniconda3/bin"; do
  [[ -d "$candidate" ]] && PATH="$candidate:$PATH"
done
export PATH

if ! command -v conda >/dev/null 2>&1; then
  echo "Conda was not found. Run INSTALL_AND_RUN.command first."
  exit 1
fi
eval "$(conda shell.bash hook)"
if ! conda env list | awk '{print $1}' | grep -qx genai-midi; then
  echo "The genai-midi environment is missing. Run INSTALL_AND_RUN.command first."
  exit 1
fi
conda activate genai-midi
PYTHON="$CONDA_PREFIX/bin/python"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(tr -cd '0-9' < "$PID_FILE")"
  if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    URL="$(grep -Eo 'http://localhost:[0-9]+' "$GUI_LOG" | tail -1 || true)"
    if [[ -n "$URL" ]] && curl -fsS "$URL/_stcore/health" >/dev/null 2>&1; then
      open "$URL"
      echo "Opened existing GUI: $URL"
      exit 0
    fi
  fi
fi

: > "$GUI_LOG"
PYTHONUNBUFFERED=1 nohup "$PYTHON" -m deterministic_midi.gui_launcher \
  >> "$GUI_LOG" 2>&1 </dev/null &
GUI_PID=$!
echo "$GUI_PID" > "$PID_FILE"

for _ in {1..120}; do
  URL="$(grep -Eo 'http://localhost:[0-9]+' "$GUI_LOG" | tail -1 || true)"
  if [[ -n "$URL" ]] && curl -fsS "$URL/_stcore/health" >/dev/null 2>&1; then
    open "$URL"
    echo "Started GUI: $URL"
    exit 0
  fi
  if ! kill -0 "$GUI_PID" 2>/dev/null; then
    echo "The GUI stopped during startup. Inspect $GUI_LOG"
    tail -80 "$GUI_LOG"
    exit 1
  fi
  sleep 0.25
done

echo "The GUI did not become ready within 30 seconds. Inspect $GUI_LOG"
exit 1
