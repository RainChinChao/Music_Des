from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

from .music_schema import ARTICULATIONS, AUDIO_FX, PRESETS


PROGRAMS = {
    "piano": 0,
    "electric piano": 4,
    "bass": 33,
    "electric guitar": 27,
    "acoustic guitar": 24,
    "vocal": 53,  # General MIDI Voice Oohs; MIDI does not contain recorded vocals.
    "violin": 40, "viola": 41, "cello": 42, "contrabass": 43,
    "harp": 46,
    "studio strings": 48,
    "string ensemble": 48, "choir": 52,
    "trumpet": 56, "trombone": 57, "french horn": 60, "tuba": 58,
    "soprano sax": 64, "alto sax": 65, "tenor sax": 66,
    "flute": 73, "piccolo": 72, "clarinet": 71, "oboe": 68, "bassoon": 70,
    "organ": 19, "accordion": 21, "harmonica": 22,
    "marimba": 12, "vibraphone": 11, "xylophone": 13, "celesta": 8,
    "synth lead": 80, "synth pad": 88, "synth bass": 38,
    "sampler": 0,
    "alchemy": 81,
    "vintage mellotron": 50,
}

PRESET_PROGRAMS = {
    "Solo Violin": 40, "Violin 1 Section": 48, "Violin 2 Section": 48,
    "Full Strings": 48, "Disco Strings": 51, "Violins Solo": 40,
    "String Ensemble": 48, "Hybrid Strings": 50, "Cinematic Violins": 48,
    "Textured Bows": 49, "1 Violins": 40, "3 Violins": 48,
}

ARTICULATION_PROGRAMS = {"Pizzicato": 45, "Tremolo": 44}

# General MIDI CC plus documented application-specific EQ band mappings.
CC = {
    "volume": 7,
    "pan": 10,
    "sustain": 64,
    "eq_resonance": 71,
    "eq_brightness": 74,
    "eq_low": 75,
    "eq_mid": 76,
    "eq_high": 77,
}


def _bounded_int(value: Any, low: int, high: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    result = int(value)
    if not low <= result <= high:
        raise ValueError(f"{field} must be between {low} and {high}")
    return result


def _beat_to_tick(beat: Any, ticks_per_beat: int, field: str) -> int:
    if isinstance(beat, bool) or not isinstance(beat, (int, float)) or beat < 0:
        raise ValueError(f"{field} must be a non-negative number")
    return round(float(beat) * ticks_per_beat)


def _pitch(value: Any) -> int:
    if isinstance(value, int):
        return _bounded_int(value, 0, 127, "pitch")
    if not isinstance(value, str):
        raise ValueError("pitch must be a MIDI number or note name")
    names = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3,
             "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8,
             "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11}
    text = value.strip().upper()
    for name in sorted(names, key=len, reverse=True):
        if text.startswith(name):
            try:
                octave = int(text[len(name):])
            except ValueError as exc:
                raise ValueError(f"invalid pitch: {value}") from exc
            midi_note = (octave + 1) * 12 + names[name]
            return _bounded_int(midi_note, 0, 127, "pitch")
    raise ValueError(f"invalid pitch: {value}")


def _add_event(events: list[tuple[int, int, Message]], tick: int, priority: int,
               message: Message) -> None:
    events.append((tick, priority, message))


def _control_events(track_data: dict[str, Any], channel: int,
                    ticks_per_beat: int) -> list[tuple[int, int, Message]]:
    events: list[tuple[int, int, Message]] = []
    settings = track_data.get("settings", {})
    volume = _bounded_int(settings.get("volume", 100), 0, 127, "volume")
    pan = _bounded_int(settings.get("pan", 64), 0, 127, "pan")
    sustain = 127 if bool(settings.get("sustain", False)) else 0
    muted = bool(settings.get("mute", False))

    for control, value in ((CC["volume"], 0 if muted else volume),
                           (CC["pan"], pan), (CC["sustain"], sustain)):
        _add_event(events, 0, 0, Message("control_change", channel=channel,
                                       control=control, value=value))

    eq = settings.get("eq", {})
    if not isinstance(eq, dict):
        raise ValueError("settings.eq must be an object")
    for key in ("brightness", "resonance", "low", "mid", "high"):
        if key in eq:
            value = _bounded_int(eq[key], 0, 127, f"eq.{key}")
            _add_event(events, 0, 0, Message("control_change", channel=channel,
                                            control=CC[f"eq_{key}"], value=value))

    for index, item in enumerate(track_data.get("automation", [])):
        kind = str(item.get("type", "")).lower()
        tick = _beat_to_tick(item.get("beat", 0), ticks_per_beat,
                             f"automation[{index}].beat")
        if kind == "mute":
            value = 0 if bool(item.get("value", True)) else volume
            control = CC["volume"]
        elif kind in CC:
            raw = item.get("value", 0)
            value = (127 if raw else 0) if kind == "sustain" else _bounded_int(
                raw, 0, 127, f"automation[{index}].value")
            control = CC[kind]
        else:
            raise ValueError(f"unsupported automation type: {kind}")
        _add_event(events, tick, 0, Message("control_change", channel=channel,
                                           control=control, value=value))
    return events


def generate_midi(data: dict[str, Any], output_path: str | Path) -> Path:
    """Validate composition data and write a deterministic Standard MIDI File."""
    ticks = _bounded_int(data.get("ticks_per_beat", 480), 24, 9600,
                         "ticks_per_beat")
    bpm = _bounded_int(data.get("tempo_bpm", 120), 20, 400, "tempo_bpm")
    midi = MidiFile(type=1, ticks_per_beat=ticks)

    conductor = MidiTrack()
    midi.tracks.append(conductor)
    conductor.append(MetaMessage("track_name", name=str(data.get("title", "Composition")), time=0))
    conductor.append(MetaMessage("set_tempo", tempo=bpm2tempo(bpm), time=0))
    signature = data.get("time_signature", [4, 4])
    if not isinstance(signature, list) or len(signature) != 2:
        raise ValueError("time_signature must be [numerator, denominator]")
    numerator = _bounded_int(signature[0], 1, 32, "time_signature numerator")
    denominator = _bounded_int(signature[1], 2, 16, "time_signature denominator")
    if denominator not in {2, 4, 8, 16}:
        raise ValueError("time_signature denominator must be 2, 4, 8 or 16")
    conductor.append(MetaMessage("time_signature", numerator=numerator,
                                 denominator=denominator, time=0))
    conductor.append(MetaMessage("end_of_track", time=0))

    used_channels: set[int] = set()
    for track_index, track_data in enumerate(data.get("tracks", [])):
        instrument = str(track_data.get("instrument", "")).strip().lower()
        if instrument not in {*PROGRAMS, "drums"}:
            raise ValueError(f"unsupported instrument: {instrument}")
        default_channel = 9 if instrument == "drums" else next(
            (c for c in range(16) if c != 9 and c not in used_channels), None)
        channel = _bounded_int(track_data.get("channel", default_channel), 0, 15,
                               f"tracks[{track_index}].channel")
        if instrument == "drums" and channel != 9:
            raise ValueError("drums must use MIDI channel 9 (displayed as channel 10)")
        if channel in used_channels:
            raise ValueError(f"MIDI channel {channel} is used by more than one track")
        used_channels.add(channel)

        track = MidiTrack()
        midi.tracks.append(track)
        name = str(track_data.get("name", track_data["instrument"]))
        track.append(MetaMessage("track_name", name=name, time=0))
        preset = str(track_data.get("preset", "Default"))
        articulation = str(track_data.get("articulation", "Legato"))
        if preset not in PRESETS:
            raise ValueError(f"unsupported preset: {preset}")
        if articulation not in ARTICULATIONS:
            raise ValueError(f"unsupported articulation: {articulation}")
        track.append(MetaMessage(
            "text", text=f"GENAI_MIDI preset={preset}; articulation={articulation}", time=0))
        events = _control_events(track_data, channel, ticks)
        if instrument != "drums":
            default_program = ARTICULATION_PROGRAMS.get(
                articulation, PRESET_PROGRAMS.get(preset, PROGRAMS[instrument]))
            program = _bounded_int(track_data.get("program", default_program),
                                   0, 127, "program")
            _add_event(events, 0, 0, Message("program_change", channel=channel,
                                            program=program))

        effects = track_data.get("audio_fx", [])
        if not isinstance(effects, list):
            raise ValueError("audio_fx must be an array")
        seen_effects: set[str] = set()
        for effect_index, effect in enumerate(effects):
            effect_type = str(effect.get("type", ""))
            if effect_type not in AUDIO_FX:
                raise ValueError(f"unsupported audio_fx type: {effect_type}")
            if effect_type in seen_effects:
                raise ValueError(f"duplicate audio_fx type: {effect_type}")
            seen_effects.add(effect_type)
            enabled = bool(effect.get("enabled", True))
            amount = _bounded_int(effect.get("amount", 64), 0, 127,
                                  f"audio_fx[{effect_index}].amount")
            track.append(MetaMessage(
                "text", text=f"GENAI_MIDI audio_fx={effect_type}; enabled={enabled}; amount={amount}",
                time=0))
            if enabled and effect_type == "Space Designer":
                _add_event(events, 0, 0, Message("control_change", channel=channel,
                                                control=91, value=amount))

        default_velocity = _bounded_int(track_data.get("settings", {}).get("velocity", 80),
                                        1, 127, "velocity")
        for note_index, note in enumerate(track_data.get("notes", [])):
            start = _beat_to_tick(note.get("start", 0), ticks, f"note[{note_index}].start")
            duration = _beat_to_tick(note.get("duration", 1), ticks,
                                     f"note[{note_index}].duration")
            if duration <= 0:
                raise ValueError("note duration must be greater than zero")
            note_number = _pitch(note.get("pitch"))
            velocity = _bounded_int(note.get("velocity", default_velocity), 1, 127,
                                    f"note[{note_index}].velocity")
            _add_event(events, start, 2, Message("note_on", channel=channel,
                                                note=note_number, velocity=velocity))
            _add_event(events, start + duration, 1, Message("note_off", channel=channel,
                                                           note=note_number, velocity=0))

        events.sort(key=lambda item: (item[0], item[1], item[2].type,
                                      getattr(item[2], "note", -1)))
        previous = 0
        for absolute_tick, _, message in events:
            message.time = absolute_tick - previous
            track.append(message)
            previous = absolute_tick
        track.append(MetaMessage("end_of_track", time=0))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    midi.save(output)
    return output


def generate_midi_from_file(json_path: str | Path,
                            output_path: str | Path) -> Path:
    with Path(json_path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("the JSON root must be an object")
    return generate_midi(data, output_path)
