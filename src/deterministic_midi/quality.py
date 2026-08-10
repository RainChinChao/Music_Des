"""Deterministic composition-quality checks used before MIDI rendering."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .requirements import MusicRequirements


@dataclass(frozen=True)
class QualityReport:
    score: int
    issues: tuple[str, ...]
    metrics: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_composition(data: dict[str, Any], requirements: MusicRequirements) -> QualityReport:
    tracks = data.get("tracks", [])
    notes = [(track, note) for track in tracks for note in track.get("notes", [])]
    issues: list[str] = []
    score = 0

    signature = data.get("time_signature", [4, 4])
    beats_per_bar = float(signature[0]) * 4.0 / float(signature[1])
    target_beats = requirements.duration_bars * beats_per_bar
    end_beat = max((float(n.get("start", 0)) + float(n.get("duration", 0))
                    for _, n in notes), default=0.0)
    duration_error = abs(end_beat - target_beats) / max(target_beats, 1.0)
    if duration_error <= 0.1:
        score += 25
    elif duration_error <= 0.25:
        score += 12
        issues.append("Bring the final note ending closer to the requested bar count.")
    else:
        issues.append(f"Duration is {end_beat:.2f} beats; target is {target_beats:.2f} beats.")

    if len(tracks) >= 3:
        score += 15
    else:
        issues.append("Use at least three complementary musical roles unless the request is explicitly solo.")

    instruments = {str(track.get("instrument", "")) for track in tracks}
    rhythmic_styles = {"Pop", "Funk", "Punk", "Indie", "Rock", "Hard rock",
                       "Metal", "Heavy metal", "City pop", "Electronic EDM"}
    if rhythmic_styles.intersection(requirements.styles):
        missing = {"Drums", "Bass"} - instruments
        if not missing:
            score += 15
        else:
            issues.append("Add the missing rhythmic foundation: " + ", ".join(sorted(missing)) + ".")
    else:
        score += 15

    quantized = sum(
        1 for _, note in notes
        if abs(float(note.get("start", 0)) * 4 - round(float(note.get("start", 0)) * 4)) < 1e-6
        and abs(float(note.get("duration", 0)) * 4 - round(float(note.get("duration", 0)) * 4)) < 1e-6
    )
    quantized_ratio = quantized / max(len(notes), 1)
    if quantized_ratio >= 0.9:
        score += 15
    else:
        issues.append("Quantize most note starts and durations to a 1/16-note grid (0.25 beat).")

    density = len(notes) / max(end_beat, 1.0)
    if 0.75 <= density <= 12:
        score += 10
    else:
        issues.append("Adjust note density; avoid an empty arrangement or an overcrowded random-note texture.")

    velocities = {int(note.get("velocity", 80)) for _, note in notes}
    if len(velocities) >= 3:
        score += 10
    else:
        issues.append("Use purposeful velocity variation for accents, phrases and section dynamics.")

    repeated_motif = False
    for track in tracks:
        pitches = [str(note.get("pitch")) for note in track.get("notes", [])]
        motifs = [tuple(pitches[i:i + 4]) for i in range(max(0, len(pitches) - 3))]
        if len(motifs) != len(set(motifs)):
            repeated_motif = True
            break
    if repeated_motif:
        score += 10
    else:
        issues.append("Develop at least one recognizable four-note motif through repetition and variation.")

    metrics = {"tracks": len(tracks), "notes": len(notes), "end_beat": round(end_beat, 3),
               "target_beats": round(target_beats, 3), "note_density": round(density, 3),
               "quantized_ratio": round(quantized_ratio, 3),
               "instruments": sorted(instruments)}
    return QualityReport(min(score, 100), tuple(issues), metrics)
