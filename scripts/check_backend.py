"""Portable backend verification using the active Python environment."""

import subprocess
import sys
import tempfile
from pathlib import Path

backend = Path(__file__).resolve().parents[1] / "backend"
with tempfile.TemporaryDirectory(prefix="research-rag-mypy-") as cache:
    commands = [
        ["-m", "ruff", "check", "app"],
        ["-m", "mypy", "--cache-dir", cache, "app"],
        ["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
    ]
    for command in commands:
        print("Checking:", " ".join(command), flush=True)
        result = subprocess.run([sys.executable, "-B", *command], cwd=backend)
        if result.returncode:
            raise SystemExit(result.returncode)
