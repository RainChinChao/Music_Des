"""First-run checks and safe local-service helpers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

PLACEHOLDER_PARTS = ("/absolute/path/", "your-soundfont", "path/to/")
DEFAULT_SOUNDFONT_URL = (
    "https://ftp.osuosl.org/pub/musescore/soundfont/"
    "MuseScore_General/MuseScore_General.sf3"
)
DEFAULT_SOUNDFONT_LICENSE_URL = (
    "https://ftp.osuosl.org/pub/musescore/soundfont/"
    "MuseScore_General/MuseScore_General_License.md"
)


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""


def is_placeholder_path(value: str | Path | None) -> bool:
    text = str(value or "").strip().lower()
    return not text or any(part in text for part in PLACEHOLDER_PARTS)


def soundfont_search_roots() -> list[Path]:
    home = Path.home()
    roots = [home / "Downloads", home / "Documents", home / "Music",
             home / "Library/Audio/Sounds/Banks", Path("/Library/Audio/Sounds/Banks")]
    # MuseScore application resources are common on macOS.
    roots.extend(Path("/Applications").glob("MuseScore*.app/Contents/Resources"))
    return roots


def discover_soundfonts(max_results: int = 50) -> list[Path]:
    found: set[Path] = set()
    configured = os.getenv("SOUNDFONT_PATH", "")
    if not is_placeholder_path(configured):
        candidate = Path(configured).expanduser()
        if candidate.is_file() and candidate.suffix.lower() in {".sf2", ".sf3"}:
            found.add(candidate.resolve())
    for root in soundfont_search_roots():
        if not root.exists():
            continue
        try:
            for pattern in ("*.sf2", "*.sf3"):
                for path in root.rglob(pattern):
                    if path.is_file():
                        found.add(path.resolve())
                        if len(found) >= max_results:
                            return sorted(found)
        except (OSError, PermissionError):
            continue
    return sorted(found)


def install_default_soundfont(destination: str | Path | None = None) -> Path:
    """Install MuseScore General and its MIT notice into the user's Music folder."""
    target_dir = (Path(destination).expanduser() if destination else
                  Path.home() / "Music" / "SoundFonts")
    target_dir.mkdir(parents=True, exist_ok=True)
    font_path = target_dir / "MuseScore_General.sf3"
    license_path = target_dir / "MuseScore_General_LICENSE.txt"
    for url, path in ((DEFAULT_SOUNDFONT_URL, font_path),
                      (DEFAULT_SOUNDFONT_LICENSE_URL, license_path)):
        if path.exists() and path.stat().st_size:
            continue
        partial = path.with_suffix(path.suffix + ".part")
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "GenAI-MIDI-Studio/4.0"})
            with urllib.request.urlopen(request, timeout=120) as response, \
                    partial.open("wb") as handle:
                shutil.copyfileobj(response, handle)
            if partial.stat().st_size == 0:
                raise RuntimeError(f"Downloaded an empty file from {url}")
            partial.replace(path)
        except Exception as exc:
            partial.unlink(missing_ok=True)
            raise RuntimeError(
                f"Could not download {path.name} from {url}: {exc}") from exc
    return font_path.resolve()


def resolve_soundfont(value: str | Path | None = None) -> Path:
    if not is_placeholder_path(value):
        path = Path(str(value)).expanduser().resolve()
        if path.is_file() and path.suffix.lower() in {".sf2", ".sf3"}:
            return path
    candidates = discover_soundfonts()
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        lines = "\n".join(f"  - {p}" for p in candidates[:10])
        raise ValueError("Select one discovered SoundFont in the GUI or pass its exact path:\n" + lines)
    raise ValueError(
        "No SoundFont was found. Download a licensed General MIDI .sf2/.sf3 file, "
        "place it in ~/Downloads or ~/Music, then run music-doctor again."
    )


def ollama_tags(base_url: str = "http://localhost:11434", timeout: float = 2.0) -> list[str]:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/tags", timeout=timeout) as response:
            data = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(
            "Ollama is installed but its server is not reachable. Run `brew services start ollama` "
            "or keep `ollama serve` running in another terminal."
        ) from exc
    return [str(item.get("name", "")) for item in data.get("models", [])]


def model_is_installed(model: str, names: list[str]) -> bool:
    requested = model if ":" in model else model + ":latest"
    return any((name if ":" in name else name + ":latest") == requested for name in names)


def start_ollama(timeout: float = 12.0) -> None:
    if not shutil.which("ollama"):
        raise RuntimeError("Ollama is not installed. Run `brew install ollama`.")
    try:
        ollama_tags(); return
    except RuntimeError:
        pass
    log = open(Path(os.getenv("TMPDIR", "/tmp")) / "genai-midi-ollama.log", "a", encoding="utf-8")
    subprocess.Popen(["ollama", "serve"], stdout=log, stderr=log,
                     start_new_session=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.5)
        try:
            ollama_tags(); return
        except RuntimeError:
            continue
    raise RuntimeError("Ollama did not start. Inspect /tmp/genai-midi-ollama.log.")


def pull_ollama_model(model: str = "qwen2.5:7b-instruct") -> None:
    start_ollama()
    subprocess.run(["ollama", "pull", model], check=True)


def run_checks(model: str = "qwen2.5:7b-instruct") -> list[Check]:
    checks = []
    for command, install in (("fluidsynth", "brew install fluid-synth"),
                             ("ffmpeg", "brew install ffmpeg"),
                             ("ollama", "brew install ollama")):
        path = shutil.which(command)
        checks.append(Check(command, bool(path), path or "not found", "" if path else install))
    if shutil.which("ollama"):
        try:
            names = ollama_tags()
            checks.append(Check("Ollama server", True, "http://localhost:11434"))
            installed = model_is_installed(model, names)
            checks.append(Check("Local model", installed, model,
                                "" if installed else f"ollama pull {model}"))
        except RuntimeError as exc:
            checks.append(Check("Ollama server", False, str(exc), "brew services start ollama"))
            checks.append(Check("Local model", False, model, f"ollama pull {model}"))
    fonts = discover_soundfonts()
    checks.append(Check("SoundFont", bool(fonts), str(fonts[0]) if fonts else "none found",
                        "Download a licensed .sf2/.sf3 into ~/Downloads or ~/Music" if not fonts else ""))
    return checks
