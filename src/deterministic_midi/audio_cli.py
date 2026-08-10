from __future__ import annotations

import argparse

from .audio import midi_to_mp3


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a MIDI file to MP3")
    parser.add_argument("input", help="Input .mid file")
    parser.add_argument("output", help="Output .mp3 file")
    parser.add_argument("--soundfont", required=True, help="SoundFont .sf2/.sf3 file")
    parser.add_argument("--sample-rate", type=int, default=44100)
    parser.add_argument("--bitrate", default="192k")
    args = parser.parse_args()
    path = midi_to_mp3(args.input, args.output, args.soundfont,
                       args.sample_rate, args.bitrate)
    print(f"MP3 written to {path}")


if __name__ == "__main__":
    main()

