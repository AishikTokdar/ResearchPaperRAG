"""Enforce a wall-clock timeout around native PDF parsing, including individual pages."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ..config import get_settings


def extract_pdf(path: str) -> dict:
    settings = get_settings()
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(__file__).with_name("pdf_extract_worker.py")),
                path,
                str(settings.max_pdf_pages),
                str(settings.max_extracted_chars),
                str(settings.pdf_memory_limit_mb),
            ],
            capture_output=True,
            timeout=30,
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        raise ValueError("PDF extraction exceeded the processing limit") from None
    except subprocess.CalledProcessError:
        raise ValueError("PDF could not be parsed") from None
    data = json.loads(result.stdout)
    if "error" in data:
        raise ValueError(data["error"])
    return data


def extract_pdf_bytes(data: bytes) -> dict:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as file:
        file.write(data)
        path = file.name
    try:
        return extract_pdf(path)
    finally:
        os.unlink(path)
