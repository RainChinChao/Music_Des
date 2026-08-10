"""AI-assisted runtime prompt/knowledge training without source-code mutation."""

from __future__ import annotations

import json
from typing import Any

from .memory import SuccessMemory
from .providers import MusicProvider


TRAINING_PROFILE_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["prompt_additions", "avoid_rules", "preferred_structure",
                 "instrument_guidance", "style_guidance", "knowledge_notes",
                 "confidence", "rationale"],
    "properties": {
        "prompt_additions": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "avoid_rules": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "preferred_structure": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "instrument_guidance": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "style_guidance": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "knowledge_notes": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
        "rationale": {"type": "string"},
    },
}


def train_prompt_profile(provider: MusicProvider, memory: SuccessMemory,
                         training_input: dict[str, Any]) -> tuple[dict[str, Any], str]:
    current = memory.load_training_profile()
    recent = memory.recent_generations(limit=5)
    compact_runs = [{
        "saved_at": item.get("saved_at"), "provider": item.get("provider"),
        "model": item.get("model"), "requirements": item.get("requirements"),
        "title": item.get("composition", {}).get("title"),
        "quality_report": item.get("quality_report"),
        "feedback": item.get("feedback"),
    } for item in recent]
    prompt = "\n\n".join([
        "Act as a music-generation prompt and preference trainer.",
        "Improve only runtime prompting and knowledge guidance. Never propose Python/source-code, "
        "schema, dependency, security, API-key, filesystem or system changes.",
        "Convert the user's requirements, feedback and ratings into concise reusable rules. "
        "Preserve useful existing rules, remove contradictions, avoid overfitting to one song, and "
        "do not infer a preference that the user did not express.",
        "Current active profile:\n" + json.dumps(current, ensure_ascii=False),
        "Recent generation summaries:\n" + json.dumps(compact_runs, ensure_ascii=False),
        "New training input:\n" + json.dumps(training_input, ensure_ascii=False),
        "Return the complete replacement training profile as JSON.",
    ])
    profile = provider.generate_structured(prompt, TRAINING_PROFILE_SCHEMA,
                                           "music_training_profile")
    try:
        from jsonschema import validate
        validate(instance=profile, schema=TRAINING_PROFILE_SCHEMA)
    except ImportError:
        pass
    memory.save_training_profile(
        profile, provider=provider.__class__.__name__,
        model=str(getattr(provider, "model", "unknown")), training_input=training_input)
    return profile, prompt
