#!/usr/bin/env bash
set -euo pipefail

MODEL="${GENAI_MIDI_MODEL:-qwen2.5:7b-instruct}"
DRIVE_URL="${GENAI_MIDI_DRIVE_URL:-https://script.google.com/macros/s/AKfycbw2jDuSYWk8DR9ECJRLLs-UE3p38_uznoThjlWStNQ1KUS16ydSy7ZpPoTG95ohyvEn/exec}"
INSTALLATION_ID="${GENAI_MIDI_INSTALLATION_ID:-}"

if ! command -v conda >/dev/null 2>&1; then
  echo "Conda is required. Install Miniconda/Anaconda, then rerun this script."
  exit 1
fi
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required. Install it from https://brew.sh, then rerun this script."
  exit 1
fi

brew install fluid-synth ffmpeg ollama
if ! conda env list | awk '{print $1}' | grep -qx genai-midi; then
  conda create -n genai-midi python=3.11 -y
fi

CONDA_BASE="$(conda info --base)"
PYTHON="$CONDA_BASE/envs/genai-midi/bin/python"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e '.[all]'
"$PYTHON" -c 'from pathlib import Path; from deterministic_midi.memory import ensure_learning_files; print("Initial learning files:", ensure_learning_files(Path.cwd() / "data"))'

test -f .env || cp .env.example .env
brew services start ollama || true
for _ in {1..20}; do
  curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1 && break
  sleep 1
done
ollama pull "$MODEL"
"$PYTHON" -m deterministic_midi.doctor_cli --install-soundfont || {
  echo "SoundFont download failed. Retry with: music-doctor --install-soundfont"
  exit 1
}

# Configure automatic Google Drive learning snapshots. Production installation
# is always three days; --interval-seconds is reserved for explicit testing.
CONFIGURE_ARGS=(--configure --drive-url "$DRIVE_URL" --anonymous-upload --interval-days 3)
if [[ -n "$INSTALLATION_ID" ]]; then
  CONFIGURE_ARGS+=(--installation-id "$INSTALLATION_ID")
fi
"$PYTHON" -m deterministic_midi.cloud_sync_cli "${CONFIGURE_ARGS[@]}"
"$PYTHON" -m deterministic_midi.cloud_sync_cli --install-schedule --interval-days 3
PLIST="$HOME/Library/LaunchAgents/com.deterministic-midi.cloud-sync.plist"
launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo
echo "Setup complete. Next run:"
echo "  conda activate genai-midi"
echo "  music-doctor"
echo "  music-gui"
echo "Google Drive KB/prompt snapshots are scheduled every 3 days."
