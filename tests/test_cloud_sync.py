from unittest.mock import Mock, patch

from deterministic_midi.cloud_sync import (load_config, normalize_installation_id,
                                           save_config, sync_now)
from deterministic_midi.memory import ensure_learning_files


def test_anonymous_google_drive_sync_needs_no_user_or_secret(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); monkeypatch.setenv("DETERMINISTIC_MIDI_CONFIG_DIR", str(tmp_path / "config"))
    (tmp_path / "data").mkdir()
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "src/deterministic_midi").mkdir(parents=True)
    (tmp_path / "data/knowledge_base.jsonl").write_text("{}\n", encoding="utf-8")
    save_config(enabled=True, project_root=str(tmp_path),
                google_drive_web_app_url="https://script.google.com/example",
                anonymous_upload=True)
    response = Mock(status_code=200); response.raise_for_status.return_value = None
    response.json.return_value = {
        "ok": True, "path": "2026_08_10/KB/KB_2026_08_10_14_30_05_test.jsonl"}
    with patch("deterministic_midi.cloud_sync.requests.post", return_value=response) as post:
        result = sync_now()
    assert result[0].startswith("2026_08_10/KB/KB_")
    payloads = [call.kwargs["json"] for call in post.call_args_list]
    assert all(payload["secret"] == "" for payload in payloads)
    assert {payload["kind"] for payload in payloads} == {"KB", "prompting"}
    assert all(payload["date_folder"].count("_") == 2 for payload in payloads)


def test_sync_interval_is_bash_configurable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); monkeypatch.setenv("DETERMINISTIC_MIDI_CONFIG_DIR", str(tmp_path / "config"))
    save_config(interval_seconds=3)
    assert load_config()["interval_seconds"] == 3


def test_installation_id_is_safe_and_stable_for_filenames():
    assert normalize_installation_id(" Rain's Product #01 ") == "RainsProduct01"
    assert normalize_installation_id("fixed_ID-2") == "fixed_ID-2"


def test_initial_learning_files_exist_and_are_not_overwritten(tmp_path):
    kb, profile = ensure_learning_files(tmp_path / "data")
    assert '"record_type": "system_bootstrap"' in kb.read_text(encoding="utf-8")
    assert '"provider": "system"' in profile.read_text(encoding="utf-8")
    kb.write_text('{"custom":true}\n', encoding="utf-8")
    profile.write_text('{"custom":true}', encoding="utf-8")
    ensure_learning_files(tmp_path / "data")
    assert kb.read_text(encoding="utf-8") == '{"custom":true}\n'
    assert profile.read_text(encoding="utf-8") == '{"custom":true}'
