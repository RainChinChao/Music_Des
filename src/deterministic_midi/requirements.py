from __future__ import annotations

from dataclasses import dataclass, field

from .music_schema import ARTICULATIONS, AUDIO_FX, INSTRUMENTS, PRESETS, STYLES


@dataclass(frozen=True)
class MusicRequirements:
    styles: tuple[str, ...]
    lyrics: str = ""
    scene: str = ""
    feeling: str = ""
    additional: str = ""
    duration_bars: int = 16
    instrument_mode: str = "automatic"
    instruments: tuple[str, ...] = ()
    preset_mode: str = "automatic"
    presets: tuple[str, ...] = ()
    articulation_mode: str = "automatic"
    articulations: tuple[str, ...] = ()
    audio_fx_mode: str = "automatic"
    audio_fx: tuple[str, ...] = ()
    style_mode: str = "manual"

    def __post_init__(self) -> None:
        # API callers may pass None/"None" for GUI-equivalent empty slots.
        selected = tuple(style for style in self.styles
                         if style is not None and str(style).strip().lower() != "none")
        style_mode = self.style_mode.strip().lower()
        if style_mode not in {"automatic", "manual"}:
            raise ValueError("style_mode must be automatic or manual")
        if style_mode == "automatic":
            selected = ()
        object.__setattr__(self, "style_mode", style_mode)
        object.__setattr__(self, "styles", selected)
        if style_mode == "manual" and not 1 <= len(selected) <= 4:
            raise ValueError("select between one and four ranked styles")
        invalid = [style for style in selected if style not in STYLES]
        if invalid:
            raise ValueError(f"unsupported styles: {invalid}")
        if len(set(selected)) != len(selected):
            raise ValueError("selected ranked styles must be different")
        if not any([self.lyrics.strip(), self.scene.strip(), self.feeling.strip()]):
            raise ValueError("provide at least one of lyrics, scene or feeling")
        if not 1 <= int(self.duration_bars) <= 128:
            raise ValueError("duration_bars must be between 1 and 128")
        mode = self.instrument_mode.strip().lower()
        if mode not in {"automatic", "manual"}:
            raise ValueError("instrument_mode must be automatic or manual")
        object.__setattr__(self, "instrument_mode", mode)
        selected_instruments = tuple(self.instruments)
        if mode == "automatic":
            selected_instruments = ()
        elif not selected_instruments:
            raise ValueError("select at least one instrument in manual mode")
        invalid_instruments = [item for item in selected_instruments if item not in INSTRUMENTS]
        if invalid_instruments:
            raise ValueError(f"unsupported instruments: {invalid_instruments}")
        if len(set(selected_instruments)) != len(selected_instruments):
            raise ValueError("manually selected instruments must be different")
        object.__setattr__(self, "instruments", selected_instruments)
        self._validate_choice("preset", self.preset_mode, self.presets, PRESETS)
        self._validate_choice("articulation", self.articulation_mode,
                              self.articulations, ARTICULATIONS)
        self._validate_choice("audio_fx", self.audio_fx_mode, self.audio_fx, AUDIO_FX)

    def _validate_choice(self, name: str, mode_value: str,
                         values: tuple[str, ...], allowed: list[str]) -> None:
        mode = mode_value.strip().lower()
        if mode not in {"automatic", "manual"}:
            raise ValueError(f"{name}_mode must be automatic or manual")
        selected = () if mode == "automatic" else tuple(values)
        if mode == "manual" and not selected:
            raise ValueError(f"select at least one {name} in manual mode")
        invalid = [item for item in selected if item not in allowed]
        if invalid:
            raise ValueError(f"unsupported {name} values: {invalid}")
        if len(set(selected)) != len(selected):
            raise ValueError(f"manually selected {name} values must be different")
        object.__setattr__(self, f"{name}_mode", mode)
        object.__setattr__(self, "audio_fx" if name == "audio_fx" else name + "s", selected)

    def as_dict(self) -> dict:
        return {
            "styles": list(self.styles), "style_mode": self.style_mode,
            "lyrics": self.lyrics,
            "scene": self.scene, "feeling": self.feeling,
            "additional": self.additional, "duration_bars": self.duration_bars,
            "instrument_mode": self.instrument_mode,
            "instruments": list(self.instruments),
            "preset_mode": self.preset_mode, "presets": list(self.presets),
            "articulation_mode": self.articulation_mode,
            "articulations": list(self.articulations),
            "audio_fx_mode": self.audio_fx_mode, "audio_fx": list(self.audio_fx),
        }
