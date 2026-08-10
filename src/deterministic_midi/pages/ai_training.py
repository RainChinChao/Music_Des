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
from deterministic_midi.music_schema import INSTRUMENTS, STYLES
from deterministic_midi.providers import create_provider
from deterministic_midi.system_setup import discover_soundfonts, ollama_tags
from deterministic_midi.training_cases import (professional_training_case,
                                                random_training_case)
from deterministic_midi.ui_components import mp3_player, output_folder_picker
from deterministic_midi.ui_config import (API_ENV_KEYS, PROVIDER_KEYS,
                                           PROVIDER_LABELS, model_options)
from deterministic_midi.workflow import MusicWorkflow

load_dotenv()
st.set_page_config(page_title="AI Music Training", page_icon="🧠", layout="wide")
st.markdown("""
<style>
.st-key-top_navigation {position: sticky; top: 2.75rem; z-index: 999;
  background: var(--background-color); padding: .45rem 0; border-bottom: 1px solid #ddd;}
[data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)
with st.container(key="top_navigation"):
    nav_main, nav_training = st.columns(2)
    if nav_main.button("🎼 GUI Streamlit App", use_container_width=True):
        st.switch_page("streamlit_app.py")
    nav_training.button("🧠 AI Training", disabled=True, use_container_width=True)

st.session_state.setdefault("training_active", False)
training_mode_label = st.radio(
    "Training requirement level", ["Simple", "Professional"], horizontal=True,
    disabled=st.session_state.training_active,
    help="Simple uses short randomized requirements. Professional asks the selected AI for a long, comprehensive production brief.")

st.title("Randomized AI Music Training")
st.info("This separate workflow creates randomized requirements and saved outputs for human ratings. "
        "The selected AI may update runtime prompt preferences and knowledge JSON, but never source code, "
        "dependencies, schema or API configuration.")

with st.sidebar:
    provider_label = st.selectbox("Training AI provider", PROVIDER_LABELS)
    installed = []
    if provider_label == "Ollama (local)":
        try: installed = ollama_tags()
        except Exception: pass
    choices = model_options(provider_label, installed) + ["Custom model…"]
    model_choice = st.selectbox("Training model", choices,
                                key=f"training_model_{PROVIDER_KEYS[provider_label]}")
    model = (st.text_input("Custom model ID",
                           key=f"training_custom_{PROVIDER_KEYS[provider_label]}")
             if model_choice == "Custom model…" else model_choice)
    output_root = output_folder_picker(
        "Training output folder", "outputs/training", "training_output_folder")
    entered_key = ""
    if provider_label != "Ollama (local)":
        entered_key = st.text_input(
            "API key", type="password",
            key="training_api_key_" + PROVIDER_KEYS[provider_label].replace("-", "_"))
        if not entered_key and os.getenv(API_ENV_KEYS[provider_label]):
            st.caption(f"Using {API_ENV_KEYS[provider_label]} from the environment.")
    st.caption("Session API keys are not written into training data.")
    fonts = discover_soundfonts()
    soundfont = st.selectbox("SoundFont", [""] + [str(path) for path in fonts])


def selected_provider():
    api_key = entered_key.strip() or os.getenv(API_ENV_KEYS.get(provider_label, ""), "")
    if provider_label != "Ollama (local)" and not api_key:
        raise ValueError(f"Enter an API key or configure {API_ENV_KEYS[provider_label]}.")
    if not model.strip():
        raise ValueError("Select or enter a model ID.")
    return create_provider(PROVIDER_KEYS[provider_label], model, api_key=api_key or None)


for key, default in {
    "training_active": False, "training_target": 5, "training_completed": 0,
    "training_case": None, "training_composition": None, "training_prompt": "",
    "training_files": {}, "training_quality": {}, "training_message": "",
}.items():
    st.session_state.setdefault(key, default)

target = st.number_input("How many generated outputs do you want to rate?",
                         min_value=1, max_value=100, value=5, step=1,
                         disabled=st.session_state.training_active)
start_col, stop_col = st.columns(2)
if start_col.button("Start randomized training", type="primary",
                    disabled=st.session_state.training_active, use_container_width=True):
    st.session_state.update(training_active=True, training_target=int(target),
                            training_completed=0, training_case=None,
                            training_composition=None, training_files={}, training_message="")
    st.rerun()
if stop_col.button("Stop training now", disabled=not st.session_state.training_active,
                   use_container_width=True):
    st.session_state.training_active = False
    st.session_state.training_message = (
        f"Training stopped after {st.session_state.training_completed} completed rating(s).")
    st.rerun()

st.progress(min(st.session_state.training_completed /
                max(st.session_state.training_target, 1), 1.0),
            text=f"{st.session_state.training_completed} / {st.session_state.training_target} rated")
if st.session_state.training_message:
    st.success(st.session_state.training_message)

if st.session_state.training_active and st.session_state.training_case is None:
    if st.button("Generate next random case", type="primary"):
        try:
            if not soundfont:
                raise ValueError("Select a SoundFont before generating a training output.")
            provider = selected_provider()
            req = (professional_training_case(provider)
                   if training_mode_label == "Professional" else random_training_case())
            flow = MusicWorkflow(provider, SuccessMemory())
            with st.spinner("Generating random requirement case, JSON, MIDI and MP3..."):
                composition, prompt = flow.generate_json(req)
                run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
                folder = (output_root / run_id).resolve()
                folder.mkdir(parents=True, exist_ok=False)
                json_path = flow.save_json(composition, folder / "composition.json")
                midi_path = flow.json_to_midi(composition, folder / "composition.mid")
                mp3_path = flow.midi_to_mp3(midi_path, folder / "composition.mp3", soundfont)
            st.session_state.update(
                training_case=req, training_composition=composition, training_prompt=prompt,
                training_case_mode=training_mode_label,
                training_files={"composition_json": str(json_path), "midi": str(midi_path),
                                "mp3": str(mp3_path)},
                training_quality=(flow.last_quality_report.as_dict()
                                  if flow.last_quality_report else {}))
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

def save_training_response(req, *, satisfied: bool, feedback: str,
                           ratings: dict[str, int], reflection: dict) -> str:
    provider = selected_provider()
    memory = SuccessMemory()
    flow = MusicWorkflow(provider, memory)
    files = st.session_state.training_files
    flow.evaluate(req, st.session_state.training_composition,
                  satisfied=satisfied, feedback=feedback, ratings=ratings,
                  output_files=files, quality_report=st.session_state.training_quality)
    job_id = submit_prompt_training(provider, memory, {
        "source": "randomized_training_popup",
        "original_requirements": req.as_dict(),
        "user_reflection": reflection, "feedback": feedback, "ratings": ratings,
        "selected_generation": st.session_state.training_composition,
        "output_files": files,
    })
    completed = st.session_state.training_completed + 1
    active = completed < st.session_state.training_target
    st.session_state.update(
        training_completed=completed, training_active=active,
        training_case=None, training_composition=None, training_prompt="",
        training_files={}, training_quality={},
        background_training_job=job_id,
        training_message=(f"Response saved. Background AI training job {job_id} is running. "
                          + ("Training target completed." if not active else "Ready for the next case.")))
    return job_id


@st.dialog("Random music training reflection", width="large")
def training_reflection_dialog() -> None:
    req = st.session_state.training_case
    current_round = st.session_state.training_completed + 1
    st.markdown(f"### Training round: {current_round}/{st.session_state.training_target}")
    st.caption(f"Requirement level: {st.session_state.get('training_case_mode', 'Simple')}")
    st.caption("Listen when ready. Audio never starts automatically.")
    mp3_player(st.session_state.training_files["mp3"], "training_popup_output")
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Random requirements")
        st.markdown("**Style and order**")
        for index, style in enumerate(req.styles, 1):
            st.write(f"{index}. {style}")
        st.markdown("**Instruments**")
        st.write(", ".join(req.instruments) or "AI automatic")
        st.markdown("**Lyrics**")
        st.write(req.lyrics)
        st.markdown("**Scene**")
        st.write(req.scene)
        st.markdown("**Feeling**")
        st.write(req.feeling)
        st.markdown("**Additional requirements**")
        st.write(req.additional)

    with right:
        st.subheader("Your reflection")
        st.markdown("**Style and order**")
        style_options = ["None"] + STYLES
        corrected_slots = []
        for index in range(4):
            current = req.styles[index] if index < len(req.styles) else "None"
            corrected_slots.append(st.selectbox(
                f"Style priority {index + 1}", style_options,
                index=style_options.index(current), key=f"reflection_style_{index}"))
        corrected_styles = tuple(item for item in corrected_slots if item != "None")
        corrected_instruments = tuple(st.multiselect(
            "Instruments", INSTRUMENTS, default=list(req.instruments),
            key="reflection_instruments"))
        lyrics_comment = st.text_area("Lyrics comments", key="reflection_lyrics")
        scene_comment = st.text_area("Scene comments", key="reflection_scene")
        feeling_comment = st.text_area("Feeling comments", key="reflection_feeling")
        additional_comment = st.text_area(
            "Additional-requirement comments", key="reflection_additional")

    comments = {
        "lyrics": lyrics_comment.strip(), "scene": scene_comment.strip(),
        "feeling": feeling_comment.strip(), "additional_requirements": additional_comment.strip(),
    }
    differences = {
        "styles": {"random": list(req.styles), "user_expected": list(corrected_styles)},
        "instruments": {"random": list(req.instruments),
                        "user_expected": list(corrected_instruments)},
    }
    reflection = {"expected_styles_in_order": list(corrected_styles),
                  "expected_instruments": list(corrected_instruments),
                  "comments": comments, "differences": differences}
    satisfy_col, reflect_col, cancel_col = st.columns(3)
    if satisfy_col.button("Satisfied", type="primary", use_container_width=True):
        try:
            save_training_response(
                req, satisfied=True, feedback="User satisfied with the generated result.",
                ratings={"style_match": 5, "musical_quality": 5, "requirement_match": 5},
                reflection={"status": "satisfied", **reflection})
            st.rerun(scope="app")
        except Exception as exc:
            st.error(str(exc))
    if reflect_col.button("Submit reflection", use_container_width=True):
        try:
            if not corrected_styles:
                raise ValueError("Select at least one expected style.")
            if not corrected_instruments:
                raise ValueError("Select at least one expected instrument.")
            has_difference = (corrected_styles != req.styles or
                              corrected_instruments != req.instruments)
            if not has_difference and not any(comments.values()):
                raise ValueError("Change a style/instrument or enter at least one comment.")
            feedback = json.dumps(reflection, ensure_ascii=False)
            save_training_response(
                req, satisfied=False, feedback=feedback,
                ratings={"style_match": 3, "musical_quality": 3, "requirement_match": 3},
                reflection={"status": "reflection_submitted", **reflection})
            st.rerun(scope="app")
        except Exception as exc:
            st.error(str(exc))
    if cancel_col.button("Cancel training", use_container_width=True):
        st.session_state.update(
            training_active=False, training_case=None, training_composition=None,
            training_prompt="", training_files={}, training_quality={},
            training_message="Training cancelled. No feedback from this output was stored.")
        st.rerun(scope="app")


if st.session_state.training_case is not None:
    training_reflection_dialog()

active_profile = SuccessMemory().load_training_profile()
if st.session_state.get("background_training_job"):
    status = read_training_status(st.session_state.background_training_job)
    st.info(f"Background AI training: {status['status']} — {status.get('detail', '')}")
    st.button("Refresh background status", key="refresh_training_job")
if active_profile:
    with st.expander("Current active runtime training profile"):
        st.json(active_profile)
