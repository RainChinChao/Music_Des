# Complete Command Tutorial (macOS + VS Code)

## A. Clean installation for a new user

Download and extract `genai-midi-studio-v8.2.zip`. In Finder, open the extracted
`deterministic-midi` folder and double-click `INSTALL_AND_RUN.command`. Terminal
performs first-time installation and then starts the web GUI in the background.
For command-line installation, open a fresh Terminal and run:

```bash
cd ~/Downloads
unzip -o genai-midi-studio-v8.2.zip
cd deterministic-midi
ls -la
```

Confirm that `pyproject.toml`, `.env.example` and `setup_macos.sh` exist.

After installation, use the locally created `OPEN_GENAI_MIDI.app`; it starts or
reopens the background GUI without showing Terminal. Use `STOP_GENAI_MIDI.app`
to stop it without showing Terminal. The `.command` files remain diagnostic
fallbacks.

### Recommended automatic setup

```bash
chmod +x setup_macos.sh
./setup_macos.sh
conda activate genai-midi
music-doctor
```

`music-doctor` should show OK for FluidSynth, FFmpeg, Ollama, the Ollama server,
Qwen, and the SoundFont. Installation also creates these files immediately:

```text
data/knowledge_base.jsonl
data/training/active_prompt_profile.json
```

It configures and loads the macOS LaunchAgent at a production interval of three
days. No user action is required for later uploads. Every generation/training
iteration updates the canonical local data: the KB appends historical evidence,
while the active prompting profile replaces its older active version. Every
cloud upload has a timestamped name, preserving recoverable snapshot history.

### Google Apps Script prerequisite

The automatic upload uses `GOOGLE_DRIVE_UPLOAD_WEB_APP.gs`. In Google Apps
Script, paste this file, then choose **Deploy → New deployment → Web app**,
**Execute as Me**, **Who has access: Anyone**, and authorize Drive. The deployed
URL must end in `/exec`. The supplied installation is configured for the current
Music-folder receiver. To override it before installation:

```bash
export GENAI_MIDI_DRIVE_URL='https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec'
export GENAI_MIDI_INSTALLATION_ID='YOUR_ID'
./setup_macos.sh
```

The Drive folder-sharing URL and the Apps Script editor `/edit` URL cannot be
used; only the deployed `/exec` URL accepts uploads.

### macOS configuration permission repair

Normally no `sudo` command is required. If installation reports `PermissionError`
for `~/.config/deterministic-midi`, repair only that application directory:

```bash
sudo mkdir -p "$HOME/.config/deterministic-midi"
sudo chown -R "$(id -u):$(id -g)" "$HOME/.config/deterministic-midi"
sudo chmod -R u+rwX "$HOME/.config/deterministic-midi"
touch "$HOME/.config/deterministic-midi/write-test"
rm "$HOME/.config/deterministic-midi/write-test"
```

Then rerun `./setup_macos.sh`. Do not change ownership of the whole home folder.

### Verify the automatic three-day installation

```bash
music-cloud-sync --test-connection
music-cloud-sync --status
launchctl print gui/$(id -u)/com.deterministic-midi.cloud-sync
music-cloud-sync --run-now
```

`--run-now` is only a diagnostic check; normal users do not need to run it.

### Manual setup alternative

```bash
brew install fluid-synth ffmpeg ollama
conda create -n genai-midi python=3.11 -y
conda activate genai-midi
python -m pip install --upgrade pip
python -m pip install -e '.[all]'
cp .env.example .env
brew services start ollama
ollama pull qwen2.5:7b-instruct
music-doctor --install-soundfont
music-doctor
```

Never activate `.venv` and Conda together. The prompt should show only
`(genai-midi)` (and possibly `(base)` should be absent).

## B. SoundFont setup

Automatic setup installs MuseScore General and its MIT notice. To install or
repair it separately:

```bash
conda activate genai-midi
music-doctor --install-soundfont
music-doctor
```

It is saved at `~/Music/SoundFonts/MuseScore_General.sf3`. You can alternatively
put another licensed General MIDI file in a searched folder. Discover files with:

```bash
find /Applications "$HOME/Downloads" "$HOME/Documents" "$HOME/Music" \
  -type f \( -iname "*.sf2" -o -iname "*.sf3" \) 2>/dev/null
```

Either choose the discovered file in the GUI, upload it through the GUI, or set
its exact absolute path in `.env`:

```text
SOUNDFONT_PATH=/Users/your-name/Downloads/your-font.sf2
```

Leaving `SOUNDFONT_PATH=` blank is valid. Automatic discovery will run.

## C. Start the GUI

```bash
conda activate genai-midi
cd ~/Downloads/deterministic-midi
music-doctor
music-gui
```

The application never invokes `open`, `afplay`, or a real-time FluidSynth
playback driver. FluidSynth runs only as a quiet offline MIDI-to-WAV renderer.
After rendering, the main GUI and AI Training page provide user-controlled MP3
**Play**, **Pause**, and **Stop** buttons. Playback never starts automatically.

Open `http://localhost:8501` if the browser does not open automatically. Stop
the GUI with Control+C.

The GUI saves each run in `outputs/<UTC-time>-<run-id>/`. Its embedded player
starts only after the user presses Play. Use **Open feedback window** after rendering.
The pop-up asks whether the user is willing to give feedback. **No** stores
nothing. **Yes** stores the three ratings (default 5/5) and optional comments,
then updates the AI runtime prompt profile. These records and the generated JSON
and file paths are stored in `data/success_templates.jsonl`; every later AI run
retrieves relevant successful structures and failure lessons.

Each of the four style selectors supports `None`. Select between one and four
styles; `None` slots are ignored and the remaining styles keep their displayed
left-to-right priority. Selected styles must be different.

Enable Lyrics, Scene and/or Feeling and enter text in at least one enabled
field. Unselected fields remain grey. The GUI shows a red warning and refuses
generation if all three are disabled or blank. Choose **AI automatic** for
instrument selection, or **Manual selection** to reveal the supported
multi-select list.

The sticky navigation at the top switches between **GUI Streamlit App** and
**AI Training** and remains visible while the page scrolls. Presets,
articulations and Audio FX have independent automatic/manual selectors because
they are not instruments.

Styles also support **AI automatic** and **Manual selection**. The automatic
mode infers styles from the enabled requirement fields. The output path appears
immediately below the AI model selector; type a path or use **Browse folders…**.
The duplicate Streamlit page selector is intentionally hidden from the sidebar.

Choose the AI provider and then choose one of that provider's model IDs in the
second selector. Use **Custom model…** only when the exact desired model does
not appear. An account may not have access to every listed online model.

## D. Repair Ollama and Qwen automatically

```bash
conda activate genai-midi
music-doctor --start-ollama --pull-model
```

Equivalent manual commands:

```bash
brew services start ollama
curl http://localhost:11434/api/tags
ollama pull qwen2.5:7b-instruct
ollama list
```

The GUI also provides **Start Ollama**, **Pull model**, and **Check system**
buttons in its sidebar.

## E. Run every function separately

### JSON to MIDI (original function, unchanged)

```bash
json-to-midi example.json output.mid
```

Fallback:

```bash
python -m deterministic_midi.cli example.json output.mid
```

### MIDI to MP3

```bash
midi-to-mp3 output.mid output.mp3 \
  --soundfont "/Users/your-name/Downloads/your-font.sf2"
```

### Requirements to JSON with local Qwen

```bash
requirements-to-json generated.json \
  --provider ollama \
  --model qwen2.5:7b-instruct \
  --style-mode automatic \
  --scene 'A neon city at midnight' \
  --feeling 'Hopeful and nostalgic' \
  --bars 16
```

For manual ranked styles:

```bash
requirements-to-json generated.json \
  --provider ollama \
  --model qwen2.5:7b-instruct \
  --style-mode manual \
  --styles Pop Funk 'City pop' 'Electronic EDM' \
  --lyrics 'Optional lyric guidance' \
  --scene 'A neon city at midnight' \
  --feeling 'Hopeful, energetic and nostalgic' \
  --additional 'Strong bass, evolving chorus and clean ending' \
  --instrument-mode manual \
  --instruments Piano Bass Drums 'Studio Strings' \
  --bars 16
```

Only one, two or three styles are also valid in Bash. Do not type placeholder
`None` values—just provide the selected styles:

```bash
requirements-to-json generated.json \
  --provider ollama \
  --model qwen2.5:7b-instruct \
  --styles Pop 'City pop' \
  --scene 'A neon city at midnight' \
  --feeling 'Hopeful and nostalgic' \
  --bars 16
```

Use a MIDI, JSON, ABC, MusicXML or audio file from a separate music-specific AI
as reference material:

```bash
requirements-to-json generated.json \
  --provider ollama \
  --model qwen2.5:7b-instruct \
  --styles Pop Rock \
  --reference-file references/music-ai-candidate.mid \
  --feeling 'Energetic and uplifting' \
  --bars 16
```

### Generated JSON to MIDI and MP3

```bash
json-to-midi generated.json generated.mid
midi-to-mp3 generated.mid generated.mp3 \
  --soundfont "/Users/your-name/Downloads/your-font.sf2"
```

No command automatically plays the generated audio.

## F. Run the complete pipeline

```bash
music-workflow outputs \
  --provider ollama \
  --model qwen2.5:7b-instruct \
  --styles Pop Funk 'City pop' 'Electronic EDM' \
  --scene 'A neon city at midnight' \
  --feeling 'Hopeful, energetic and nostalgic' \
  --additional 'Strong bass and an uplifting final chorus' \
  --bars 16 \
  --soundfont "/Users/your-name/Downloads/your-font.sf2"
```

Outputs:

```text
outputs/composition.json
outputs/composition.mid
outputs/composition.mp3
```

## G. Online providers

Edit `.env` and add only the required key:

```bash
code .env
```

```text
OPENAI_API_KEY=
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
SOUNDFONT_PATH=
```

Then choose the provider and its model in the GUI. Every provider has preset
model choices plus a custom model-ID option because availability changes.

Gemini 3.6 requires Google SDK 2.x and the revised Interactions API path included
in v6.7. If Google rejects the large native composition schema, the provider
automatically retries in JSON-only mode and validates the response locally.
When updating an existing environment, reinstall the project and run:

```bash
python -m pip uninstall -y google-genai
python -m pip install -U 'google-genai>=2,<3'
python -m pip install -e '.[all]'
```

Alternatively, select an online provider and paste its key into the masked API
key box in the GUI sidebar. A key entered there lasts only for the current GUI
session and is not saved to `.env` or knowledge-base files. When both are
present, the GUI value takes precedence over the corresponding `.env` value.

### Google AI Studio free-tier API

Create an API key in Google AI Studio, then choose **Google AI Studio (Gemini
free tier)** and paste the key into the masked box. The implementation uses the
official `google-genai` SDK and `GEMINI_API_KEY`. Free quotas and model
eligibility may change; free-tier content may be used by Google to improve its
products, so do not treat it as a confidential production tier.

## H. Anonymous Google Drive learning-file upload

The supplied Drive folder is configured in `GOOGLE_DRIVE_UPLOAD_WEB_APP.gs`.
Deploy that file as a Google Apps Script web app that executes as you and
allows anonymous access. When updating an existing deployment, select a **new
version**; saving the script alone does not update its `/exec` endpoint. Copy
the deployment `/exec` URL, then run:

```bash
music-cloud-sync --configure \
  --drive-url 'https://script.google.com/macros/s/DEPLOYMENT_ID/exec' \
  --anonymous-upload \
  --installation-id 'MY_PRODUCT_001' \
  --interval-days 3

music-cloud-sync --run-now
music-cloud-sync --install-schedule
launchctl bootstrap gui/$(id -u) \
  "$HOME/Library/LaunchAgents/com.deterministic-midi.cloud-sync.plist"
```

Change the upload interval at any time:

```bash
music-cloud-sync --configure --interval-days 1
music-cloud-sync --install-schedule --interval-days 1
```

For a three-second test, use the scheduler itself (not a relative-path shell loop):

```bash
music-cloud-sync --configure \
  --drive-url 'https://script.google.com/macros/s/DEPLOYMENT_ID/exec' \
  --anonymous-upload \
  --installation-id 'TEST001' \
  --interval-seconds 3
music-cloud-sync --test-connection
music-cloud-sync --install-schedule --interval-seconds 3
launchctl bootout gui/$(id -u) \
  "$HOME/Library/LaunchAgents/com.deterministic-midi.cloud-sync.plist" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) \
  "$HOME/Library/LaunchAgents/com.deterministic-midi.cloud-sync.plist"
music-gui
```

The installed command locates the project automatically, regardless of the
terminal's current folder. Its persistent configuration is stored under
`~/.config/deterministic-midi`.

See `CLOUD_SYNC_SETUP.md` for the complete anonymous/protected deployment and
LaunchAgent reload instructions.

## H. Separate AI training page

From the main GUI, click **Open AI Training Page**. Enter requirements or
preferences, feedback, and three ratings. Optionally select a recent generation
run, then click **Train prompt and knowledge profile**.

Training writes:

```text
data/knowledge_base.jsonl
data/training/active_prompt_profile.json
data/training/training_history.jsonl
```

Every later generation loads the active profile automatically. The trainer is
schema-constrained and prohibited from modifying Python code, dependencies,
API configuration or the MIDI schema.

Training AI providers:

```text
Ollama local       no API key; enter any installed model name
Google AI Studio   GEMINI_API_KEY
Gemini API         GEMINI_API_KEY
OpenAI GPT         OPENAI_API_KEY
Claude             ANTHROPIC_API_KEY
DeepSeek API       DEEPSEEK_API_KEY
OpenRouter         OPENROUTER_API_KEY
```

For OpenRouter, enter a model slug such as `openrouter/free` or another
`provider/model` value. Model availability, licence, data handling and price
depend on the selected route. DeepSeek uses its official OpenAI-compatible API
endpoint; the default model field remains editable.

## I. Commands for later sessions

If Ollama runs through Homebrew services:

```bash
cd ~/Downloads/deterministic-midi
conda activate genai-midi
music-doctor
music-gui
```

If the Ollama service is stopped:

```bash
brew services start ollama
cd ~/Downloads/deterministic-midi
conda activate genai-midi
music-gui
```

When finished:

```bash
# Stop GUI first with Control+C
conda deactivate
```

Ollama may remain in the background. Stop it only if desired:

```bash
brew services stop ollama
```

## J. Diagnostic meanings

- `music-gui: command not found`: wrong environment or package not installed;
  run `conda activate genai-midi` and `python -m pip install -e '.[all]'`.
- `Connection refused` on port 11434: run `music-doctor --start-ollama`.
- Qwen/model not installed: run `music-doctor --pull-model`.
- Placeholder SoundFont path: clear it in `.env`, then select/upload a real file.
- No SoundFont found: place a licensed `.sf2/.sf3` in a searched folder.
- Python 3.9 rejected: recreate the environment with Python 3.11.
