#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/data"
LOG="$ROOT/data/install_and_run.log"
exec > >(tee -a "$LOG") 2>&1

echo "============================================================"
echo " GenAI MIDI Studio — install (when needed) and run"
echo " Project: $ROOT"
echo " Log: $LOG"
echo "============================================================"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This launcher is for macOS."
  read -r -p "Press Return to close..." _
  exit 1
fi

# Finder-launched .command files may not inherit the interactive shell PATH.
for candidate in /opt/homebrew/bin /usr/local/bin /opt/anaconda3/bin \
                 "$HOME/anaconda3/bin" "$HOME/miniconda3/bin"; do
  [[ -d "$candidate" ]] && PATH="$candidate:$PATH"
done
export PATH

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required. Install it from https://brew.sh and double-click this file again."
  open "https://brew.sh" || true
  read -r -p "Press Return to close..." _
  exit 1
fi
if ! command -v conda >/dev/null 2>&1; then
  echo "Anaconda or Miniconda is required. Install it and double-click this file again."
  open "https://www.anaconda.com/download" || true
  read -r -p "Press Return to close..." _
  exit 1
fi

eval "$(conda shell.bash hook)"

# Repair only this application's config directory if an earlier sudo command
# created it with the wrong owner. No broad home-directory ownership change.
CONFIG_DIR="$HOME/.config/deterministic-midi"
if ! mkdir -p "$CONFIG_DIR" 2>/dev/null || [[ ! -w "$CONFIG_DIR" ]]; then
  echo "macOS permission repair is required for $CONFIG_DIR"
  sudo mkdir -p "$CONFIG_DIR"
  sudo chown -R "$(id -u):$(id -g)" "$CONFIG_DIR"
  sudo chmod -R u+rwX "$CONFIG_DIR"
fi

MARKER="$ROOT/.genai-midi-installation-v8.1-complete"
if [[ ! -f "$MARKER" ]] || ! conda env list | awk '{print $1}' | grep -qx genai-midi; then
  echo "Running first-time comprehensive installation..."
  chmod +x "$ROOT/setup_macos.sh"
  "$ROOT/setup_macos.sh"
  touch "$MARKER"
else
  echo "Existing installation detected; skipping large downloads."
fi

conda activate genai-midi
PYTHON="$CONDA_PREFIX/bin/python"

# Always refresh the editable package so launcher/source updates take effect.
"$PYTHON" -m pip install -e '.[all]'
"$PYTHON" -c 'from pathlib import Path; from deterministic_midi.memory import ensure_learning_files; print("Learning files:", ensure_learning_files(Path.cwd() / "data"))'

brew services start ollama >/dev/null 2>&1 || true
chmod +x "$ROOT/run_gui_background.sh" "$ROOT/STOP_GENAI_MIDI.command"
if command -v osacompile >/dev/null 2>&1; then
  rm -rf "$ROOT/OPEN_GENAI_MIDI.app" "$ROOT/STOP_GENAI_MIDI.app"
  osacompile -o "$ROOT/OPEN_GENAI_MIDI.app" "$ROOT/OPEN_GENAI_MIDI.applescript"
  osacompile -o "$ROOT/STOP_GENAI_MIDI.app" "$ROOT/STOP_GENAI_MIDI.applescript"
  printf '%s' "$ROOT" > "$ROOT/OPEN_GENAI_MIDI.app/Contents/Resources/project_root.txt"
  printf '%s' "$ROOT" > "$ROOT/STOP_GENAI_MIDI.app/Contents/Resources/project_root.txt"
  xattr -dr com.apple.quarantine "$ROOT/OPEN_GENAI_MIDI.app" "$ROOT/STOP_GENAI_MIDI.app" 2>/dev/null || true
  echo "Created hidden launchers:"
  echo "  $ROOT/OPEN_GENAI_MIDI.app"
  echo "  $ROOT/STOP_GENAI_MIDI.app"
fi

echo "Starting the web GUI in the background..."
"$ROOT/run_gui_background.sh"
echo "Installation task finished. Future launches do not show Terminal:"
echo "  Double-click OPEN_GENAI_MIDI.app to open."
echo "  Double-click STOP_GENAI_MIDI.app to stop."
