"""Compatibility entrypoint for the session-isolated API.

Both ``uvicorn backend.main:app`` and ``python backend/main.py`` use the same
application and security controls as ``backend.app.main:app``.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = str(Path(__file__).resolve().parents[1])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.main import app  # noqa: E402

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), proxy_headers=False)
