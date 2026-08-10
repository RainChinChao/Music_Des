from __future__ import annotations

import random
from typing import Any

from .music_schema import INSTRUMENTS, STYLES
from .providers import MusicProvider
from .requirements import MusicRequirements

SCENES = [
    "A neon-lit city train crossing a rainy skyline at midnight",
    "Friends driving toward the coast as the sun rises",
    "A quiet astronaut seeing Earth after a long journey",
    "A crowded summer festival building toward its final fireworks",
    "An old theatre reopening while memories return to the stage",
    "A determined runner entering the last kilometre of a championship",
]
FEELINGS = [
    "hopeful and intimate, gradually becoming triumphant",
    "restless, playful and rhythmically confident",
    "melancholic but warm, with a peaceful resolution",
    "mysterious and spacious, then urgent at the climax",
    "joyful, nostalgic and highly danceable",
]
LYRICS = [
    "We follow the light / through every turning street / home is the sound we make",
    "Hold on to the morning / let the old shadows go / we begin again",
    "Under the open sky / our small voices rise / louder than yesterday",
    "The city keeps dreaming / while the midnight colours run / stay until the dawn",
]


PROFESSIONAL_REQUIREMENTS_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["styles", "instruments", "lyrics", "scene", "feeling", "additional"],
    "properties": {
        "styles": {"type": "array", "minItems": 1, "maxItems": 4,
                   "items": {"type": "string", "enum": STYLES}},
        "instruments": {"type": "array", "minItems": 2, "maxItems": 10,
                        "items": {"type": "string", "enum": INSTRUMENTS}},
        "lyrics": {"type": "string"}, "scene": {"type": "string"},
        "feeling": {"type": "string"}, "additional": {"type": "string"},
    },
}


def random_training_case(rng: random.Random | None = None) -> MusicRequirements:
    rng = rng or random.Random()
    style_count = rng.randint(1, 4)
    instrument_count = rng.randint(2, min(6, len(INSTRUMENTS)))
    return MusicRequirements(
        styles=tuple(rng.sample(STYLES, style_count)),
        lyrics=rng.choice(LYRICS), scene=rng.choice(SCENES),
        feeling=rng.choice(FEELINGS),
        additional=rng.choice([
            "Use a memorable recurring motif and a clear ending.",
            "Create strong section contrast without losing musical continuity.",
            "Keep the harmony accessible and give the climax a distinctive rhythmic lift.",
        ]),
        duration_bars=rng.choice([8, 12, 16, 24]),
        instrument_mode="manual",
        instruments=tuple(rng.sample(INSTRUMENTS, instrument_count)),
    )


def professional_training_case(provider: MusicProvider,
                               rng: random.Random | None = None) -> MusicRequirements:
    rng = rng or random.Random()
    inspiration = rng.choice([
        "a feature-film opening sequence", "an emotionally complex stage performance",
        "a large-scale city festival at night", "a speculative science-fiction journey",
        "a character-driven dramatic turning point", "an immersive interactive-world finale",
    ])
    prompt = f"""Create a randomized professional music-production brief inspired by {inspiration}.
Return JSON only. Rank one to four styles from the allowed list and select two to ten instruments.
Write original lyrics of at least 120 words with clear verse/chorus development. Write a scene
description of at least 120 words covering setting, action, pacing and narrative arc. Write a feeling
description of at least 80 words covering emotional progression, energy and tension. Write additional
requirements of at least 150 words covering tempo, metre, harmony, melody, rhythm, sections,
instrument roles, dynamics, articulations, spatial arrangement, transitions and ending. Make every
field specific, coherent, technically useful and substantially different from a short consumer prompt.
Allowed styles: {STYLES}
Allowed instruments: {INSTRUMENTS}
"""
    data = provider.generate_structured(
        prompt, PROFESSIONAL_REQUIREMENTS_SCHEMA, "professional_music_training_brief")
    for field, minimum in (("lyrics", 120), ("scene", 120), ("feeling", 80), ("additional", 150)):
        if len(str(data.get(field, "")).split()) < minimum:
            raise ValueError(f"Professional AI brief field `{field}` is too short; regenerate the case.")
    return MusicRequirements(
        styles=tuple(data["styles"]), instruments=tuple(data["instruments"]),
        lyrics=str(data["lyrics"]), scene=str(data["scene"]), feeling=str(data["feeling"]),
        additional=str(data["additional"]), duration_bars=rng.choice([24, 32, 48, 64]),
        instrument_mode="manual")
