from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_TRAINING_PROFILE: dict[str, Any] = {
    "updated_at": "initial-installation",
    "provider": "system",
    "model": "deterministic-default",
    "profile": {
        "prompt_additions": ["Create a coherent arrangement with recurring motifs and clear sections."],
        "avoid_rules": ["Avoid stuck notes, unrelated tracks, accidental dissonant clusters, and constant density."],
        "preferred_structure": ["intro", "development", "climax", "ending"],
        "instrument_guidance": ["Give every instrument a distinct role and coordinate rhythm, harmony, and dynamics."],
        "style_guidance": ["Respect ranked style priority and use later styles only as secondary influences."],
        "knowledge_notes": ["Align bass with chord roots, melody with strong-beat chord tones, and drums with metre."],
        "confidence": 50,
        "rationale": "Stable system defaults installed before user-specific learning begins."
    },
}


def ensure_learning_files(data_root: str | Path = "data") -> tuple[Path, Path]:
    """Create valid canonical learning files without replacing learned content."""
    root = Path(data_root)
    kb_path = root / "knowledge_base.jsonl"
    profile_path = root / "training" / "active_prompt_profile.json"
    kb_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    if not kb_path.exists() or kb_path.stat().st_size == 0:
        initial_record = {
            "record_type": "system_bootstrap",
            "saved_at": "initial-installation",
            "knowledge": DEFAULT_TRAINING_PROFILE["profile"],
        }
        kb_path.write_text(json.dumps(initial_record, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    if not profile_path.exists() or profile_path.stat().st_size == 0:
        profile_path.write_text(
            json.dumps(DEFAULT_TRAINING_PROFILE, ensure_ascii=False, indent=2),
            encoding="utf-8")
    return kb_path, profile_path


class SuccessMemory:
    def __init__(self, path: str | Path = "data/success_templates.jsonl") -> None:
        self.path = Path(path)
        ensure_learning_files(self.path.parent)

    @property
    def generation_path(self) -> Path:
        return self.path.parent / "knowledge_base.jsonl"

    @property
    def active_profile_path(self) -> Path:
        return self.path.parent / "training" / "active_prompt_profile.json"

    @property
    def training_history_path(self) -> Path:
        return self.path.parent / "training" / "training_history.jsonl"

    @staticmethod
    def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def add_generation(self, requirements: dict[str, Any], composition: dict[str, Any],
                       *, prompt: str, provider: str, model: str,
                       quality_report: dict[str, Any] | None = None,
                       feedback: str = "") -> None:
        self._append_jsonl(self.generation_path, {
            "record_type": "generation_run",
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "provider": provider, "model": model,
            "requirements": requirements, "composition": composition,
            "quality_report": quality_report or {}, "feedback": feedback,
            "prompt": prompt,
        })

    def load_training_profile(self) -> dict[str, Any]:
        if not self.active_profile_path.exists():
            return {}
        try:
            value = json.loads(self.active_profile_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def save_training_profile(self, profile: dict[str, Any], *, provider: str,
                              model: str, training_input: dict[str, Any]) -> Path:
        self.active_profile_path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "provider": provider, "model": model,
            "profile": profile,
        }
        self.active_profile_path.write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        self._append_jsonl(self.training_history_path, {
            **envelope, "record_type": "prompt_training", "training_input": training_input})
        self._append_jsonl(self.generation_path, {
            **envelope, "record_type": "training_update",
            "training_input": training_input})
        return self.active_profile_path

    def recent_generations(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.generation_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.generation_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                    if record.get("record_type") == "generation_run":
                        records.append(record)
                except json.JSONDecodeError: continue
        return records[-limit:][::-1]

    def add(self, requirements: dict[str, Any], composition: dict[str, Any],
            feedback: str = "") -> None:
        """Backward-compatible success-template writer."""
        self.add_evaluation(requirements, composition, satisfied=True,
                            feedback=feedback)

    def add_evaluation(self, requirements: dict[str, Any],
                       composition: dict[str, Any], *, satisfied: bool,
                       feedback: str = "", ratings: dict[str, int] | None = None,
                       output_files: dict[str, str] | None = None,
                       quality_report: dict[str, Any] | None = None) -> None:
        record = {"saved_at": datetime.now(timezone.utc).isoformat(),
                  "requirements": requirements, "composition": composition,
                  "evaluation": {
                      "satisfied": satisfied,
                      "ratings": ratings or {},
                      "feedback": feedback,
                  },
                  # Retained for readers of the original v3 JSONL format.
                  "feedback": feedback,
                  "output_files": output_files or {},
                  "quality_report": quality_report or {}}
        self._append_jsonl(self.path, record)

    def retrieve(self, styles: list[str] | tuple[str, ...], limit: int = 8) -> list[dict[str, Any]]:
        """Return a relevant mix of successes and failure lessons for every run."""
        if not self.path.exists():
            return []
        wanted = set(styles)
        positive: list[tuple[int, dict[str, Any]]] = []
        negative: list[tuple[int, dict[str, Any]]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                    stored = set(record.get("requirements", {}).get("styles", []))
                    score = len(wanted & stored)
                    evaluation = record.get("evaluation", {})
                    satisfied = evaluation.get("satisfied", True)
                    ratings = evaluation.get("ratings", {})
                    score = score * 10 + sum(int(v) for v in ratings.values())
                    (positive if satisfied else negative).append((score, record))
                except (json.JSONDecodeError, TypeError):
                    continue
        positive.sort(key=lambda item: item[0], reverse=True)
        negative.sort(key=lambda item: item[0], reverse=True)
        # Reserve space for both reusable structures and explicit mistakes to avoid.
        negative_limit = min(len(negative), max(1, limit // 3))
        chosen = positive[:limit - negative_limit] + negative[:negative_limit]
        chosen.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in chosen[:limit]]
