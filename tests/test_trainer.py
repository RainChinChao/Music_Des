from deterministic_midi.memory import SuccessMemory
from deterministic_midi.providers import MusicProvider
from deterministic_midi.trainer import TRAINING_PROFILE_SCHEMA, train_prompt_profile


class TrainingProvider(MusicProvider):
    model = "training-test"

    def generate(self, prompt):
        raise AssertionError("music generation should not be used by the trainer")

    def generate_structured(self, prompt, schema, schema_name):
        assert schema is TRAINING_PROFILE_SCHEMA
        assert schema_name == "music_training_profile"
        assert "Never propose Python/source-code" in prompt
        return {"prompt_additions": ["Use an eight-bar chorus"],
                "avoid_rules": ["Avoid excessive density"],
                "preferred_structure": ["Intro, verse, chorus, outro"],
                "instrument_guidance": ["Use warm strings"],
                "style_guidance": ["Keep Pop dominant"],
                "knowledge_notes": ["User prefers clear motifs"],
                "confidence": 90, "rationale": "Direct user feedback"}


def test_training_updates_only_runtime_json_files(tmp_path):
    memory = SuccessMemory(tmp_path / "success.jsonl")
    profile, _ = train_prompt_profile(
        TrainingProvider(), memory,
        {"requirements": "Better chorus", "feedback": "Too dense", "ratings": {}})
    assert profile["confidence"] == 90
    assert memory.active_profile_path.exists()
    assert memory.training_history_path.exists()
    assert '"record_type": "training_update"' in memory.generation_path.read_text()
    assert memory.load_training_profile()["profile"]["prompt_additions"]
