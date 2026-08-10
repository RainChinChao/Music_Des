# GenAI MIDI Studio v8.2

Version 3 extends the original deterministic JSON-to-MIDI library without
changing its generator or `json-to-midi` command.

The first-run layer fixes the most common installation failures:

- Ollama installed but server stopped: preflight explains how to start it.
- Qwen not installed: preflight gives the exact `ollama pull` command.
- Placeholder SoundFont path: ignored rather than treated as a real file.
- Unknown SoundFont location: standard macOS folders are searched automatically.
- No SoundFont: installer downloads MuseScore General SF3 and its MIT notice;
  GUI also supports a persistent `.sf2`/`.sf3` upload.
- Wrong Conda environment: `music-doctor` exposes missing commands immediately.
- Missing learning data: installation creates a valid initial KB and active
  prompting profile, so the first automatic cloud snapshot never depends on
  the user generating music first.

## Independent functions

1. JSON → MIDI: unchanged deterministic Python implementation.
2. MIDI → MP3: FluidSynth renders MIDI through a user-supplied SoundFont;
   FFmpeg encodes MP3.
3. Requirements → JSON: optional GPT, Gemini, Google AI Studio or local Ollama provider.
4. Combined workflow: requirements → JSON → MIDI → MP3.
5. Streamlit GUI: sticky top navigation between the generator and AI training,
   provider-specific model selection, automatic or manual ranked styles,
   (unused slots may be `None`), conditional lyrics/scene/feeling fields,
   automatic or manual instrument choice, visible prompt, JSON review,
   persistent output files, and consent-first pop-up feedback capture.
6. System doctor: executable, Ollama server/model and SoundFont checks.
7. Separate randomized AI Training page: choose 1–100 cases, stop at any time,
   and evaluate each output in an automatic two-column reflection pop-up. The
   left side shows ordered styles, instruments, lyrics, scene, feeling and
   additional requirements. The right side captures corrected style order,
   instruments and comments in the same order.
8. Background learning: feedback windows close immediately after submission;
   AI prompt-profile training continues in a serialized background queue with
   visible queued/running/completed/failed status.
9. Scheduled Google Drive snapshots: upload the KB and active prompt profile
   every three days without an end-user Google login. The installed command
   automatically locates the project, stores configuration in
   `~/.config/deterministic-midi`, validates the Apps Script endpoint, and the interval and
   anonymous/protected upload mode are configurable from Bash.

## Extended string production metadata

Tracks support Studio Strings, Sampler, Alchemy and Vintage Mellotron alongside
the original instruments. They also carry a preset, articulation and Audio FX
list. Named Logic-style patches/effects are embedded as MIDI text metadata;
Pizzicato, Tremolo and Space Designer receive General MIDI approximations.
Exact Logic patches and effects require Logic Pro or a compatible host.

## Local model and business use

The default is `qwen2.5:7b-instruct` through Ollama. Qwen's release notice says
Qwen2.5 variants other than 3B and 72B use Apache 2.0; the 7B selection is made
for that reason. `mistral:7b-instruct` is an alternative whose original Mistral
7B release is Apache 2.0. Model and SoundFont licences must be reviewed again
for the exact version and distribution method before production use. This is
technical guidance, not legal advice.

## Install

For a clean macOS installation from the extracted project folder:

```bash
chmod +x setup_macos.sh
./setup_macos.sh
conda activate genai-midi
music-doctor
music-gui
```

The setup script installs FluidSynth, FFmpeg and Ollama; creates a Python 3.11
Conda environment; installs all Python dependencies; starts Ollama; pulls
`qwen2.5:7b-instruct`; and installs `MuseScore_General.sf3` plus its MIT licence
in `~/Music/SoundFonts`. It also creates the initial KB/prompt files and installs
the automatic Google Drive LaunchAgent with the production three-day interval.
Review `LICENSE_NOTES.md` before commercial release.

See `COMMAND_TUTORIAL.md` for every command and `JSON_RULES.md` for the data
contract.

## Double-click installation on macOS

### First installation

1. Download the project and extract the ZIP file. Do not run the installer from
   inside the ZIP preview.
2. Open the extracted project folder.
3. Double-click `INSTALL_AND_RUN.command`.
4. Allow the installation to finish. It installs the required applications and
   Python environment, creates the initial learning files, configures the
   optional three-day Google Drive schedule, starts the web server in the
   background, and opens the GUI in the default browser.
5. After installation, the project folder contains:
   - `OPEN_GENAI_MIDI.app` — double-click to reopen the tool.
   - `STOP_GENAI_MIDI.app` — double-click to stop the background server.

Keep the extracted project folder in its original location after installation.
Moving or renaming it may prevent the generated launcher applications from
finding the installed files.

### If macOS says Apple cannot verify the developer

The application is not notarised with a paid Apple Developer certificate, so
macOS Gatekeeper may block the first launch. This warning does not mean that the
application failed to install.

Use either of these macOS methods:

**Method 1 — Control-click Open**

1. In Finder, hold **Control** and click `INSTALL_AND_RUN.command`.
2. Select **Open**.
3. Select **Open** again in the security dialog.

**Method 2 — Privacy & Security**

1. Try to open `INSTALL_AND_RUN.command` once and close the warning.
2. Open **System Settings → Privacy & Security**.
3. Scroll to **Security** and find the message that
   `INSTALL_AND_RUN.command` was blocked.
4. Click **Open Anyway**, authenticate with Touch ID or the Mac password, and
   confirm **Open**.

The same one-time approval may be required for `OPEN_GENAI_MIDI.app` and
`STOP_GENAI_MIDI.app`.

If macOS still blocks files downloaded from GitHub, open Terminal, change to the
extracted project directory, and run:

```bash
chmod +x INSTALL_AND_RUN.command
xattr -dr com.apple.quarantine INSTALL_AND_RUN.command OPEN_GENAI_MIDI.app STOP_GENAI_MIDI.app
./INSTALL_AND_RUN.command
```

Only remove the quarantine attribute after confirming that the files came from
this official repository.

### Reopening and closing the tool

After the first installation:

- To open it again, double-click `OPEN_GENAI_MIDI.app`. The server runs in the
  background without leaving a Terminal window open, and the GUI opens in the
  browser.
- Closing the browser tab does not stop the tool.
- To stop it completely, double-click `STOP_GENAI_MIDI.app`.
- If the browser was closed while the server is still running, double-click
  `OPEN_GENAI_MIDI.app` again.

### Terminal fallback

If double-click installation does not work, open Terminal in the extracted
project folder and run:

```bash
chmod +x setup_macos.sh INSTALL_AND_RUN.command
./INSTALL_AND_RUN.command
```

No DMG installation is required for this version.

## Architecture

```text
User requirements + 1–4 ranked styles
              ↓
Optional GenAI provider + approved examples
              ↓
       composition JSON
              ↓
unchanged deterministic JSON-to-MIDI
              ↓
  FluidSynth + SoundFont → WAV
              ↓
          FFmpeg → MP3
              ↓
 save files → pop-up evaluation → knowledge JSONL → retrieve on every AI run
```

API keys stay in `.env`. Satisfied templates, dissatisfied results, numeric
ratings, comments, generated composition JSON and output paths stay locally in
`data/success_templates.jsonl`. Every initial generation and revision retrieves
the most relevant positive and negative lessons from this file. Retrieval is
bounded to keep prompts stable as the knowledge base grows. The application
never writes API keys into prompts, generated JSON or templates.

Generated `composition.json`, `composition.mid`, and `composition.mp3` files
are stored under `outputs/<UTC-time>-<run-id>/`. Both the main GUI and AI
Training page include explicit MP3 **Play**, **Pause**, and **Stop** controls.
Audio never starts automatically; Stop resets playback to the beginning.

## Enhanced composition quality

The default enhanced mode uses explicit harmony, motif, section, quantisation,
arrangement and duration rules. A deterministic quality analyser scores the
first composition. Below 85/100, the system sends its concrete issues into one
automatic refinement pass and retains the higher-scoring result. The score and
metrics are visible in the GUI and stored with user evaluation data.

An optional reference input accepts MIDI, composition JSON, ABC, MusicXML and
common audio formats produced by another music AI. Symbolic formats are reduced
to compact note/structure context for the structured AI stage. Audio is retained
as a reference asset with metadata in the base installation; it is not treated
as an accurate note transcription.

See `MODEL_POLICY.md` before selecting or distributing any general or
music-specific AI model in a commercial product.

## Online API keys in the GUI

Selecting OpenAI GPT, Gemini, Google AI Studio or Claude displays a provider-specific password
field in the sidebar. A pasted key is retained only in the running Streamlit
session and passed directly to that provider. It is never written to `.env`,
prompts, composition JSON, output files, logs or feedback memory. If the field
is blank, the GUI can use `OPENAI_API_KEY`, `GEMINI_API_KEY` or
`ANTHROPIC_API_KEY` already configured in the environment. Ollama is local and
does not show an API-key field.

Google AI Studio uses the official Gemini Developer API and `GEMINI_API_KEY`.
Free-tier quotas and eligible models may change. Google currently states that
free-tier content may be used to improve its products; use a paid configuration
and review current terms before sending confidential commercial data.

Gemini 3.6 structured output uses Google's post-May-2026 Interactions API: a
single polymorphic `response_format` object and the `output_text` response
property. Earlier Gemini models retain the compatible `generateContent`
implementation. The package requires `google-genai>=2,<3` and refuses to send
a Gemini 3.6 request when a legacy 1.x SDK is detected.
Because Google may reject very large or deeply nested native structured-output
schemas, Gemini 3.6 automatically retries a rejected schema in JSON-only mode.
The returned object is still parsed and validated locally against the complete
composition or training schema before it can be used or saved.

## Knowledge and training files

- `data/knowledge_base.jsonl`: every completed JSON-generation run.
- `data/success_templates.jsonl`: explicit satisfaction ratings and comments.
- `data/training/active_prompt_profile.json`: validated rules applied to later prompts.
- `data/training/training_history.jsonl`: auditable AI-training inputs and outputs.

Use **AI Training** in the sticky top navigation. Each case randomly
combines one to four ranked styles, an original lyric fragment, a scene,
feeling, instrument set, musical instruction and duration. No audio autoplays.
**Satisfied** stores a positive 5/5 case and trains the runtime profile;
**Submit reflection** stores structured differences/comments and trains it;
**Cancel training** stops the session without storing feedback for that output.
The reflection window displays the current round (for example, `1/3`) and
automatically closes after Satisfied, Submit reflection, or Cancel completes.
Training can update only
these runtime JSON files; it cannot rewrite Python, schemas or dependencies.

Training-provider choices are independent from the provider used to generate
the song. The page supports local Ollama (any installed model), Google AI
Studio/Gemini, OpenAI GPT, Claude, DeepSeek API and OpenRouter. Online choices
show a masked API-key field only when needed. OpenRouter accepts editable
`provider/model` slugs; the selected routed model's licence, privacy policy and
commercial terms remain applicable.

## Simple and professional AI training

The selector immediately below the sticky page navigation has two modes:

- **Simple**: short deterministic randomized styles, instruments, lyrics,
  scene, feeling and additional requirements.
- **Professional**: the selected AI first creates a long production brief with
  original lyrics and comprehensive narrative, emotional, structural,
  harmonic, rhythmic, instrumental, dynamic and spatial requirements. The
  resulting brief is then used for music generation and human reflection.

## Cloud learning-file snapshots

Cloud sync is disabled until explicitly configured. Google Drive uses the
included Apps Script receiver and can accept uploads without an end-user Google
login. The supplied Drive folder ID is included as the receiver default. Snapshots
are organized under UTC `year_month_date/KB` and
`year_month_date/prompting` folders. Filenames use `KB_..._installationID` and
`Pro_..._installationID`; collisions receive numbered suffixes rather than
overwriting earlier files. See `CLOUD_SYNC_SETUP.md` for setup, privacy,
scheduling and Bash commands.

## Required and optional GUI fields

- Styles: choose **AI automatic** to infer 1–4 suitable styles from the other
  requirements, or **Manual selection** to rank 1–4 distinct styles. Manual
  `None` slots are ignored.
- Lyrics, Scene and Feeling: individually optional, but enable and enter text in
  at least one. Otherwise a red warning appears and generation is refused.
- Instruments: required mode choice. **AI automatic** hides the list and lets
  the model arrange from supported instruments. **Manual selection** reveals a
  multi-select and requires at least one instrument.
- Presets, articulations and Audio FX are separate concepts and each has its
  own automatic/manual selector. Presets are sound patches (for example Solo
  Violin or Full Strings); articulations define note performance (Legato,
  Staccato, Spiccato, Pizzicato or Tremolo); Audio FX process sound (Channel EQ,
  Space Designer and Sample Delay).
- Additional requirements, reference file and feedback comments: optional.
- Feedback ratings default to 5/5. **Yes — save and learn** records the result
  and asks the selected AI to refresh runtime learning files. **No — do nothing**
  closes the dialog without writing feedback data.

Each AI provider has a second model selector. Choose a listed model or
**Custom model…** and enter the exact provider model ID. Availability, pricing,
free-tier eligibility and names can change; confirm them with the provider.

The output-folder control is directly below the model selector. Enter a path or
use **Browse folders…** to navigate parent/subfolders and select a directory.
Streamlit's duplicate built-in sidebar page list is hidden; page switching is
available only from the sticky top navigation.
