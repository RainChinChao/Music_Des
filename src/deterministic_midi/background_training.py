from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .memory import SuccessMemory
from .providers import MusicProvider
from .trainer import train_prompt_profile

_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="music-ai-training")
_WRITE_LOCK = threading.Lock()


def _write_status(job_id: str, status: str, detail: str = "") -> None:
    path = Path("data/training/jobs") / f"{job_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "job_id": job_id, "status": status, "detail": detail,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def submit_prompt_training(provider: MusicProvider, memory: SuccessMemory,
                           training_input: dict) -> str:
    """Queue one serialized background prompt-profile update."""
    job_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    _write_status(job_id, "queued")

    def work() -> None:
        _write_status(job_id, "running")
        try:
            with _WRITE_LOCK:
                train_prompt_profile(provider, memory, training_input)
                try:
                    from .cloud_sync import sync_if_due
                    sync_if_due()
                except Exception as sync_exc:
                    _write_status(job_id, "completed", f"Training saved; Google Drive sync: {sync_exc}")
                    return
            _write_status(job_id, "completed", "Runtime prompt profile and knowledge base updated.")
        except Exception as exc:
            _write_status(job_id, "failed", str(exc))

    _EXECUTOR.submit(work)
    return job_id


def read_training_status(job_id: str) -> dict:
    path = Path("data/training/jobs") / f"{job_id}.json"
    if not path.exists():
        return {"job_id": job_id, "status": "unknown", "detail": ""}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"job_id": job_id, "status": "unknown", "detail": "Unreadable status file."}
