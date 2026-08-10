from pathlib import Path
from unittest.mock import patch

import pytest

from deterministic_midi.system_setup import (is_placeholder_path, model_is_installed,
                                              resolve_soundfont,
                                              install_default_soundfont)


def test_placeholder_paths_are_not_real_configuration():
    assert is_placeholder_path("/absolute/path/to/your-soundfont.sf2")
    assert is_placeholder_path("")
    assert not is_placeholder_path("/Users/test/Music/font.sf2")


def test_model_matching_requires_the_requested_variant():
    assert model_is_installed("qwen2.5:7b-instruct", ["qwen2.5:7b-instruct"])
    assert not model_is_installed("qwen2.5:7b-instruct", ["qwen2.5:latest"])
    assert not model_is_installed("qwen2.5:7b-instruct", ["mistral:latest"])


def test_resolve_soundfont_auto_selects_one(tmp_path):
    font = tmp_path / "General.sf2"; font.write_bytes(b"font")
    with patch("deterministic_midi.system_setup.discover_soundfonts", return_value=[font]):
        assert resolve_soundfont("/absolute/path/to/your-soundfont.sf2") == font


def test_resolve_soundfont_explains_missing_asset():
    with patch("deterministic_midi.system_setup.discover_soundfonts", return_value=[]):
        with pytest.raises(ValueError, match="No SoundFont was found"):
            resolve_soundfont("")


def test_default_soundfont_install_keeps_font_and_license(tmp_path):
    class Response:
        def __init__(self, payload): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read(self, size=-1):
            value, self.payload = self.payload[:size], self.payload[size:]
            return value

    with patch("deterministic_midi.system_setup.urllib.request.urlopen",
               side_effect=[Response(b"sf3"), Response(b"MIT licence")]):
        installed = install_default_soundfont(tmp_path)
    assert installed.read_bytes() == b"sf3"
    assert (tmp_path / "MuseScore_General_LICENSE.txt").read_bytes() == b"MIT licence"
