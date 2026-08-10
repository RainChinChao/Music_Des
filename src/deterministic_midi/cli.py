from __future__ import annotations

import argparse

from .generator import generate_midi_from_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MIDI deterministically from JSON")
    parser.add_argument("input", help="Input JSON file")
    parser.add_argument("output", help="Output .mid file")
    args = parser.parse_args()
    path = generate_midi_from_file(args.input, args.output)
    print(f"MIDI written to {path}")


if __name__ == "__main__":
    main()

