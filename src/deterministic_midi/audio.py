"""Independent MIDI-to-MP3 rendering; the original MIDI generator is untouched."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from .system_setup import resolve_soundfont


class AudioDependencyError(RuntimeError):
    """Raised when FluidSynth, FFmpeg or a SoundFont is unavailable."""


class AudioRenderError(RuntimeError):
    """Raised with useful renderer output instead of a bare exit status."""


def _run_audio_command(command: list[str], stage: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "No diagnostic output was returned.").strip()
        if len(detail) > 4000:
            detail = detail[-4000:]
        raise AudioRenderError(f"{stage} failed (exit {exc.returncode}):\n{detail}") from exc


def _validate_wav(path: Path, renderer_output: str = "") -> None:
    if not path.is_file() or path.stat().st_size <= 44:
        detail = renderer_output.strip()
        suffix = f"\nFluidSynth output:\n{detail[-3000:]}" if detail else ""
        raise AudioRenderError(
            "FluidSynth did not produce a usable WAV file. Check the MIDI duration "
            "and available disk space." + suffix)
    try:
        with wave.open(str(path), "rb") as audio:
            if audio.getnframes() <= 0 or audio.getframerate() <= 0:
                raise AudioRenderError("FluidSynth produced an empty WAV audio stream.")
    except (wave.Error, EOFError) as exc:
        raise AudioRenderError(f"FluidSynth produced an invalid WAV file: {exc}") from exc


def _require_executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise AudioDependencyError(
            f"{name} was not found. Install it and ensure it is on PATH."
        )
    return path


def midi_to_mp3(
    midi_path: str | Path,
    mp3_path: str | Path,
    soundfont_path: str | Path,
    sample_rate: int = 44100,
    bitrate: str = "192k",
) -> Path:
    """Render MIDI through a SoundFont, then encode the rendered WAV as MP3."""
    midi = Path(midi_path).expanduser().resolve()
    output = Path(mp3_path).expanduser().resolve()
    soundfont = resolve_soundfont(soundfont_path)
    if not midi.is_file() or midi.suffix.lower() not in {".mid", ".midi"}:
        raise ValueError(f"MIDI input does not exist or has an invalid extension: {midi}")
    if not 8000 <= int(sample_rate) <= 192000:
        raise ValueError("sample_rate must be between 8000 and 192000")
    fluidsynth = _require_executable("fluidsynth")
    ffmpeg = _require_executable("ffmpeg")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="deterministic-midi-") as tmp:
        wav = Path(tmp) / "render.wav"
        render_result = _run_audio_command(
            # FluidSynth requires all options before positional SoundFont/MIDI
            # arguments on some builds, including Homebrew's macOS package.
            [fluidsynth, "-ni", "-q", "-F", str(wav), "-T", "wav",
             "-r", str(int(sample_rate)), str(soundfont), str(midi)],
            "FluidSynth MIDI rendering",
        )
        _validate_wav(wav, (render_result.stdout or "") + (render_result.stderr or ""))
        try:
            _run_audio_command(
                [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                 "-i", str(wav), "-map", "0:a:0", "-vn", "-ac", "2",
                 "-ar", str(int(sample_rate)), "-codec:a", "libmp3lame",
                 "-b:a", bitrate, "-map_metadata", "-1", str(output)],
                "FFmpeg MP3 encoding",
            )
        except Exception:
            output.unlink(missing_ok=True)
            raise
        if not output.is_file() or output.stat().st_size == 0:
            output.unlink(missing_ok=True)
            raise AudioRenderError("FFmpeg reported success but produced no MP3 data.")
    return output
