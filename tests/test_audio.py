from pathlib import Path
import subprocess
import wave
from unittest.mock import patch

import pytest

from deterministic_midi.audio import AudioRenderError, midi_to_mp3


def test_audio_pipeline_invokes_two_tools(tmp_path):
    midi = tmp_path / "x.mid"; midi.write_bytes(b"MThd")
    sf = tmp_path / "x.sf2"; sf.write_bytes(b"sf")
    out = tmp_path / "x.mp3"
    def run_command(command, **kwargs):
        if command[0].endswith("fluidsynth"):
            wav = Path(command[command.index("-F") + 1])
            with wave.open(str(wav), "wb") as audio:
                audio.setnchannels(2); audio.setsampwidth(2); audio.setframerate(44100)
                audio.writeframes(b"\0" * 400)
        else:
            Path(command[-1]).write_bytes(b"mp3")
        return subprocess.CompletedProcess(command, 0, "", "")

    with patch("deterministic_midi.audio.shutil.which", side_effect=lambda x: f"/usr/bin/{x}"), \
         patch("deterministic_midi.audio.subprocess.run", side_effect=run_command) as run:
        assert midi_to_mp3(midi, out, sf) == out.resolve()
        assert run.call_count == 2


def test_ffmpeg_failure_exposes_stderr_and_removes_partial_file(tmp_path):
    midi = tmp_path / "x.mid"; midi.write_bytes(b"MThd")
    sf = tmp_path / "x.sf3"; sf.write_bytes(b"sf")
    out = tmp_path / "x.mp3"

    def run_command(command, **kwargs):
        if command[0].endswith("fluidsynth"):
            wav = Path(command[command.index("-F") + 1])
            with wave.open(str(wav), "wb") as audio:
                audio.setnchannels(2); audio.setsampwidth(2); audio.setframerate(44100)
                audio.writeframes(b"\0" * 400)
            return subprocess.CompletedProcess(command, 0, "", "")
        out.write_bytes(b"partial")
        raise subprocess.CalledProcessError(254, command, stderr="No space left on device")

    with patch("deterministic_midi.audio.shutil.which", side_effect=lambda x: f"/usr/bin/{x}"), \
         patch("deterministic_midi.audio.subprocess.run", side_effect=run_command):
        with pytest.raises(AudioRenderError, match="No space left on device"):
            midi_to_mp3(midi, out, sf)
    assert not out.exists()
