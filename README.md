# ResearchPaperRAG

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Vite](https://img.shields.io/badge/Vite-5.4+-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![React](https://img.shields.io/badge/React-18.3+-blue?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4+-blue?logo=typescript)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4+-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue?logo=docker&logoColor=white)](https://www.docker.com/)

ResearchPaperRAG is a state-of-the-art, open-source Retrieval-Augmented Generation (RAG) platform designed for multi-document indexing, intelligent synthesis, and context-aware chat interaction. It combines local CPU embeddings, FAISS vector search, a 7-stage agent pipeline, and real-time Server-Sent Events (SSE) streaming with multi-provider AI model failover.

- **GitHub Repository:** [https://github.com/AishikTokdar/ResearchPaperRAG](https://github.com/AishikTokdar/ResearchPaperRAG)

---

## Table of Contents

- [Core Capabilities](#core-capabilities)
- [System Architecture & Data Flow](#system-architecture--data-flow)
- [Component Breakdown & Context](#component-breakdown--context)
- [Smart Zero-Config Defaults Architecture](#smart-zero-config-defaults-architecture)
- [Deployment Guides](#deployment-guides)
  - [Option 1: Hugging Face Spaces (Backend Docker / Python SDK)](#option-1-hugging-face-spaces-backend-docker--python-sdk)
  - [Option 2: Vercel (Frontend) + Render (Backend)](#option-2-vercel-frontend--render-backend)
  - [Option 3: PythonAnywhere (Backend Web Service)](#option-3-pythonanywhere-backend-web-service)
  - [Option 4: Docker & Docker Compose (Local / Self-Hosted / Coolify)](#option-4-docker--docker-compose-local--self-hosted--coolify)
- [Local Bash Deployment Guide](#local-bash-deployment-guide)
- [Supported AI Models & API Keys Guide](#supported-ai-models--api-keys-guide)
- [Environment Configuration (.env Reference)](#environment-configuration-env-reference)
- [API Reference & Interactive Documentation](#api-reference--interactive-documentation)
- [Tech Stack](#tech-stack)
- [License](#license)

---

## Core Capabilities

- **Multi-Document Ingestion**: Upload up to 3 PDF documents simultaneously with a combined size limit of 50 MB.
- **Dual Knowledge Modes**:
  - **Hybrid Brain Mode**: Combines retrieved PDF citations with the AI's internal pretrained world knowledge for synthesized reasoning.
  - **Strict to Source Mode**: Enforces strict adherence to PDF context only, stating when information is absent.
- **Local Zero-Key Embeddings**: Uses Hugging Face `sentence-transformers/all-MiniLM-L6-v2` running on CPU for vector embeddings, requiring zero external embedding API keys.
- **7-Stage Multi-Agent Pipeline**: Executes Extractor, Analyzer, Preprocessor, Optimizer, Synthesizer, Validator, and Assembler stages for maximum answer grounding and reliability.
- **Multi-Provider Failover**: Automatically switches between Google Gemini, Groq, Cerebras, SambaNova, Hugging Face, and OpenRouter if a key or model hits rate limits.
- **SSE Token Streaming**: Real-time token-by-token streaming responses over Server-Sent Events.
- **Formatted Chat Exports**: One-click exports of full conversation history to clean `.txt` files or print-formatted `.pdf` documents.
- **Anonymous Session Isolation**: Browser-side Web Crypto UUID isolation ensures per-tab vector store privacy without mandatory user logins.

---

## System Architecture & Data Flow

```text
+-----------------------------------------------------------------------------------------------+
|                                    RESEARCHPAPERRAG SYSTEM ARCHITECTURE                       |
+-----------------------------------------------------------------------------------------------+

  [ CLIENT LAYER ] - Browser SPA
  +---------------------------------------------------------------------------------------------+
  |  React 18 SPA (Vite + Tailwind CSS + Framer Motion)                                         |
  |  ├── Anonymous Session Generator (Web Crypto UUID v4 -> X-Chat-Session-Id header)           |
  |  ├── Interactive Chat Stream & Markdown Formatting Engine (Inline Citation Pills)            |
  |  ├── Knowledge Source Mode Switch (Hybrid Brain vs. Strict to Source)                       |
  |  └── Client Storage & Exporters (IndexedDB Chat History, Text .txt & PDF .pdf Exports)       |
  +---------------------------------------------------------------------------------------------+
                                                |
                      HTTP API Requests & SSE Real-time Token Stream
                                                |
                                                v
  [ INGESTION & VECTOR LAYER ] - Backend Pipeline
  +---------------------------------------------------------------------------------------------+
  |  1. PDF Ingestion & Document Processing                                                     |
  |     └── Upload Multi-PDF (up to 3 files, cumulative <= 50 MB)                               |
  |     └── PyPDF Loader -> Text Extraction -> RecursiveCharacterTextSplitter                   |
  |                                                                                             |
  |  2. Local Zero-Key Vector Engine                                                            |
  |     └── HuggingFace sentence-transformers/all-MiniLM-L6-v2 (Runs 100% locally on CPU)        |
  |     └── FAISS Dense Vector Store (Isolated per X-Chat-Session-Id in faiss_index/sessions/)  |
  +---------------------------------------------------------------------------------------------+
                                                |
                                      Context Vector Retrieval
                                                |
                                                v
  [ REASONING & PIPELINE LAYER ] - 7-Stage Agent Engine
  +---------------------------------------------------------------------------------------------+
  |  3. Multi-Agent RAG Orchestration                                                           |
  |     ├── [Stage 1: Extractor]   -> Top-k similarity retrieval from session FAISS index         |
  |     ├── [Stage 2: Analyzer]    -> Document context relevance filtering & deduplication      |
  |     ├── [Stage 3: Preprocess]  -> Text cleaning & prompt normalization                       |
  |     ├── [Stage 4: Optimizer]   -> Token window trimming & document chunk context packing     |
  |     ├── [Stage 5: Synthesizer] -> Mode-based prompt construction (Hybrid vs. Strict)        |
  |     ├── [Stage 6: Validator]   -> Fact grounding & safety validation                        |
  |     └── [Stage 7: Assembler]   -> Format answer text, metadata & citation pills             |
  +---------------------------------------------------------------------------------------------+
                                                |
                                 Multi-Provider Model API Calls
                                                |
                                                v
  [ AI PROVIDER FAILOVER LAYER ] - 6 AI Platforms / 22+ Models
  +---------------------------------------------------------------------------------------------+
  |  4. Failover Order: Google Gemini -> Groq LPU -> Cerebras -> SambaNova -> HF -> OpenRouter  |
  |     ├── Google Gemini: gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash                  |
  |     ├── Groq LPU: llama-3.3-70b-versatile, llama-3.1-8b-instant, deepseek-r1-distill-70b   |
  |     ├── Cerebras WSE: llama3.3-70b, llama3.1-8b (2000+ tokens/sec)                          |
  |     ├── SambaNova Cloud: Meta-Llama-3.3-70B-Instruct, DeepSeek-R1-Distill-Llama-70B        |
  |     ├── Hugging Face: Qwen2.5-Coder-32B-Instruct, Mistral-7B-Instruct                      |
  |     └── OpenRouter: llama-3.3-70b-instruct:free, deepseek-r1:free, qwen-2.5-72b:free       |
  +---------------------------------------------------------------------------------------------+
```

---

## Component Breakdown & Context

### 1. React 18 Single Page Application (Frontend)
- **Context in Project**: Provides the modern interactive user interface. It manages real-time streaming displays, file dropzones, multi-document badges, theme toggling, and export options.
- **Key Responsibilities**: Renders Markdown bolding/lists, formats inline document citation pills (`[Doc - Page X]`), and maintains client-side chat state in IndexedDB.

### 2. Anonymous Session Isolation (`X-Chat-Session-Id`)
- **Context in Project**: Allows instant, privacy-respecting multi-tenant document indexing without requiring user registration or account databases.
- **Key Responsibilities**: A unique UUID v4 is generated in the browser using Web Crypto API and attached to every API request header. The backend uses this ID to scope FAISS vector stores in `faiss_index/sessions/<uuid>/`.

### 3. Local CPU Embedding Service (`sentence-transformers`)
- **Context in Project**: Converts extracted text chunks into 384-dimensional dense vector representations.
- **Key Responsibilities**: Operates locally on CPU using `sentence-transformers/all-MiniLM-L6-v2`. This eliminates third-party embedding API costs, eliminates embedding quota errors, and allows zero-key document ingestion.

### 4. FAISS Vector Store Engine
- **Context in Project**: Acts as the fast vector search index for similarity retrieval.
- **Key Responsibilities**: Stores vector embeddings and chunk metadata. When a user asks a question, FAISS computes L2 distance / cosine similarity to return the top-k most relevant document excerpts.

### 5. 7-Stage Multi-Agent Pipeline
- **Context in Project**: Ensures answers are strictly grounded, high-quality, and free of hallucination.
- **Key Responsibilities**:
  1. **Extractor**: Retrieves top-k raw chunks from FAISS.
  2. **Analyzer**: Filters duplicate or low-similarity text chunks.
  3. **Preprocessor**: Cleans formatting anomalies and standardizes text.
  4. **Optimizer**: Trims context to fit the selected LLM's token context window.
  5. **Synthesizer**: Constructs the grounded RAG prompt based on selected Knowledge Mode.
  6. **Validator**: Checks generated output for safety and factual grounding.
  7. **Assembler**: Packages the final response with model metadata and citation pills.

---

## Smart Zero-Config Defaults Architecture

ResearchPaperRAG is built with **Smart Zero-Config Defaults**. You do **not** need to fill out a long `.env` file with dozens of technical variables.

### How It Works:
1. **You Only Supply API Keys**: All you need to supply in your deployment environment is at least one AI provider API key (such as `GOOGLE_API_KEY` or `GROQ_API_KEY`).
2. **Pre-configured Defaults**: All system settings automatically fallback to optimal built-in default values:
   - `CORS_ORIGINS`: Defaults to wildcard `*` or local dev URLs (`http://localhost:5173`).
   - `FAISS_PERSIST_DIR`: Defaults to `faiss_index`.
   - `CHUNK_SIZE`: Defaults to `1000`.
   - `CHUNK_OVERLAP`: Defaults to `200`.
   - `RETRIEVAL_K`: Defaults to `4`.
   - `MAX_VECTOR_SESSIONS`: Defaults to `64`.
   - `FAISS_SESSION_MAX_AGE_DAYS`: Defaults to `3`.
   - `RATE_LIMIT_UPLOAD_PER_MINUTE`: Defaults to `8`.
   - `RATE_LIMIT_ASK_PER_MINUTE`: Defaults to `90`.
3. **Optional Overrides**: If you want to customize any of these values, you can set them in your environment variables. Otherwise, leave them unset and the system handles them automatically.

---

## Deployment Guides

### Option 1: Hugging Face Spaces (Backend ZeroGPU Gradio)

Hugging Face Spaces provides a **100% FREE Tier (2 vCPU • 16 GB RAM / ZeroGPU Hardware)** with **zero credit card required** when using the native **Gradio SDK** (Python environment).

#### Key Deployment Architecture:
- **`app.py`**: Entrypoint for Hugging Face Spaces. Uses `@spaces.GPU` probe to register with ZeroGPU hardware scheduling and mounts the FastAPI application (`from app.main import app as fastapi_app`) via `gr.mount_gradio_app(fastapi_app, demo, path="/", ssr_mode=False)`.
- **`gradio_app.py`**: Standalone native Gradio 5.x UI dashboard featuring PDF uploading, RAG chat, model selector, and system health tabs.
- **REST API Endpoints**: Exposes interactive Swagger UI at `/docs` and ReDoc at `/redoc`.

#### Step 1: Create a Space on Hugging Face
1. Log in to [Hugging Face](https://huggingface.co/) (Create a free account if needed).
2. Go to [huggingface.co/new-space](https://huggingface.co/new-space).
3. **Space Name**: `researchpaperrag-backend`.
4. **License**: `mit`.
5. **Select the Space SDK**: **Gradio**.
6. **Space Hardware**: **CPU Basic • 2 vCPU • 16 GB RAM** (Free) or **ZeroGPU**.
7. Visibility: **Public** or **Private**.
8. Click **Create Space**.

#### Step 2: Push Repository Code & Entrypoint
Upload the files inside `backend/` to the root of your Hugging Face Space repository:

```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/researchpaperrag-backend
cd researchpaperrag-backend

# Copy all files from your local ResearchPaperRAG/backend/ into this directory
# Ensure app.py, gradio_app.py, requirements.txt, and app/ are in the root of the Space

git add .
git commit -m "Deploy ResearchPaperRAG ZeroGPU Gradio Backend"
git push origin main
```

#### Step 3: Configure Environment Secrets (Hide API Keys)
1. In your Space, navigate to **Settings** -> **Variables and Secrets** -> **New Secret**.
2. Add your provider API keys safely:
   - `GOOGLE_API_KEY`: `your_gemini_api_key`
   - `GROQ_API_KEY`: `your_groq_api_key`
   - `CORS_ORIGINS`: `*`
3. Hugging Face Spaces will automatically build the environment, launch your backend on port `7860`, and expose both the interactive Gradio UI and FastAPI REST endpoints.

---

## Option 2: Vercel (Frontend) + Hugging Face (Backend)

Decouple the frontend Single Page Application (hosted on Vercel's global Edge CDN) from the Python AI backend service running on Hugging Face Spaces. **100% free with zero credit card required**.

#### Step 1: Obtain Hugging Face Backend Direct URL
Deploy your backend to Hugging Face Spaces (Option 1 above). Note your Space's direct backend URL:
`https://YOUR_USERNAME-researchpaperrag-backend.hf.space`

#### Step 2: Deploy Frontend to Vercel
1. Log in to [Vercel](https://vercel.com/).
2. Click **Add New...** -> **Project** and import your repository (`ResearchPaperRAG`).
3. Set **Root Directory**: `frontend`.
4. **Framework Preset**: Vite.
5. Add Environment Variables:
   - `VITE_API_BASE_URL` = `https://YOUR_USERNAME-researchpaperrag-backend.hf.space`
6. Click **Deploy**. Vercel will build and distribute the React SPA globally.

---

### Option 3: Render (Backend) - Free Tier Limitation Note

You can also deploy the backend service to [Render](https://render.com/) as a Docker Web Service or Python Web Service.

> [!WARNING]
> **Render Free Tier RAM Limitation Note**:
> Render's free web service tier limits memory allocation to **512 MB RAM**. Loading PyTorch CPU runtime, Hugging Face `sentence-transformers/all-MiniLM-L6-v2` embedding weights, and FAISS dense vector search during cold startup can consume **450 MB – 600 MB** of RAM. This frequently triggers Out-of-Memory (OOM) `SIGKILL` termination on Render's free tier.
> 
> **Recommendation**: For free cloud deployment, use **Hugging Face Spaces** (Option 1 & 2), which provides **16 GB RAM** on its free tier.

#### Deploying on Render (If using paid/higher tier):
1. Log in to [Render](https://render.com/) and click **New +** -> **Web Service**.
2. Connect repository and set **Root Directory**: `backend`.
3. Set **Runtime**: **Docker** (uses `backend/Dockerfile`) or **Python 3**.
4. Set **Start Command** (for Python runtime): `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Add Environment Variables: `GOOGLE_API_KEY`, `GROQ_API_KEY`, `CORS_ORIGINS=*`, `WEB_CONCURRENCY=1`.

---

### Option 4: Docker & Docker Compose Deployment

For self-hosted VPS servers (Coolify, Hetzner, AWS EC2, DigitalOcean) or local containerized testing.

#### Method A: Standalone Backend Docker Container
```bash
cd backend

# Build Docker image
docker build -t researchpaperrag-backend .

# Run container with environment file
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  --name researchpaperrag-backend \
  researchpaperrag-backend
```

#### Method B: Docker Compose (Full Stack: Frontend + Backend)
1. Create `backend/.env` from template:
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env and add GOOGLE_API_KEY or GROQ_API_KEY
   ```
2. Launch full-stack container services:
   ```bash
   docker compose up --build
   ```
3. Active Endpoints:
   - **React Frontend SPA**: `http://localhost:5173`
   - **FastAPI Backend API**: `http://localhost:8000`
   - **Swagger UI Sandbox**: `http://localhost:8000/docs`

---

## Local CLI / Bash Deployment Guide

Run ResearchPaperRAG natively on your local machine using standard terminal commands.

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18+ and npm 9+
- Git

### 1. Clone Repository
```bash
git clone https://github.com/AishikTokdar/ResearchPaperRAG.git
cd ResearchPaperRAG
```

### 2. Backend Local CLI Setup
```bash
cd backend

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows PowerShell: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment file
cp .env.example .env
# Edit backend/.env and add your API key (e.g. GOOGLE_API_KEY or GROQ_API_KEY)

# Launch backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Local CLI Setup (New Terminal)
```bash
cd frontend

# Install dependencies
npm install
cp .env.example .env
npm run dev
```

---

## Supported AI Models & API Keys Guide

ResearchPaperRAG supports 6 AI providers offering access to over 22 models. You only need to configure at least one valid key in your environment.

### 1. Google Gemini API Key (`GOOGLE_API_KEY`)
- **Supported Models**: `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`.
- **How to Get**:
  1. Visit [Google AI Studio](https://aistudio.google.com/).
  2. Sign in with your Google account.
  3. Click **Get API Key** -> **Create API key in new project** and copy the key.

### 2. Groq LPU API Key (`GROQ_API_KEY`)
- **Supported Models**: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`, `deepseek-r1-distill-llama-70b`.
- **How to Get**:
  1. Visit [Groq Console](https://console.groq.com/).
  2. Navigate to **API Keys** -> **Create API Key** and copy the key.

### 3. Cerebras Wafer-Scale Engine Key (`CEREBRAS_API_KEY`)
- **Supported Models**: `llama3.3-70b`, `llama3.1-8b`.
- **How to Get**:
  1. Visit [Cerebras Cloud Console](https://cloud.cerebras.ai/).
  2. Go to **API Keys** -> **Create New Key** and copy the key.

### 4. SambaNova Cloud Key (`SAMBANOVA_API_KEY`)
- **Supported Models**: `Meta-Llama-3.3-70B-Instruct`, `DeepSeek-R1-Distill-Llama-70B`, `Qwen2.5-72B-Instruct`.
- **How to Get**:
  1. Visit [SambaNova Cloud Portal](https://cloud.sambanova.ai/).
  2. Access **API Keys** and generate your key.

### 5. Hugging Face Access Token (`HF_API_KEY`)
- **Supported Models**: `Qwen/Qwen2.5-Coder-32B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.3`.
- **How to Get**:
  1. Visit [Hugging Face Settings Tokens](https://huggingface.co/settings/tokens).
  2. Click **Create new token** (Role: Read) and copy the token.

### 6. OpenRouter Key (`OPENROUTER_API_KEY`)
- **Supported Models**: `meta-llama/llama-3.3-70b-instruct:free`, `deepseek/deepseek-r1:free`, `qwen/qwen-2.5-72b-instruct:free`.
- **How to Get**:
  1. Visit [OpenRouter Keys](https://openrouter.ai/keys).
  2. Click **Create Key** and copy your key.

---

## Environment Configuration (.env Reference)

### Minimum Backend Environment (`backend/.env`)
Only your chosen API keys are required:
```env
GOOGLE_API_KEY=your_google_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### Full Optional Backend Configuration Reference (`backend/.env`)
```env
# Server Settings
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production

# CORS Origins (Use * or comma-separated origins)
CORS_ORIGINS=*

# AI API Keys (Configure at least one)
GOOGLE_API_KEY=your_google_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
CEREBRAS_API_KEY=your_cerebras_api_key_here
SAMBANOVA_API_KEY=your_sambanova_api_key_here
HF_API_KEY=your_huggingface_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Default Model Selection
DEFAULT_MODEL=gemini-2.5-flash
DEFAULT_PROVIDER=gemini

# Vector Store & Session Limits
MAX_FILE_SIZE=52428800
FAISS_PERSIST_DIR=faiss_index
MAX_VECTOR_SESSIONS=64
FAISS_SESSION_MAX_AGE_DAYS=3

# IP Rate Limits (0 to disable)
RATE_LIMIT_UPLOAD_PER_MINUTE=8
RATE_LIMIT_ASK_PER_MINUTE=90
```

### Frontend Environment Reference (`frontend/.env`)
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## API Reference & Interactive Documentation

ResearchPaperRAG provides auto-generated interactive OpenAPI / Swagger UI documentation out of the box.

### Interactive API Explorer Endpoints:
- **Swagger UI Sandbox**: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)
- **ReDoc Technical View**: [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc)
- **Raw OpenAPI Schema**: [`http://127.0.0.1:8000/openapi.json`](http://127.0.0.1:8000/openapi.json)

### API Endpoints Overview:

All protected state endpoints accept an optional `X-Chat-Session-Id` header (UUID v4) for session isolation.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/docs` | Interactive Swagger UI API documentation & testing sandbox |
| `GET` | `/redoc` | ReDoc API specification documentation view |
| `GET` | `/openapi.json` | OpenAPI 3.1 JSON schema definition |
| `GET` | `/` | System health and API basic info |
| `GET` | `/health` | Live backend health status check |
| `GET` | `/models` | List supported AI models & credential availability |
| `GET` | `/status` | Session vector store loaded status |
| `POST` | `/upload` | Upload PDF files (up to 3 files, combined <= 50 MB) |
| `POST` | `/ask` | Submit question (Non-streaming JSON response) |
| `POST` | `/ask/stream` | Submit question (SSE real-time token streaming) |
| `GET` | `/runtime-summary` | Provider health metrics dashboard |

---

## Tech Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Vanilla Tailwind CSS & Framer Motion
- **Icons**: Lucide React
- **Storage**: Browser IndexedDB & Web Storage

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Server**: Uvicorn ASGI
- **Vector Search**: FAISS CPU
- **Embeddings**: Hugging Face `sentence-transformers/all-MiniLM-L6-v2`
- **PDF Processing**: PyPDF & LangChain Text Splitters
- **Validation**: Pydantic v2

---

## License

This project is licensed under the [MIT License](LICENSE). Feel free to inspect, customize, and extend ResearchPaperRAG for personal, educational, or commercial applications.
