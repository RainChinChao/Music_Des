from __future__ import annotations

import json
from typing import Any

from .music_schema import (ARTICULATIONS, AUDIO_FX, INSTRUMENTS,
                           MUSIC_JSON_SCHEMA, PRESETS)
from .requirements import MusicRequirements


def build_music_prompt(requirements: MusicRequirements,
                       examples: list[dict[str, Any]] | None = None,
                       failure_feedback: str = "",
                       previous_json: dict[str, Any] | None = None,
                       reference_material: str = "",
                       training_profile: dict[str, Any] | None = None) -> str:
    ranked = " > ".join(requirements.styles)
    context = {
        "style_selection": {"mode": requirements.style_mode,
                            "ranked_styles": ranked},
        "scene": requirements.scene, "feeling": requirements.feeling,
        "additional_requirements": requirements.additional,
        "target_duration_bars": requirements.duration_bars,
        "instrument_selection": {
            "mode": requirements.instrument_mode,
            "selected": list(requirements.instruments),
        },
        "preset_selection": {"mode": requirements.preset_mode,
                             "selected": list(requirements.presets)},
        "articulation_selection": {"mode": requirements.articulation_mode,
                                   "selected": list(requirements.articulations)},
        "audio_fx_selection": {"mode": requirements.audio_fx_mode,
                               "selected": list(requirements.audio_fx)},
    }
    parts = [
        "Create one complete musical composition as JSON for a deterministic MIDI generator.",
        "Return JSON only and follow the supplied schema exactly.",
        f"Use only these instruments: {', '.join(INSTRUMENTS)}.",
        f"Use only these presets: {', '.join(PRESETS)}.",
        f"Use only these articulations: {', '.join(ARTICULATIONS)}.",
        f"Audio FX may use: {', '.join(AUDIO_FX)}. amount is 0-127. Logic-specific "
        "names are preserved as MIDI metadata and approximated where General MIDI permits.",
        ("Infer one to four suitable ranked styles from the lyrics, scene, feeling and additional "
         "requirements because the user selected AI-automatic style mode."
         if requirements.style_mode == "automatic" else
         "Style priority is ordered: earlier selected styles must dominate later selected styles."),
        ("Choose the instruments automatically from the allowed list to best serve the styles, scene, "
         "feeling and lyrics." if requirements.instrument_mode == "automatic" else
         "Use the user's manually selected instruments and do not add instruments outside that selection: "
         + ", ".join(requirements.instruments) + "."),
        ("Choose presets automatically." if requirements.preset_mode == "automatic" else
         "Use only these user-selected presets: " + ", ".join(requirements.presets) + "."),
        ("Choose articulations automatically." if requirements.articulation_mode == "automatic" else
         "Use only these user-selected articulations: " +
         ", ".join(requirements.articulations) + "."),
        ("Choose audio effects automatically and omit them when unnecessary."
         if requirements.audio_fx_mode == "automatic" else
         "Use only these user-selected audio effects: " + ", ".join(requirements.audio_fx) + "."),
        "Use MIDI note events; lyrics guide melody/rhythm but cannot become recorded vocals.",
        "Keep melodic tracks on unique channels and drums on channel 9, or omit all channels.",
        "Compose a coherent arrangement, not independent random tracks: establish one tonal centre; "
        "use a repeating chord progression; make bass follow chord roots; align melody with chord tones "
        "on strong beats; and make drums reinforce the metre.",
        "Use clear sections such as intro, verse/development, chorus/climax and ending. Reuse and vary "
        "recognizable motifs, use smooth voice leading, purposeful rests, velocity-shaped phrases, and "
        "contrasting section dynamics.",
        "Quantize most events to 0.25-beat units. Avoid stuck notes, accidental dissonant clusters, "
        "unnecessary track doubling, extreme pitch jumps and constant maximum density.",
        "time_signature must contain exactly [numerator, denominator], and denominator must be "
        "one of 2, 4, 8 or 16.",
        "The final note-off should be near the exact requested duration. Give every included track a "
        "musical role and coordinate its rhythm and harmony with all other tracks.",
        "Composition requirements:\n" + json.dumps(context, ensure_ascii=False, indent=2),
        "JSON schema:\n" + json.dumps(MUSIC_JSON_SCHEMA, ensure_ascii=False),
    ]
    if examples:
        compact = [{"requirements": item.get("requirements"),
                    "composition": item.get("composition"),
                    "evaluation": item.get("evaluation", {
                        "satisfied": True,
                        "feedback": item.get("feedback", "")
                    })} for item in examples]
        parts.append("Previous user evaluations. Reuse strengths from satisfied items and "
                     "avoid problems described in dissatisfied items:\n" +
                     json.dumps(compact, ensure_ascii=False))
    if previous_json is not None:
        parts.append("Previous composition to revise:\n" +
                     json.dumps(previous_json, ensure_ascii=False))
    if failure_feedback.strip():
        parts.append("User dissatisfaction/failure information to correct:\n" + failure_feedback.strip())
    if reference_material.strip():
        parts.append("Optional music-specific AI/reference-file analysis. Extract useful melody, "
                     "rhythm, harmony, structure and instrumentation, but still obey the user "
                     "requirements and output schema:\n" + reference_material.strip())
    if training_profile:
        profile = training_profile.get("profile", training_profile)
        parts.append("Validated active training profile. Apply these learned preferences and "
                     "prompt improvements unless they conflict with the current user request or "
                     "schema:\n" + json.dumps(profile, ensure_ascii=False, indent=2))
    return "\n\n".join(parts)
