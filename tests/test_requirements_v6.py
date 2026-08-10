import random

import pytest

from deterministic_midi.requirements import MusicRequirements
from deterministic_midi.generator import PROGRAMS
from deterministic_midi.music_schema import INSTRUMENTS
from deterministic_midi.training_cases import (professional_training_case,
                                                random_training_case)
from deterministic_midi.ui_config import PROVIDER_LABELS, model_options


def test_requires_lyrics_scene_or_feeling_not_only_additional():
    with pytest.raises(ValueError, match="at least one"):
        MusicRequirements(("Pop",), additional="make it catchy")


def test_manual_instruments_are_validated_and_serialized():
    req = MusicRequirements(("Pop",), feeling="bright", instrument_mode="manual",
                            instruments=("Piano", "Studio Strings"))
    assert req.as_dict()["instruments"] == ["Piano", "Studio Strings"]
    with pytest.raises(ValueError, match="at least one instrument"):
        MusicRequirements(("Pop",), feeling="bright", instrument_mode="manual")


def test_automatic_mode_ignores_accidental_manual_values():
    req = MusicRequirements(("Pop",), scene="sunrise", instruments=("Piano",))
    assert req.instruments == ()


def test_random_training_case_is_complete_and_repeatable():
    first = random_training_case(random.Random(42))
    second = random_training_case(random.Random(42))
    assert first == second
    assert first.lyrics and first.scene and first.feeling
    assert 1 <= len(first.styles) <= 4
    assert first.instrument_mode == "manual"
    assert 2 <= len(first.instruments) <= 6


def test_every_provider_has_model_choices():
    assert all(model_options(label) for label in PROVIDER_LABELS)


def test_manual_preset_articulation_and_fx_are_serialized():
    req = MusicRequirements(
        ("Orchestral",), scene="A concert hall",
        preset_mode="manual", presets=("Solo Violin", "Full Strings"),
        articulation_mode="manual", articulations=("Legato", "Pizzicato"),
        audio_fx_mode="manual", audio_fx=("Channel EQ", "Space Designer"))
    result = req.as_dict()
    assert result["presets"] == ["Solo Violin", "Full Strings"]
    assert result["articulations"] == ["Legato", "Pizzicato"]
    assert result["audio_fx"] == ["Channel EQ", "Space Designer"]


def test_every_selectable_instrument_has_a_midi_mapping():
    assert {item.lower() for item in INSTRUMENTS} == set(PROGRAMS) | {"drums"}


def test_automatic_style_mode_allows_ai_to_infer_styles():
    req = MusicRequirements((), scene="A rainy futuristic city", style_mode="automatic")
    assert req.styles == ()
    assert req.as_dict()["style_mode"] == "automatic"


def test_manual_style_mode_still_requires_a_style():
    with pytest.raises(ValueError, match="one and four"):
        MusicRequirements((), feeling="energetic", style_mode="manual")


def test_professional_training_case_uses_ai_long_form_brief():
    class Provider:
        def generate_structured(self, prompt, schema, schema_name):
            return {
                "styles": ["Orchestral", "Pop"], "instruments": ["Violin", "Piano"],
                "lyrics": "word " * 120, "scene": "scene " * 120,
                "feeling": "feeling " * 80, "additional": "arrangement " * 150,
            }
    req = professional_training_case(Provider(), random.Random(3))
    assert req.styles == ("Orchestral", "Pop")
    assert req.instruments == ("Violin", "Piano")
    assert len(req.additional.split()) >= 150
