from __future__ import annotations

import subprocess
import sys
import socket
import signal
from pathlib import Path


def available_port(preferred: int = 8501) -> int:
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            probe.bind(("127.0.0.1", 0))
            return int(probe.getsockname()[1])


def main() -> None:
    app = Path(__file__).with_name("streamlit_app.py")
    port = available_port()
    print(f"Opening GenAI MIDI Studio at http://localhost:{port}")
    process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", str(app),
        "--server.address", "127.0.0.1", "--server.port", str(port),
        "--server.headless", "true", "--server.fileWatcherType", "none",
        "--server.enableCORS", "true", "--server.enableXsrfProtection", "true",
        "--browser.serverAddress", "localhost", "--browser.serverPort", str(port),
        "--browser.gatherUsageStats", "false",
    ])

    def stop_server(_signum, _frame) -> None:
        if process.poll() is None:
            process.terminate()

    signal.signal(signal.SIGTERM, stop_server)
    signal.signal(signal.SIGINT, stop_server)
    raise SystemExit(process.wait())


if __name__ == "__main__": main()
