---
title: ResearchPaperRAG Backend
emoji: 📚
colorFrom: gray
colorTo: green
sdk: gradio
sdk_version: 6.31.0
python_version: "3.12"
app_file: app.py
base_path: /gradio/
pinned: false
---

# ResearchPaperRAG backend

## Upload to Hugging Face directly

Upload the contents of this entire `backend` folder into the root of your Gradio Space, just as before. Keep `README.md`, `app.py`, `app/`, `requirements.txt` and `requirements-api.txt` together at the Space root. No packaging script or separate dependency installation is needed: `requirements.txt` automatically installs the API plus Gradio/Spaces.

Keep your provider keys in Space Secrets and `CORS_ORIGINS` set to your exact Cloudflare Pages origin. Hugging Face's own runtime host is accepted automatically. The Gradio UI opens at `/gradio/`; `/health` and `/docs` expose the backend API. For updates, upload the backend files again; existing Space settings/secrets stay on the platform.

Do not upload local `.env`, `.venv`, cache/index or uploaded-document folders. The default profile includes Gradio; Docker uses `requirements-api.txt` to retain its lean API-only installation.

See the [simple frontend upload instructions](https://github.com/AishikTokdar/ResearchPaperRAG/blob/main/frontend/README.md) and [hosted deployment guide](https://github.com/AishikTokdar/ResearchPaperRAG/blob/main/docs/HOSTED_DEPLOYMENT.md).

The primary deployment is the FastAPI service in `app/main.py`, served by one Uvicorn worker. Use Python 3.12. Configuration is in `.env` or process environment; server credentials are never supplied by the browser.

From this directory, after activating a virtual environment:

```sh
python -m pip install -r requirements-dev.txt
# Copy .env.example to .env and set a real supported provider key.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

For a service supervisor, use `--host 0.0.0.0 --workers 1` without reload. Do not use the removed/deprecated `uvicorn.workers` Gunicorn command. Docker starts this single-worker configuration and runs as an unprivileged user.

The authoritative endpoint list, payloads and streaming events are in [API.md](https://github.com/AishikTokdar/ResearchPaperRAG/blob/main/docs/API.md) and the running `/docs`, `/redoc`, `/openapi.json`. Key routes are `POST /api/papers/search`, `POST /api/papers/ingest`, `POST /api/analyze/gaps`, `POST /api/analyze/stream`, `POST /api/chat/followup`, `DELETE /api/chat/followup`, `POST /upload`, `GET /status`, `POST /ask`, `POST /ask/stream`, `GET /health`, `GET /models`, `GET /runtime-summary` and `GET /pipeline-info`.

All document/research operations require a UUID v4 `X-Chat-Session-Id`. It is a bearer capability, not login authentication. The main research engine and legacy PDF engine are independent; an upload to `/upload` does not populate the workspace's research engine.

## Optional interfaces

The default `requirements.txt` includes Gradio/Spaces; `requirements-gradio.txt` remains a compatibility alias. Use either entrypoint:

- `python app.py`: a small Gradio status page at `/gradio/` mounted alongside the API, suitable for the explicit Hugging Face Gradio profile.
- `python gradio_app.py`: the compatibility PDF-chat interface.

Neither replaces the React research workspace. `spaces` is optional for CPU use; the compatibility adapter handles Gradio 6 messages. The optional dependency profile has the Gradio/Pillow security constraint recorded in [the project README](https://github.com/AishikTokdar/ResearchPaperRAG/blob/main/README.md). Keep it out of the primary API deployment unless separately assessed.

See [deployment](https://github.com/AishikTokdar/ResearchPaperRAG/blob/main/docs/DEPLOYMENT.md), [verification](https://github.com/AishikTokdar/ResearchPaperRAG/blob/main/docs/TESTING.md), and the [feature map](https://github.com/AishikTokdar/ResearchPaperRAG/blob/main/docs/FEATURES.md) for runtime limits and tested scope.
