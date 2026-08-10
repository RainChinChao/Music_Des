# System Architecture

## Separate operations

- `json-to-midi`: original deterministic JSON-to-MIDI path.
- `midi-to-mp3`: independent FluidSynth and FFmpeg audio-rendering path.
- `requirements-to-json`: requirements plus retrieved positive/negative knowledge
  to composition JSON.
- `music-workflow`: combined JSON, MIDI and MP3 pipeline.
- `music-gui`: local Streamlit interface and feedback loop.
- `AI Training Page`: isolated runtime prompt/knowledge learning interface.
- `music-doctor`: preflight for audio tools, Ollama, Qwen and SoundFonts.

## Data flow

1. The user chooses one to four different styles in ranked order from the fixed
   list. Any GUI priority slot may be `None`; empty slots are removed while the
   remaining left-to-right priority is preserved.
2. The user enters lyrics, scene, feeling and optional additional requirements.
3. An optional MIDI/JSON/ABC/MusicXML/audio file from another music AI is
   converted into bounded reference context; the user confirms permission.
4. Every generation retrieves a bounded, style-relevant mix of successful
   compositions and dissatisfied feedback, then displays the complete prompt.
5. The selected provider returns composition JSON. Deterministic musical checks
   score structure, duration, roles, quantisation, density, dynamics and motif
   reuse; a low-scoring result receives one automatic refinement pass.
6. JSON Schema validation runs before deterministic MIDI generation.
7. FluidSynth performs quiet offline rendering through the selected SoundFont;
   FFmpeg encodes MP3. No real-time playback process or GUI audio player exists.
8. The GUI saves JSON/MIDI/MP3 under `outputs/<run-id>/`, offers downloads, and
   deliberately provides no embedded audio player or automatic playback.
9. A complete pop-up records satisfaction, three ratings, comments, generated
   composition JSON and output paths in `data/success_templates.jsonl`.
10. Rejection makes the saved feedback available to the next revision; approval
   becomes a positive structural example for later runs.
11. Every generation is logged to `data/knowledge_base.jsonl`. The separate
    trainer converts requirements, feedback and ratings into a validated active
    prompt profile; later generations load it automatically.

Before local generation, the provider checks that Ollama is reachable and that
the requested model is installed. Before MP3 rendering, placeholder paths are
ignored and standard SoundFont locations are searched. The macOS installer
installs MuseScore General plus its licence; GUI uploads persist in
`data/soundfonts` rather than a temporary folder.

API keys are loaded from environment variables. They are never stored in
composition JSON or success memory.
