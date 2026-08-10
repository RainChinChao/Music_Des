from __future__ import annotations

import base64
import json
import os
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from .memory import ensure_learning_files

DEFAULT_CONFIG = {
    "enabled": False, "interval_seconds": 259200,
    "project_root": "",
    "google_drive_web_app_url": "", "anonymous_upload": True,
    "installation_id": "",
}


def config_path() -> Path:
    override = os.getenv("DETERMINISTIC_MIDI_CONFIG_DIR", "").strip()
    base = (Path(override).expanduser() if override else
            Path.home() / ".config/deterministic-midi")
    return base / "cloud_sync_config.json"


def discover_project_root() -> Path:
    configured = ""
    if config_path().exists():
        try:
            configured = str(json.loads(
                config_path().read_text(encoding="utf-8")).get("project_root", ""))
        except (OSError, json.JSONDecodeError): pass
    candidates: list[Any] = [os.getenv("DETERMINISTIC_MIDI_HOME", ""), configured,
                             Path.cwd(), *Path.cwd().parents]
    module_root = Path(__file__).resolve().parents[2]
    candidates.extend([module_root, *module_root.parents,
                       Path.home() / "Downloads/deterministic-midi",
                       Path.home() / "Documents/deterministic-midi"])
    for candidate in candidates:
        if not candidate: continue
        path = Path(candidate).expanduser().resolve()
        if (((path / "pyproject.toml").is_file() and
             (path / "src/deterministic_midi").is_dir()) or
                (path / ".genai-midi-root").is_file()):
            return path
    raise RuntimeError("Cannot find deterministic-midi. Set DETERMINISTIC_MIDI_HOME to its absolute path.")


def load_config() -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if config_path().exists():
        try:
            value = json.loads(config_path().read_text(encoding="utf-8"))
            if isinstance(value, dict): config.update(value)
        except (OSError, json.JSONDecodeError): pass
    return config


def save_config(**changes: Any) -> Path:
    config = load_config(); config.update(changes)
    path = config_path(); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def normalize_installation_id(value: str) -> str:
    cleaned = "".join(char for char in value.strip() if char.isalnum() or char in "-_")
    if not cleaned:
        cleaned = uuid4().hex[:12]
    return cleaned[:64]


def _last_sync_path() -> Path:
    return config_path().parent / "cloud_last_sync.json"


def _is_due(config: dict[str, Any]) -> bool:
    if not _last_sync_path().exists(): return True
    try:
        completed = datetime.fromisoformat(json.loads(
            _last_sync_path().read_text(encoding="utf-8"))["completed_at"])
    except (OSError, json.JSONDecodeError, KeyError, ValueError): return True
    seconds = float(config.get("interval_seconds",
                               float(config.get("interval_days", 3)) * 86400))
    return datetime.now(timezone.utc) >= completed + timedelta(seconds=seconds)


def _response_json(response: requests.Response, operation: str) -> dict[str, Any]:
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Google Drive {operation} failed with HTTP {response.status_code}: "
                           f"{response.text[:300]}") from exc
    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Google Drive {operation} returned HTML/non-JSON. Use the deployed Apps Script /exec "
            "URL with Execute as Me and access set to Anyone. Response: " +
            response.text[:300]) from exc
    if not isinstance(result, dict) or not result.get("ok"):
        detail = result.get("error", result) if isinstance(result, dict) else result
        raise RuntimeError(f"Google Drive {operation} rejected: {detail}")
    return result


def test_connection(url: str | None = None) -> dict[str, Any]:
    endpoint = (url or str(load_config().get("google_drive_web_app_url", ""))).strip()
    if not endpoint: raise RuntimeError("Google Drive Apps Script web-app URL is not configured.")
    return _response_json(requests.get(endpoint, timeout=30), "connection test")


def sync_now() -> list[str]:
    config = load_config()
    if not config.get("enabled"):
        raise RuntimeError("Google Drive sync is disabled. Run music-cloud-sync --configure.")
    configured_root = str(config.get("project_root", "")).strip()
    root = Path(configured_root).expanduser().resolve() if configured_root else discover_project_root()
    if not ((root / "pyproject.toml").is_file() or
            (root / ".genai-midi-root").is_file()):
        root = discover_project_root(); save_config(project_root=str(root))
    load_dotenv(root / ".env")
    url = str(config.get("google_drive_web_app_url", "")).strip()
    if not url: raise RuntimeError("Google Drive Apps Script web-app URL is not configured.")
    anonymous = bool(config.get("anonymous_upload", True))
    secret = os.getenv("GOOGLE_DRIVE_UPLOAD_SECRET", "").strip()
    if not anonymous and not secret:
        raise RuntimeError("GOOGLE_DRIVE_UPLOAD_SECRET is required for protected upload.")
    ensure_learning_files(root / "data")
    files = [root / "data/knowledge_base.jsonl",
             root / "data/training/active_prompt_profile.json"]
    now = datetime.now(timezone.utc)
    date_folder = now.strftime("%Y_%m_%d")
    stamp = now.strftime("%Y_%m_%d_%H_%M_%S")
    installation_id = normalize_installation_id(str(config.get("installation_id", "")))
    if installation_id != config.get("installation_id"):
        save_config(installation_id=installation_id)
    uploaded: list[str] = []
    for path in files:
        is_kb = path.name == "knowledge_base.jsonl"
        kind = "KB" if is_kb else "prompting"
        prefix = "KB" if is_kb else "Pro"
        name = f"{prefix}_{stamp}_{installation_id}{path.suffix}"
        response = requests.post(url, json={
            "filename": name, "mime_type": "application/json",
            "date_folder": date_folder, "kind": kind,
            "timestamp": stamp, "installation_id": installation_id,
            "content_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
            "secret": "" if anonymous else secret,
        }, timeout=60)
        result = _response_json(response, f"upload of {name}")
        uploaded.append(str(result.get("path", result.get("name", name))))
    _last_sync_path().write_text(json.dumps({
        "completed_at": datetime.now(timezone.utc).isoformat(), "uploaded": uploaded,
    }, indent=2), encoding="utf-8")
    return uploaded


def sync_if_due() -> list[str]:
    config = load_config()
    return sync_now() if config.get("enabled") and _is_due(config) else []
