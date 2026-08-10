import json

from mido import Message, MetaMessage, MidiFile, MidiTrack

from deterministic_midi.quality import analyze_composition
from deterministic_midi.reference import extract_music_reference
from deterministic_midi.requirements import MusicRequirements


def test_midi_reference_extracts_actual_note_timing(tmp_path):
    path = tmp_path / "reference.mid"
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack(); midi.tracks.append(track)
    track.append(MetaMessage("set_tempo", tempo=500000, time=0))
    track.append(Message("note_on", note=60, velocity=90, time=0))
    track.append(Message("note_off", note=60, velocity=0, time=480))
    midi.save(path)
    reference = json.loads(extract_music_reference(path))
    assert reference["tempo_bpm"] == 120
    assert reference["notes"][0]["pitch"] == 60
    assert reference["notes"][0]["duration"] == 1


def test_quality_report_detects_underdeveloped_composition():
    req = MusicRequirements(("Pop",), feeling="happy", duration_bars=16)
    data = {"time_signature": [4, 4], "tracks": [{"instrument": "Piano",
            "notes": [{"pitch": "C4", "start": 0, "duration": 1, "velocity": 80}]}]}
    report = analyze_composition(data, req)
    assert report.score < 50
    assert any("Duration" in issue for issue in report.issues)
    assert any("rhythmic foundation" in issue for issue in report.issues)
