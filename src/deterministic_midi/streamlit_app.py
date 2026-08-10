from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv

from deterministic_midi.memory import SuccessMemory
from deterministic_midi.background_training import (read_training_status,
                                                     submit_prompt_training)
from deterministic_midi.music_schema import (ARTICULATIONS, AUDIO_FX, INSTRUMENTS,
                                              PRESETS, STYLES)
from deterministic_midi.providers import create_provider
from deterministic_midi.requirements import MusicRequirements
from deterministic_midi.reference import extract_music_reference
from deterministic_midi.ui_components import mp3_player, output_folder_picker
from deterministic_midi.ui_config import (API_ENV_KEYS, PROVIDER_KEYS,
                                           PROVIDER_LABELS, model_options)
from deterministic_midi.workflow import MusicWorkflow
from deterministic_midi.system_setup import (discover_soundfonts, pull_ollama_model,
                                              run_checks, start_ollama,
                                              is_placeholder_path)

load_dotenv()
st.set_page_config(page_title="GenAI MIDI Studio", page_icon="🎼", layout="wide")
st.markdown("""
<style>
.st-key-top_navigation {position: sticky; top: 2.75rem; z-index: 999;
  background: var(--background-color); padding: .45rem 0; border-bottom: 1px solid #ddd;}
[data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)
with st.container(key="top_navigation"):
    nav_main, nav_training = st.columns(2)
    nav_main.button("🎼 GUI Streamlit App", disabled=True, use_container_width=True)
    if nav_training.button("🧠 AI Training", use_container_width=True):
        st.switch_page("pages/ai_training.py")
st.title("GenAI MIDI Studio")
st.caption("Requirements → visible prompt → JSON → deterministic MIDI → MP3 → feedback memory")

for key, default in {"composition": None, "prompt": "", "requirements": None,
                     "midi": None, "mp3": None, "json_path": None,
                     "last_feedback": "", "reference_path": None,
                     "reference_material": "", "quality_report": None}.items():
    st.session_state.setdefault(key, default)

with st.sidebar:
    provider_name = st.selectbox("AI provider", PROVIDER_LABELS)
    installed_models = []
    if provider_name == "Ollama (local)":
        try:
            from deterministic_midi.system_setup import ollama_tags
            installed_models = ollama_tags()
        except Exception:
            pass
    choices = model_options(provider_name, installed_models) + ["Custom model…"]
    model_choice = st.selectbox("AI model", choices,
                                key=f"main_model_choice_{PROVIDER_KEYS[provider_name]}")
    model = (st.text_input("Custom model ID", key=f"main_custom_{PROVIDER_KEYS[provider_name]}")
             if model_choice == "Custom model…" else model_choice)
    output_root = output_folder_picker("Output folder", "outputs", "main_output_folder")
    entered_api_key = ""
    if provider_name != "Ollama (local)":
        entered_api_key = st.text_input(
            f"{provider_name} API key", type="password",
            key=f"api_key_{PROVIDER_KEYS[provider_name].replace('-', '_')}",
            placeholder="Paste API key for this session",
            help="Held only in this running GUI session; never saved to project files or feedback data.")
        if not entered_api_key and os.getenv(API_ENV_KEYS[provider_name]):
            st.caption(f"Using {API_ENV_KEYS[provider_name]} from the environment.")
    provider_terms = {
        "Ollama (local)": "Default Qwen2.5 7B: Apache-2.0; verify the exact Ollama manifest.",
        "OpenAI GPT": "Commercial API; governed by current OpenAI service terms.",
        "Google AI Studio (Gemini free tier)":
            "Gemini Developer API free tier; quotas/model availability may change and free-tier data may be used to improve Google products.",
        "Gemini": "Commercial API; governed by current Google service terms.",
        "Claude": "Commercial API; governed by current Anthropic service terms.",
        "DeepSeek API": "Commercial API; review current DeepSeek terms and model documentation.",
        "OpenRouter": "Gateway service; the selected upstream model's licence and terms also apply.",
    }
    st.caption(provider_terms[provider_name])
    st.markdown("#### System readiness")
    if st.button("Check system"):
        st.session_state["system_checks"] = run_checks(model)
    for check in st.session_state.get("system_checks", []):
        st.write(("✅" if check.ok else "❌") + f" **{check.name}:** {check.detail}")
        if check.fix: st.caption("Fix: " + check.fix)
    if provider_name == "Ollama (local)":
        c1, c2 = st.columns(2)
        if c1.button("Start Ollama"):
            try: start_ollama(); st.success("Ollama started")
            except Exception as exc: st.error(str(exc))
        if c2.button("Pull model"):
            try: pull_ollama_model(model); st.success("Model installed")
            except Exception as exc: st.error(str(exc))
    found_fonts = discover_soundfonts()
    configured_font = os.getenv("SOUNDFONT_PATH", "")
    font_options = [str(p) for p in found_fonts]
    if not is_placeholder_path(configured_font) and configured_font not in font_options:
        font_options.insert(0, configured_font)
    soundfont = st.selectbox("Discovered SoundFont", [""] + font_options,
                             help="The app searches Downloads, Documents, Music and macOS sound-bank folders")
    uploaded_font = st.file_uploader("Or upload a SoundFont", type=["sf2", "sf3"])
    if uploaded_font is not None:
        upload_dir = Path("data/soundfonts").resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)
        uploaded_path = upload_dir / Path(uploaded_font.name).name
        uploaded_path.write_bytes(uploaded_font.getbuffer())
        soundfont = str(uploaded_path)
    bars = st.slider("Target length (bars)", 4, 64, 16, 4)

st.subheader("1. Style selection")
style_mode_label = st.radio(
    "Style choice (required)", ["AI automatic", "Manual selection"], horizontal=True,
    help="Automatic infers styles from the other requirements. Manual lets you rank up to four styles.")
styles: tuple[str, ...] = ()
if style_mode_label == "Manual selection":
    cols = st.columns(4)
    style_options = ["None"] + STYLES
    style_slots = tuple(cols[i].selectbox(
        f"Priority {i + 1}", style_options, index=i + 1,
        help="Choose None to leave this priority unused.") for i in range(4))
    styles = tuple(style for style in style_slots if style != "None")
    st.caption("Choose between one and four different styles. None selections are ignored; "
               "the remaining selections keep their left-to-right priority.")
else:
    st.caption("The AI will infer and rank one to four styles from Lyrics, Scene, Feeling and "
               "Additional requirements.")

st.subheader("2. Music requirements")
st.caption("Required: enable and complete at least one of Lyrics, Scene or Feeling.")
enabled_cols = st.columns(3)
lyrics_enabled = enabled_cols[0].checkbox("Use Lyrics (optional)", value=False)
scene_enabled = enabled_cols[1].checkbox("Use Scene (optional)", value=False)
feeling_enabled = enabled_cols[2].checkbox("Use Feeling (optional)", value=False)
lyrics = st.text_area("Lyrics (optional)", placeholder="Lyrics or vocal phrasing guidance",
                      disabled=not lyrics_enabled)
scene = st.text_area("Scene / imagination / movie information (optional)",
                     placeholder="Describe the visual scene", disabled=not scene_enabled)
feeling = st.text_area("Feeling (optional)",
                       placeholder="Describe emotion, energy and development",
                       disabled=not feeling_enabled)
if not any((lyrics_enabled, scene_enabled, feeling_enabled)):
    st.error("Select at least one requirement type: Lyrics, Scene or Feeling.")

instrument_mode_label = st.radio(
    "Instrument choice (required)", ["AI automatic", "Manual selection"], horizontal=True,
    help="Automatic lets the AI choose. Manual restricts it to your selected instruments.")
manual_instruments: tuple[str, ...] = ()
if instrument_mode_label == "Manual selection":
    manual_instruments = tuple(st.multiselect(
        "Instruments (select one or more)", INSTRUMENTS,
        placeholder="Choose instruments"))
    if not manual_instruments:
        st.error("Manual instrument mode requires at least one instrument.")

st.caption("Presets are sound patches; articulations describe how notes are played; "
           "Audio FX process the resulting sound. Each category can be chosen by AI or restricted manually.")

def optional_sound_selection(label: str, options: list[str], key: str) -> tuple[str, tuple[str, ...]]:
    mode_label = st.radio(f"{label} choice (optional)", ["AI automatic", "Manual selection"],
                          horizontal=True, key=f"{key}_mode")
    selected: tuple[str, ...] = ()
    if mode_label == "Manual selection":
        selected = tuple(st.multiselect(label, options, key=f"{key}_values",
                                        placeholder=f"Choose one or more {label.lower()}"))
        if not selected:
            st.error(f"Manual {label.lower()} mode requires at least one selection.")
    return ("automatic" if mode_label == "AI automatic" else "manual", selected)

preset_mode, manual_presets = optional_sound_selection("Presets", PRESETS, "presets")
articulation_mode, manual_articulations = optional_sound_selection(
    "Articulations", ARTICULATIONS, "articulations")
audio_fx_mode, manual_audio_fx = optional_sound_selection("Audio FX", AUDIO_FX, "audio_fx")
additional = st.text_area("Additional requirements (optional)",
                          placeholder="Tempo, structure, changes...")

st.subheader("3. Optional music-AI/reference input")
reference_upload = st.file_uploader(
    "Reference produced by another music AI or supplied by the user",
    type=["mid", "midi", "json", "abc", "musicxml", "mxl", "xml",
          "wav", "mp3", "flac", "m4a", "ogg"],
    help="MIDI, JSON, ABC and MusicXML provide symbolic content. Audio is accepted as a reference asset.")
if reference_upload is not None:
    reference_dir = Path("data/references").resolve()
    reference_dir.mkdir(parents=True, exist_ok=True)
    reference_path = reference_dir / Path(reference_upload.name).name
    reference_path.write_bytes(reference_upload.getbuffer())
    try:
        st.session_state.reference_material = extract_music_reference(reference_path)
        st.session_state.reference_path = reference_path
        st.success(f"Reference loaded: {reference_path.name}")
    except Exception as exc:
        st.error(str(exc))
reference_permission = st.checkbox(
    "I have permission to use the uploaded reference material",
    value=reference_upload is None,
    disabled=reference_upload is None)

provider_key = PROVIDER_KEYS[provider_name]
effective_api_key = entered_api_key.strip() or os.getenv(API_ENV_KEYS.get(provider_name, ""), "")

def selected_provider():
    if provider_name != "Ollama (local)" and not effective_api_key:
        raise ValueError(f"Enter a {provider_name} API key in the sidebar or configure "
                         f"{API_ENV_KEYS[provider_name]} in .env.")
    return create_provider(provider_key, model, api_key=effective_api_key or None)

def current_requirements() -> MusicRequirements:
    selected_lyrics = lyrics if lyrics_enabled else ""
    selected_scene = scene if scene_enabled else ""
    selected_feeling = feeling if feeling_enabled else ""
    if not any(value.strip() for value in (selected_lyrics, selected_scene, selected_feeling)):
        raise ValueError("Enable and complete at least one of Lyrics, Scene or Feeling.")
    return MusicRequirements(
        styles=styles, lyrics=selected_lyrics, scene=selected_scene,
        feeling=selected_feeling, additional=additional, duration_bars=bars,
        instrument_mode="automatic" if instrument_mode_label == "AI automatic" else "manual",
        instruments=manual_instruments, preset_mode=preset_mode, presets=manual_presets,
        articulation_mode=articulation_mode, articulations=manual_articulations,
        audio_fx_mode=audio_fx_mode, audio_fx=manual_audio_fx,
        style_mode="automatic" if style_mode_label == "AI automatic" else "manual")

def output_file_map() -> dict[str, str]:
    return {
        "composition_json": str(st.session_state.json_path or ""),
        "midi": str(st.session_state.midi or ""),
        "mp3": str(st.session_state.mp3 or ""),
        "reference": str(st.session_state.reference_path or ""),
    }

@st.dialog("Output feedback", width="large")
def evaluation_dialog() -> None:
    st.subheader("Are you willing to give feedback to the output?")
    st.caption("Choose No to close without storing anything. Choose Yes to save the ratings and "
               "comments and let the selected AI improve the runtime prompt profile and knowledge base.")
    c1, c2, c3 = st.columns(3)
    style_rating = c1.slider("Style match", 1, 5, 5)
    quality_rating = c2.slider("Musical quality", 1, 5, 5)
    requirement_rating = c3.slider("Requirement match", 1, 5, 5)
    feedback = st.text_area(
        "Comments / revision requirements",
        placeholder="Describe strengths to preserve and problems to correct.")
    yes_col, no_col = st.columns(2)
    if yes_col.button("Yes — save and learn", type="primary", use_container_width=True):
        try:
            flow = MusicWorkflow(selected_provider(), SuccessMemory())
            ratings = {"style_match": style_rating, "musical_quality": quality_rating,
                       "requirement_match": requirement_rating}
            files = output_file_map()
            flow.evaluate(
                st.session_state.requirements, st.session_state.composition,
                satisfied=sum(ratings.values()) / len(ratings) >= 4, feedback=feedback,
                ratings=ratings, output_files=files,
                quality_report=st.session_state.quality_report)
            job_id = submit_prompt_training(flow.provider, flow.memory, {
                "source": "application_feedback", "requirements": st.session_state.requirements.as_dict(),
                "feedback": feedback, "ratings": ratings,
                "selected_generation": st.session_state.composition,
                "output_files": files,
            })
            st.session_state.background_training_job = job_id
            st.session_state.feedback_training_message = (
                f"Feedback saved. Background AI training job {job_id} has started.")
            st.session_state.last_feedback = feedback if sum(ratings.values()) / 3 < 4 else ""
            st.session_state.evaluation_saved = True
            st.rerun(scope="app")
        except Exception as exc:
            st.error(str(exc))
    if no_col.button("No — do nothing", use_container_width=True):
        st.session_state.feedback_training_message = "Feedback declined; no feedback data was stored."
        st.rerun(scope="app")

if st.button("Generate composition JSON", type="primary"):
    try:
        if reference_upload is not None and not reference_permission:
            raise ValueError("Confirm permission for the uploaded reference material first.")
        req = current_requirements()
        flow = MusicWorkflow(selected_provider(), SuccessMemory())
        with st.spinner("Generating structured composition..."):
            composition, prompt = flow.generate_json(
                req, reference_material=st.session_state.reference_material)
        st.session_state.update(composition=composition, prompt=prompt, requirements=req,
                                midi=None, mp3=None,
                                quality_report=(flow.last_quality_report.as_dict()
                                                if flow.last_quality_report else None))
    except Exception as exc:
        st.error(str(exc))

if st.session_state.prompt:
    with st.expander("Prompt sent to AI (visible to user)"):
        st.code(st.session_state.prompt)

if st.session_state.quality_report:
    report = st.session_state.quality_report
    st.metric("Deterministic composition quality score", f"{report['score']}/100")
    with st.expander("Quality analysis"):
        if report["issues"]:
            for issue in report["issues"]: st.write("• " + issue)
        else:
            st.success("No deterministic structural issues detected.")
        st.json(report["metrics"])

if st.session_state.composition:
    st.subheader("4. Generated JSON")
    edited = st.text_area("Review or manually edit JSON",
        value=json.dumps(st.session_state.composition, ensure_ascii=False, indent=2), height=420)
    if st.button("Apply JSON edits"):
        try: st.session_state.composition = json.loads(edited); st.success("JSON updated")
        except json.JSONDecodeError as exc: st.error(str(exc))

    if st.button("Generate MIDI and MP3"):
        try:
            if not soundfont: raise ValueError(
                "No SoundFont selected. Choose a discovered file or upload an .sf2/.sf3 file."
            )
            run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
            work = (output_root / run_id).resolve()
            work.mkdir(parents=True, exist_ok=False)
            flow = MusicWorkflow(selected_provider(), SuccessMemory())
            json_path = flow.save_json(st.session_state.composition, work / "composition.json")
            midi = flow.json_to_midi(st.session_state.composition, work / "composition.mid")
            mp3 = flow.midi_to_mp3(midi, work / "composition.mp3", soundfont)
            st.session_state.update(json_path=json_path, midi=midi, mp3=mp3,
                                    evaluation_saved=False, last_feedback="")
            st.success(f"Files saved in: {work}")
        except Exception as exc: st.error(str(exc))

if st.session_state.mp3:
    st.subheader("5. Saved output and evaluation")
    st.info("Playback starts only when you press Play. Pause preserves the position; Stop returns to the beginning.")
    st.code(str(Path(st.session_state.mp3).parent))
    mp3_player(st.session_state.mp3, "main_generated_output")
    st.download_button("Download MIDI", Path(st.session_state.midi).read_bytes(), "composition.mid")
    st.download_button("Download MP3", Path(st.session_state.mp3).read_bytes(), "composition.mp3")
    if st.button("Open satisfaction window", type="primary"):
        evaluation_dialog()
    if st.session_state.get("evaluation_saved"):
        st.success(st.session_state.get("feedback_training_message",
                                       "Evaluation saved for future AI runs."))
    elif st.session_state.get("feedback_training_message"):
        st.info(st.session_state.feedback_training_message)
    if st.session_state.get("background_training_job"):
        status = read_training_status(st.session_state.background_training_job)
        st.info(f"Background AI training: {status['status']} — {status.get('detail', '')}")
        st.button("Refresh background status")
    if st.session_state.last_feedback and st.button("Generate revision from saved feedback"):
        try:
            req = current_requirements()
            flow = MusicWorkflow(selected_provider(), SuccessMemory())
            with st.spinner("Revising composition..."):
                composition, prompt = flow.generate_json(
                    req, st.session_state.last_feedback, st.session_state.composition,
                    reference_material=st.session_state.reference_material)
            st.session_state.update(composition=composition, prompt=prompt, requirements=req,
                                    midi=None, mp3=None, json_path=None, last_feedback="",
                                    quality_report=(flow.last_quality_report.as_dict()
                                                    if flow.last_quality_report else None))
            st.rerun()
        except Exception as exc: st.error(str(exc))
