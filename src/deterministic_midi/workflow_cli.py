from __future__ import annotations

import argparse
from pathlib import Path

from .providers import create_provider
from .requirements import MusicRequirements
from .reference import extract_music_reference
from .workflow import MusicWorkflow


def main() -> None:
    p = argparse.ArgumentParser(description="Requirements -> JSON -> MIDI -> MP3")
    p.add_argument("output_dir"); p.add_argument("--provider", required=True)
    p.add_argument("--model"); p.add_argument(
        "--styles", nargs="*", default=[],
        help="One to four ranked styles; quote names containing spaces")
    p.add_argument("--style-mode", choices=["automatic", "manual"], default="manual")
    p.add_argument("--lyrics", default=""); p.add_argument("--scene", default="")
    p.add_argument("--feeling", default=""); p.add_argument("--additional", default="")
    p.add_argument("--bars", type=int, default=16); p.add_argument("--soundfont", required=True)
    p.add_argument("--instrument-mode", choices=["automatic", "manual"], default="automatic")
    p.add_argument("--instruments", nargs="*", default=[])
    p.add_argument("--preset-mode", choices=["automatic", "manual"], default="automatic")
    p.add_argument("--presets", nargs="*", default=[])
    p.add_argument("--articulation-mode", choices=["automatic", "manual"], default="automatic")
    p.add_argument("--articulations", nargs="*", default=[])
    p.add_argument("--audio-fx-mode", choices=["automatic", "manual"], default="automatic")
    p.add_argument("--audio-fx", nargs="*", default=[])
    p.add_argument("--reference-file",
                   help="Optional MIDI, JSON, ABC, MusicXML or audio reference")
    args = p.parse_args()
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    req = MusicRequirements(
        styles=tuple(args.styles), lyrics=args.lyrics, scene=args.scene,
        feeling=args.feeling, additional=args.additional, duration_bars=args.bars,
        instrument_mode=args.instrument_mode, instruments=tuple(args.instruments),
        preset_mode=args.preset_mode, presets=tuple(args.presets),
        articulation_mode=args.articulation_mode,
        articulations=tuple(args.articulations), audio_fx_mode=args.audio_fx_mode,
        audio_fx=tuple(args.audio_fx), style_mode=args.style_mode)
    flow = MusicWorkflow(create_provider(args.provider, args.model))
    reference = extract_music_reference(args.reference_file) if args.reference_file else ""
    composition, _ = flow.generate_json(req, reference_material=reference)
    json_path = flow.save_json(composition, out / "composition.json")
    midi_path = flow.json_to_midi(composition, out / "composition.mid")
    mp3_path = flow.midi_to_mp3(midi_path, out / "composition.mp3", args.soundfont)
    print(f"JSON: {json_path}\nMIDI: {midi_path}\nMP3: {mp3_path}")


if __name__ == "__main__": main()
