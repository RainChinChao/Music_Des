"""Convert common music-model outputs into compact prompt reference material."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mido import MidiFile, tempo2bpm


SUPPORTED_REFERENCE_SUFFIXES = {
    ".mid", ".midi", ".json", ".abc", ".musicxml", ".mxl", ".xml",
    ".wav", ".mp3", ".flac", ".m4a", ".ogg",
}


def _midi_reference(path: Path, max_notes: int = 600) -> str:
    midi = MidiFile(path)
    tempo = 500000
    signature = "4/4"
    notes: list[dict] = []
    programs: dict[int, int] = {}
    for track_index, track in enumerate(midi.tracks):
        absolute = 0
        active: dict[tuple[int, int], tuple[int, int]] = {}
        for message in track:
            absolute += message.time
            if message.type == "set_tempo": tempo = message.tempo
            elif message.type == "time_signature":
                signature = f"{message.numerator}/{message.denominator}"
            elif message.type == "program_change": programs[message.channel] = message.program
            elif message.type == "note_on" and message.velocity > 0:
                active[(message.channel, message.note)] = (absolute, message.velocity)
            elif message.type in {"note_off", "note_on"}:
                key = (message.channel, message.note)
                if key in active and len(notes) < max_notes:
                    start, velocity = active.pop(key)
                    notes.append({"track": track_index, "channel": message.channel,
                                  "pitch": message.note,
                                  "start": round(start / midi.ticks_per_beat, 3),
                                  "duration": round((absolute - start) / midi.ticks_per_beat, 3),
                                  "velocity": velocity})
    return json.dumps({"format": "MIDI", "tempo_bpm": round(tempo2bpm(tempo), 2),
                       "time_signature": signature, "programs": programs,
                       "notes": notes, "notes_truncated": len(notes) >= max_notes},
                      ensure_ascii=False)


def _audio_reference(path: Path) -> str:
    command = ["ffprobe", "-v", "error", "-show_entries",
               "format=duration,format_name:stream=codec_name,sample_rate,channels",
               "-of", "json", str(path)]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        metadata = json.loads(result.stdout)
    except Exception:
        metadata = {"file_name": path.name}
    return json.dumps({"format": "audio_reference", "metadata": metadata,
                       "instruction": "Use this only as a reference asset. Audio note transcription "
                                      "is not inferred by the base installation."}, ensure_ascii=False)


def extract_music_reference(path: str | Path, max_characters: int = 30000) -> str:
    source = Path(path).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() not in SUPPORTED_REFERENCE_SUFFIXES:
        raise ValueError(f"Unsupported or missing reference music file: {source}")
    suffix = source.suffix.lower()
    if suffix in {".mid", ".midi"}:
        return _midi_reference(source)
    if suffix in {".wav", ".mp3", ".flac", ".m4a", ".ogg"}:
        return _audio_reference(source)
    text = source.read_text(encoding="utf-8", errors="replace")[:max_characters]
    if suffix == ".json":
        text = json.dumps(json.loads(text), ensure_ascii=False, separators=(",", ":"))
    return json.dumps({"format": suffix.lstrip("."), "content": text}, ensure_ascii=False)
