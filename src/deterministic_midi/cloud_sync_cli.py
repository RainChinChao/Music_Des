from __future__ import annotations

import argparse
import plistlib
import sys
from uuid import uuid4
from pathlib import Path

from .cloud_sync import (discover_project_root, load_config,
                         normalize_installation_id, save_config, sync_now,
                         test_connection)


def _install_schedule(seconds: float, root: Path) -> Path:
    (root / "data").mkdir(parents=True, exist_ok=True)
    target = Path.home() / "Library/LaunchAgents/com.deterministic-midi.cloud-sync.plist"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(plistlib.dumps({
        "Label": "com.deterministic-midi.cloud-sync",
        "ProgramArguments": [sys.executable, "-m", "deterministic_midi.cloud_sync_cli", "--run-now"],
        "WorkingDirectory": str(root), "StartInterval": max(1, round(seconds)),
        "RunAtLoad": True, "StandardOutPath": str(root / "data/cloud_sync.log"),
        "StandardErrorPath": str(root / "data/cloud_sync_error.log"),
    }))
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure scheduled Google Drive learning-file sync")
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--install-schedule", action="store_true")
    parser.add_argument("--disable", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--test-connection", action="store_true")
    parser.add_argument("--drive-url")
    parser.add_argument("--anonymous-upload", action="store_true")
    parser.add_argument("--protected-upload", action="store_true")
    parser.add_argument("--interval-days", type=float)
    parser.add_argument("--interval-seconds", type=float,
                        help="Upload interval in seconds; intended for short tests")
    parser.add_argument("--installation-id",
                        help="Stable device/product installation ID used in uploaded filenames")
    args = parser.parse_args(); root = discover_project_root()
    if args.disable: print(f"Google Drive sync disabled: {save_config(enabled=False)}")
    if args.configure:
        current = load_config()
        seconds = (args.interval_seconds if args.interval_seconds is not None else
                   args.interval_days * 86400 if args.interval_days is not None else
                   float(current.get("interval_seconds", 259200)))
        if seconds <= 0: raise SystemExit("upload interval must be greater than zero")
        endpoint = (args.drive_url if args.drive_url is not None
                    else current.get("google_drive_web_app_url", ""))
        if not endpoint:
            raise SystemExit("--drive-url is required for the first configuration")
        print("Google Drive connection OK:", test_connection(str(endpoint)))
        print("Google Drive sync configured:", save_config(
            enabled=True, interval_seconds=seconds, project_root=str(root),
            google_drive_web_app_url=endpoint,
            anonymous_upload=(False if args.protected_upload else True if args.anonymous_upload
                              else current.get("anonymous_upload", True)),
            installation_id=normalize_installation_id(
                args.installation_id or current.get("installation_id") or uuid4().hex[:12])))
    if args.install_schedule:
        current = load_config()
        seconds = (args.interval_seconds if args.interval_seconds is not None else
                   args.interval_days * 86400 if args.interval_days is not None else
                   float(current.get("interval_seconds", 259200)))
        save_config(interval_seconds=seconds, project_root=str(root))
        plist = _install_schedule(seconds, root)
        print(f"LaunchAgent written: {plist}")
        print(f"Load it with: launchctl bootstrap gui/$(id -u) {plist}")
    if args.run_now:
        for item in sync_now(): print(f"Uploaded: {item}")
    if args.test_connection:
        print("Google Drive connection OK:", test_connection(args.drive_url))
    if args.status or not any((args.configure, args.run_now, args.install_schedule,
                               args.disable, args.test_connection)):
        print(load_config())


if __name__ == "__main__": main()
