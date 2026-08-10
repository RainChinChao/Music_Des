from deterministic_midi.memory import SuccessMemory
from deterministic_midi.providers import MusicProvider
from deterministic_midi.requirements import MusicRequirements
from deterministic_midi.workflow import MusicWorkflow
import pytest


class FakeProvider(MusicProvider):
    def generate(self, prompt):
        return {"title": "Test", "tempo_bpm": 120, "time_signature": [4, 4],
                "ticks_per_beat": 480, "tracks": [{"name": "Piano", "instrument": "Piano",
                "preset": "Default", "articulation": "Legato", "audio_fx": [],
                "settings": {"volume": 100, "velocity": 80, "sustain": False,
                "mute": False, "pan": 64, "eq": {"brightness": 64, "resonance": 64,
                "low": 64, "mid": 64, "high": 64}},
                "notes": [{"pitch": "C4", "start": 0, "duration": 1, "velocity": 80}],
                "automation": []}]}


def test_generate_approve_and_retrieve(tmp_path):
    memory = SuccessMemory(tmp_path / "success.jsonl")
    req = MusicRequirements(("Pop", "Funk", "Indie", "Rock"), feeling="happy")
    flow = MusicWorkflow(FakeProvider(), memory)
    composition, prompt = flow.generate_json(req)
    assert "Pop > Funk > Indie > Rock" in prompt
    assert flow.json_to_midi(composition, tmp_path / "x.mid").exists()
    flow.approve(req, composition)
    assert len(memory.retrieve(req.styles)) == 1


def test_both_satisfaction_outcomes_are_retrieved(tmp_path):
    memory = SuccessMemory(tmp_path / "knowledge.jsonl")
    req = MusicRequirements(("Pop", "Funk", "Indie", "Rock"), feeling="happy")
    flow = MusicWorkflow(FakeProvider(), memory)
    composition, _ = flow.generate_json(req)
    flow.evaluate(req, composition, satisfied=True,
                  ratings={"musical_quality": 5}, output_files={"midi": "x.mid"})
    flow.evaluate(req, composition, satisfied=False, feedback="Bass is too loud")
    records = memory.retrieve(req.styles)
    assert {record["evaluation"]["satisfied"] for record in records} == {True, False}
    assert records[0]["composition"]["title"] == "Test"


def test_optional_style_slots_are_removed_in_priority_order():
    req = MusicRequirements(("Pop", None, "City pop", "None"), feeling="happy")
    assert req.styles == ("Pop", "City pop")
    assert req.as_dict()["styles"] == ["Pop", "City pop"]


def test_at_least_one_unique_style_is_required():
    with pytest.raises(ValueError, match="between one and four"):
        MusicRequirements((None, "None"), feeling="happy")
    with pytest.raises(ValueError, match="must be different"):
        MusicRequirements(("Pop", "Pop"), feeling="happy")
