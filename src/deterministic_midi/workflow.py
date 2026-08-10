from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audio import midi_to_mp3
from .generator import generate_midi
from .memory import SuccessMemory
from .prompting import build_music_prompt
from .providers import MusicProvider
from .quality import QualityReport, analyze_composition
from .requirements import MusicRequirements


class MusicWorkflow:
    def __init__(self, provider: MusicProvider,
                 memory: SuccessMemory | None = None) -> None:
        self.provider = provider
        self.memory = memory or SuccessMemory()
        self.last_quality_report: QualityReport | None = None

    @staticmethod
    def _validate_schema(composition: dict[str, Any]) -> None:
        try:
            from jsonschema import validate
            from .music_schema import MUSIC_JSON_SCHEMA
            validate(instance=composition, schema=MUSIC_JSON_SCHEMA)
        except ImportError:
            pass

    def generate_json(self, requirements: MusicRequirements,
                      feedback: str = "", previous: dict[str, Any] | None = None,
                      enhance: bool = True, reference_material: str = ""
                      ) -> tuple[dict[str, Any], str]:
        # Knowledge retrieval is deliberately mandatory for initial generations
        # and revisions. The bounded retrieval keeps prompts deterministic in size.
        examples = self.memory.retrieve(requirements.styles, limit=8)
        training_profile = self.memory.load_training_profile()
        prompt = build_music_prompt(requirements, examples, feedback, previous,
                                    reference_material, training_profile)
        composition = self.provider.generate(prompt)
        self._validate_schema(composition)
        initial_report = analyze_composition(composition, requirements)
        self.last_quality_report = initial_report

        if enhance and initial_report.score < 85:
            quality_feedback = (
                "Automatic deterministic quality review. Correct every issue while preserving the "
                "user's intent. Return a complete replacement JSON object.\n" +
                json.dumps(initial_report.as_dict(), ensure_ascii=False, indent=2))
            refinement_prompt = build_music_prompt(
                requirements, examples,
                "\n".join(filter(None, [feedback.strip(), quality_feedback])),
                composition, reference_material, training_profile)
            try:
                refined = self.provider.generate(refinement_prompt)
                self._validate_schema(refined)
                refined_report = analyze_composition(refined, requirements)
                if refined_report.score >= initial_report.score:
                    composition, self.last_quality_report = refined, refined_report
                prompt += "\n\n--- AUTOMATIC QUALITY REFINEMENT PROMPT ---\n\n" + refinement_prompt
            except Exception as exc:
                prompt += "\n\nAutomatic refinement was skipped after an error: " + str(exc)
        self.memory.add_generation(
            requirements.as_dict(), composition, prompt=prompt,
            provider=self.provider.__class__.__name__,
            model=str(getattr(self.provider, "model", "unknown")),
            quality_report=(self.last_quality_report.as_dict()
                            if self.last_quality_report else {}),
            feedback=feedback)
        return composition, prompt

    def save_json(self, composition: dict[str, Any], path: str | Path) -> Path:
        output = Path(path); output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(composition, ensure_ascii=False, indent=2), encoding="utf-8")
        return output

    def json_to_midi(self, composition: dict[str, Any], path: str | Path) -> Path:
        return generate_midi(composition, path)

    def midi_to_mp3(self, midi: str | Path, mp3: str | Path,
                    soundfont: str | Path) -> Path:
        return midi_to_mp3(midi, mp3, soundfont)

    def approve(self, requirements: MusicRequirements,
                composition: dict[str, Any], note: str = "") -> None:
        self.memory.add(requirements.as_dict(), composition, note)

    def evaluate(self, requirements: MusicRequirements,
                 composition: dict[str, Any], *, satisfied: bool,
                 feedback: str = "", ratings: dict[str, int] | None = None,
                 output_files: dict[str, str] | None = None,
                 quality_report: dict[str, Any] | None = None) -> None:
        self.memory.add_evaluation(
            requirements.as_dict(), composition, satisfied=satisfied,
            feedback=feedback, ratings=ratings, output_files=output_files,
            quality_report=quality_report)
