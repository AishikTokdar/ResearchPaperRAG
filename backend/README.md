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

# ResearchPaperRAG Backend API

This repository holds the FastAPI + Gunicorn backend for **ResearchPaperRAG**—a multi-source academic paper retrieval, RAG vector indexing, and 8-layer literature synthesis engine.

### Key REST API Endpoints:
- `GET /health`: Connection health check
- `GET /api/search`: Concurrent literature retrieval across 6 academic APIs (arXiv, Crossref, Semantic Scholar, OpenAlex, PubMed, DOAJ) with 3-year publication filter
- `POST /api/analyze`: 8-layer structured RAG research gap synthesis
- `POST /api/chat`: Grounded follow-up Q&A chat
- `POST /upload`: Custom PDF paper ingestion & text extraction
- `GET /models`: List pre-configured AI models & provider availability
- `GET /pipeline-info`: 7-stage processing pipeline telemetry

### Production Gunicorn Launch Command:
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
