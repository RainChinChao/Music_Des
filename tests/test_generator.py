import json
import pytest

from mido import MidiFile

from deterministic_midi import generate_midi, generate_midi_from_file
from deterministic_midi.music_schema import MUSIC_JSON_SCHEMA
from jsonschema import validate


def test_example_generation(tmp_path):
    source = __import__("pathlib").Path(__file__).parents[1] / "example.json"
    output = tmp_path / "example.mid"
    generate_midi_from_file(source, output)
    midi = MidiFile(output)
    assert midi.type == 1
    assert len(midi.tracks) == 3
    assert sum(message.type == "note_on" for track in midi.tracks for message in track) == 6
    validate(instance=json.loads(source.read_text()), schema=MUSIC_JSON_SCHEMA)


def test_mute_and_unmute_automation(tmp_path):
    data = {"tracks": [{"instrument": "Bass", "settings": {"volume": 91, "mute": True},
                        "notes": [{"pitch": "C2", "start": 0, "duration": 1}],
                        "automation": [{"type": "mute", "beat": 0.5, "value": False}]}]}
    output = generate_midi(data, tmp_path / "mute.mid")
    volumes = [m.value for m in MidiFile(output).tracks[1]
               if m.type == "control_change" and m.control == 7]
    assert volumes == [0, 91]


def test_invalid_time_signature_denominator_is_rejected(tmp_path):
    data = {"time_signature": [4, 3], "tracks": []}
    with pytest.raises(ValueError, match="denominator must be 2, 4, 8 or 16"):
        generate_midi(data, tmp_path / "invalid.mid")


def test_every_structured_output_array_declares_items():
    def visit(value):
        if isinstance(value, dict):
            if value.get("type") == "array":
                assert "items" in value
            for child in value.values(): visit(child)
        elif isinstance(value, list):
            for child in value: visit(child)
    visit(MUSIC_JSON_SCHEMA)


def test_string_preset_articulation_and_fx_are_embedded(tmp_path):
    data = {"tracks": [{"name": "Violins", "instrument": "Studio Strings",
             "preset": "Cinematic Violins", "articulation": "Pizzicato",
             "audio_fx": [{"type": "Space Designer", "enabled": True, "amount": 50}],
             "settings": {"volume": 100, "velocity": 80, "sustain": False,
                          "mute": False, "pan": 64,
                          "eq": {"brightness": 64, "resonance": 64, "low": 64,
                                 "mid": 64, "high": 64}},
             "notes": [{"pitch": "A4", "start": 0, "duration": 1, "velocity": 80}],
             "automation": []}]}
    midi = MidiFile(generate_midi(data, tmp_path / "strings.mid"))
    texts = [message.text for message in midi.tracks[1] if message.type == "text"]
    assert any("Cinematic Violins" in text and "Pizzicato" in text for text in texts)
    assert any("Space Designer" in text for text in texts)
    assert any(message.type == "program_change" and message.program == 45
               for message in midi.tracks[1])
