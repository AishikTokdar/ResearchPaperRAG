---
title: ResearchPaperRAG Backend
emoji: rocket
colorFrom: purple
colorTo: indigo
sdk: gradio
sdk_version: 5.20.0
python_version: "3.12"
app_file: app.py
pinned: false
---

# ResearchPaperRAG Hugging Face Backend API

This Hugging Face Space hosts the FastAPI backend for ResearchPaperRAG only.
The frontend is deployed separately, for example on Vercel, and should call this Space over HTTP. The Hugging Face deployment serves the backend API at `/`, `/docs`, `/redoc`, and the REST endpoints below.

Key endpoints include:
- `/health`
- `/upload`
- `/ask`
- `/ask/stream`
- `/models`
- `/pipeline-info`
- `/runtime-summary`
