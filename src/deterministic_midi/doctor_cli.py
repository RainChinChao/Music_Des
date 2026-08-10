from __future__ import annotations

import argparse

from .cloud_sync import discover_project_root
from .memory import ensure_learning_files
from .system_setup import (install_default_soundfont, pull_ollama_model,
                           run_checks, start_ollama)


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose GenAI MIDI Studio dependencies")
    parser.add_argument("--model", default="qwen2.5:7b-instruct")
    parser.add_argument("--start-ollama", action="store_true")
    parser.add_argument("--pull-model", action="store_true")
    parser.add_argument("--install-soundfont", action="store_true",
                        help="Install MuseScore General SF3 and its MIT licence")
    args = parser.parse_args()
    root = discover_project_root()
    kb_path, profile_path = ensure_learning_files(root / "data")
    if args.start_ollama: start_ollama()
    if args.pull_model: pull_ollama_model(args.model)
    if args.install_soundfont:
        print(f"Installed SoundFont: {install_default_soundfont()}")
    print(f"Learning files: {kb_path}, {profile_path}")
    checks = run_checks(args.model)
    for check in checks:
        symbol = "OK" if check.ok else "FAIL"
        print(f"[{symbol}] {check.name}: {check.detail}")
        if check.fix: print(f"       Fix: {check.fix}")
    if not all(item.ok for item in checks):
        raise SystemExit(1)


if __name__ == "__main__": main()
