from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st


def output_folder_picker(label: str, default: str, key: str) -> Path:
    """Editable output path with a server-side directory browser."""
    value_key = f"{key}_value"
    browse_key = f"{key}_browse_path"
    st.session_state.setdefault(value_key, default)

    @st.dialog(f"Browse: {label}", width="large")
    def browser() -> None:
        entered = Path(st.session_state[value_key]).expanduser()
        fallback = entered if entered.is_dir() else entered.parent
        current = Path(st.session_state.get(browse_key, fallback or Path.cwd())).expanduser()
        try:
            current = current.resolve()
            directories = sorted(
                (item for item in current.iterdir() if item.is_dir() and not item.name.startswith(".")),
                key=lambda item: item.name.lower())
        except (OSError, PermissionError) as exc:
            st.error(f"Cannot browse this folder: {exc}")
            current, directories = Path.cwd().resolve(), []
        st.code(str(current))
        parent_col, select_col = st.columns(2)
        if parent_col.button("⬆ Parent folder", use_container_width=True,
                             disabled=current.parent == current):
            st.session_state[browse_key] = str(current.parent)
            st.rerun(scope="fragment")
        if select_col.button("Select this folder", type="primary", use_container_width=True):
            st.session_state[value_key] = str(current)
            st.rerun()
        if directories:
            chosen = st.selectbox("Subfolders", directories,
                                  format_func=lambda item: item.name)
            if st.button("Open selected subfolder", use_container_width=True):
                st.session_state[browse_key] = str(chosen)
                st.rerun(scope="fragment")
        else:
            st.caption("No accessible subfolders are shown here.")

    path_text = st.text_input(label, key=value_key)
    if st.button("Browse folders…", key=f"{key}_browse_button", use_container_width=True):
        browser()
    return Path(path_text).expanduser()


def mp3_player(path: str | Path, key: str) -> None:
    """Render a non-autoplay MP3 player with explicit play, pause and stop controls."""
    source = Path(path)
    if not source.is_file() or source.suffix.lower() != ".mp3":
        st.warning("The MP3 player is unavailable because the saved MP3 file cannot be found.")
        return
    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    element_id = "mp3_" + "".join(char if char.isalnum() else "_" for char in key)
    safe_id = html.escape(element_id, quote=True)
    document = f"""
        <style>
          .player {{font-family: sans-serif; border: 1px solid #ddd; border-radius: 10px;
                    padding: 12px; background: #fafafa;}}
          .controls {{display: flex; gap: 8px; margin-top: 9px;}}
          button {{flex: 1; border: 1px solid #bbb; border-radius: 7px; padding: 8px;
                   background: white; cursor: pointer; font-weight: 600;}}
          button:hover {{background: #f0f2f6;}}
          audio {{width: 100%;}}
        </style>
        <div class="player">
          <audio id="{safe_id}" preload="metadata">
            <source src="data:audio/mpeg;base64,{encoded}" type="audio/mpeg">
          </audio>
          <div class="controls">
            <button onclick="document.getElementById('{safe_id}').play()">▶ Play</button>
            <button onclick="document.getElementById('{safe_id}').pause()">⏸ Pause</button>
            <button onclick="const a=document.getElementById('{safe_id}');a.pause();a.currentTime=0;">⏹ Stop</button>
          </div>
        </div>
        """
    document_url = "data:text/html;base64," + base64.b64encode(
        document.encode("utf-8")).decode("ascii")
    st.iframe(document_url, height=105, width="stretch", tab_index=0)
