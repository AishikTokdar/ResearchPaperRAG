# ResearchPaperRAG: Automated Academic Literature Retrieval & Multi-Paper RAG Gap Synthesis Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Vite](https://img.shields.io/badge/Vite-5.4+-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![React](https://img.shields.io/badge/React-18.3+-blue?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4+-blue?logo=typescript)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4+-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Gunicorn](https://img.shields.io/badge/Gunicorn-22.0+-499848?logo=gunicorn&logoColor=white)](https://gunicorn.org/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue?logo=docker&logoColor=white)](https://www.docker.com/)

ResearchPaperRAG is an open-source Retrieval-Augmented Generation (RAG) platform designed for researchers, computer scientists, academics, and students. It automates multi-source academic paper discovery, enforces a strict 3-year publication window (2024–2026) to capture cutting-edge literature, indexes text layers into local vector stores using zero-cost CPU embeddings, and synthesizes structured 8-Layer Research Analysis & Gap Reports.

The platform incorporates an interactive Research Gap Analyzer SPA powered by a high-performance FastAPI / Gunicorn backend with multi-provider failover across 27+ AI models.

- GitHub Repository: https://github.com/AishikTokdar/ResearchPaperRAG
- Live Local App Access: http://127.0.0.1:5173/chat
- Interactive OpenAPI / Swagger Documentation: http://127.0.0.1:8000/docs

---

## Table of Contents
1. Key Capabilities & Features
2. Structured 8-Layer Literature Synthesis Framework
3. System Architecture & Data Flow
4. Component Breakdown
5. Obtaining & Configuring Free AI API Keys
6. Complete Environment Configuration Reference (.env)
7. Local Quickstart & Execution Guide
8. Production Deployment with Gunicorn & Uvicorn
9. Docker & Containerization Guide
10. Cloud Deployment Options (Hugging Face Spaces Backend & Vercel Frontend)
11. REST API Reference & OpenAPI Specification
12. Troubleshooting & FAQs
13. Tech Stack Summary
14. License & Attribution

---

## Key Capabilities & Features

### 1. 6 Free Academic Search APIs Integration
ResearchPaperRAG conducts concurrent, real-time searches across 6 open-access literature databases without requiring paid subscriptions:
- arXiv API: Computer Science, Artificial Intelligence, Machine Learning, Physics, Mathematics, and Quantitative Biology.
- Crossref API: Global DOI metadata registry covering peer-reviewed conference proceedings and journal articles.
- Semantic Scholar API: Academic graph database providing paper abstracts, citation metrics, and author affiliations.
- OpenAlex API: Fully open global bibliometric database indexing over 250 million scholarly entities.
- PubMed API: National Library of Medicine repository for biomedical, healthcare, and life sciences literature.
- DOAJ API: Directory of Open Access Journals across all scientific disciplines.

### 2. Strict 3-Year Publication Window (2024–2026)
Research results are automatically validated against publication dates and filtered strictly to the current date's 3-year publication window (2024, 2025, 2026). This filters out outdated methodologies and forces the gap analysis engine to focus exclusively on contemporary state-of-the-art research.

### 3. Max 5-Paper Focused RAG Knowledge Base
Users can select up to 5 research papers (or attach custom PDF files up to 50 MB cumulative size) per gap analysis run, expanding multi-document synthesis while maintaining high-precision context retrieval.

### 4. Direct New-Tab Paper Access
Every fetched paper in the interactive search list includes direct external links (url / pdf_url / doi). Clicking any paper card immediately opens the original publisher document or PDF in a new browser tab.

### 5. Grounded Interactive Chat with Citation Badges
Following the 8-layer report synthesis, users can conduct follow-up Q&A strictly grounded in the ingested paper texts. Inline citations ([Paper Title, 2026, Section 3.2]) clean out raw Markdown formatting symbols and render as compact, styled inline pills.

### 6. Multi-Format Exporters (.pdf, .md, .txt)
- Print PDF Export (.pdf): Generates a clean print-styled document with custom CSS table styling and triggers native browser printing.
- Raw Markdown Export (.md): Saves full report markdown with H2 section card dividers.
- Plain Text Export (.txt): Strips markdown symbols for unformatted text logging.

### 7. Internal AI Model Selector & Save Action Bar
Redesigned model management bar eliminates raw text input boxes and manual API key fields. Users select from a pre-configured 27-model registry, click "Save Model", and receive instant toast notifications (Active AI Model Saved: Llama 3.3 70B Versatile (GROQ)) and UI badges.

---

## Structured 8-Layer Literature Synthesis Framework

When papers are ingested, ResearchPaperRAG executes cross-document retrieval and passes chunks through an 8-layer prompt orchestration engine:

| Layer | Section Name | Analytical Focus & Content Output |
| :---: | :--- | :--- |
| 1 | Literature Summary | Core research objectives, primary datasets, model architectures, and key empirical takeaways from each selected paper. |
| 2 | Trend Detection | Architectural shifts, dataset evolutions, and algorithmic trends observed across the 2024–2026 publication timeline. |
| 3 | Common Methods | Shared baseline models, evaluation metrics (F1, BLEU, ROUGE, Accuracy), data preprocessing pipelines, and loss functions. |
| 4 | Limitations | Methodological bottlenecks, hardware/compute constraints, domain generalization failures, and dataset distribution bias. |
| 5 | Contradictions | Conflicting findings, empirical discrepancies, and opposing experimental results between the analyzed papers. |
| 6 | Research Gaps | Explicitly stated and implicitly discovered research gaps, unaddressed edge cases, and missing benchmarks. |
| 7 | Future Directions | Strategic roadmap items, recommended theoretical extensions, and concrete algorithmic scaling proposals. |
| 8 | Novel Paper Suggestions | Actionable novel research paper titles, problem formulations, and thesis project concepts for researchers. |

---

## System Architecture & Data Flow

```text
+-----------------------------------------------------------------------------------------------+
|                                RESEARCHPAPERRAG ARCHITECTURE MAP                              |
+-----------------------------------------------------------------------------------------------+

  [ CLIENT LAYER ] - React 18 Single Page Application (Vite + Tailwind CSS + Framer Motion)
  +---------------------------------------------------------------------------------------------+
  |  - Multi-Source Search Bar (arXiv, Crossref, Semantic Scholar, OpenAlex, PubMed, DOAJ)      |
  |  - 3-Year Date Filter (Strict 2024–2026 publication validation)                             |
  |  - Max 5-Paper Selection checklist & PDF drag-and-drop file dropzone                       |
  |  - Internal Model Selector Dropdown & "Save Model" Action Bar                              |
  |  - 8-Layer Structured Report Card Renderer                                                   |
  |  - Compact Inline Citation Badge Normalizer ([Paper Title, Year, Section])                   |
  |  - Multi-Format Exporters (Print .pdf, Raw .md, Plain .txt)                                 |
  +---------------------------------------------------------------------------------------------+
                                                |
                      REST API Requests (/api/search, /api/analyze, /api/chat)
                                                |
                                                v
  [ BACKEND LAYER ] - FastAPI / Gunicorn WSGI Engine (Python 3.11+)
  +---------------------------------------------------------------------------------------------+
  |  1. Concurrent Academic Search Fetcher                                                      |
  |     - Parallel HTTP requests via aiohttp to 6 academic search provider APIs                 |
  |     - Abstract extraction, DOI mapping, and publication year filtering (>= 2024)            |
  |                                                                                             |
  |  2. PDF Ingestion & Document Processing                                                     |
  |     - PyPDF Loader -> Text Extraction -> RecursiveCharacterTextSplitter (chunk_size=1000)   |
  |                                                                                             |
  |  3. Local CPU Zero-Key Vector Engine                                                        |
  |     - HuggingFace sentence-transformers/all-MiniLM-L6-v2 (100% CPU local embeddings)        |
  |     - FAISS / Chroma Vector Stores (Per-session UUID directory isolation)                   |
  +---------------------------------------------------------------------------------------------+
                                                |
                                      Vector Context Retrieval
                                                |
                                                v
  [ SYNTHESIS ENGINE ] - 7-Stage Multi-Agent Orchestration
  +---------------------------------------------------------------------------------------------+
  |  - [Stage 1: Extractor]   -> Similarity search retrieval from session vector store          |
  |  - [Stage 2: Analyzer]    -> Context relevance scoring & chunk deduplication                |
  |  - [Stage 3: Preprocess]  -> Text cleaning & whitespace normalization                       |
  |  - [Stage 4: Optimizer]   -> Token window trimming to fit target LLM context budget         |
  |  - [Stage 5: Synthesizer] -> 8-Layer Prompt Construction & comparative matrix generation      |
  |  - [Stage 6: Validator]   -> Fact grounding & uncertainty marker verification               |
  |  - [Stage 7: Assembler]   -> Response packaging with citation badges and telemetry         |
  +---------------------------------------------------------------------------------------------+
                                                |
                                 Multi-Provider Model API Calls
                                                |
                                                v
  [ AI PROVIDER FAILOVER LAYER ] - 6 AI Cloud Platforms / 27+ Pre-configured Models
  +---------------------------------------------------------------------------------------------+
  |  - Groq LPU (Primary Default): llama-3.3-70b-versatile, deepseek-r1-distill-llama-70b       |
  |  - Google Gemini: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp                      |
  |  - OpenRouter Free: meta-llama/llama-3.3-70b-instruct:free, deepseek/deepseek-r1:free      |
  |  - Cerebras Engine: llama3.3-70b, llama3.1-8b (2000+ tokens/sec inference)                   |
  |  - SambaNova Cloud: Meta-Llama-3.3-70B-Instruct, DeepSeek-R1-Distill-Llama-70B             |
  |  - Hugging Face: Qwen/Qwen2.5-Coder-32B-Instruct, mistralai/Mistral-7B-Instruct-v0.3       |
  +---------------------------------------------------------------------------------------------+
```

---

## Component Breakdown

### 1. React 18 Single Page Application (frontend/)
- Renders a responsive, modern user interface built with Tailwind CSS, Framer Motion animations, and Lucide React icons.
- Handles real-time search filtering, paper selection state management, model selector dropdown overlay, report rendering, and file export formatting.

### 2. FastAPI / Gunicorn Backend (backend/)
- Asynchronous Python web service running FastAPI routed through Uvicorn or multi-worker Gunicorn.
- Exposes REST endpoints for academic literature search (/api/search), RAG gap analysis (/api/analyze), follow-up chat (/api/chat), PDF upload (/upload), and model status (/models).

### 3. Local CPU Embedding Service (sentence-transformers)
- Uses sentence-transformers/all-MiniLM-L6-v2 running 100% locally on CPU to generate 384-dimensional dense vector embeddings.
- Eliminates third-party embedding API costs, quota errors, and external embedding key requirements.

### 4. FAISS / Chroma Vector Store Engine
- Stores vectorized paper chunks in local persistent indexes.
- Session isolation ensures each browser session gets an isolated vector store directory (faiss_index/sessions/<session_id>/), automatically cleaned up after 3 days.

---

## Obtaining & Configuring Free AI API Keys

ResearchPaperRAG requires at least one free provider API key to perform LLM synthesis. Groq Cloud is configured as the default provider.

### 1. Groq Cloud API Key (GROQ_API_KEY) — Recommended Default
- Available Models: llama-3.3-70b-versatile, deepseek-r1-distill-llama-70b, gemma2-9b-it.
- How to Obtain:
  1. Visit Groq Console (https://console.groq.com/).
  2. Sign in with Google/GitHub and navigate to API Keys.
  3. Click Create API Key and copy your key.
  4. Set in backend/.env: GROQ_API_KEY=gsk_...

### 2. Google Gemini API Key (GOOGLE_API_KEY)
- Available Models: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp.
- How to Obtain:
  1. Visit Google AI Studio (https://aistudio.google.com/).
  2. Click Get API Key -> Create API key in new project.
  3. Set in backend/.env: GOOGLE_API_KEY=AIzaSy...

### 3. OpenRouter Free Tier Key (OPENROUTER_API_KEY)
- Available Models: meta-llama/llama-3.3-70b-instruct:free, deepseek/deepseek-r1:free, qwen/qwen-2.5-72b-instruct:free.
- How to Obtain:
  1. Visit OpenRouter Keys (https://openrouter.ai/keys).
  2. Click Create Key and copy.
  3. Set in backend/.env: OPENROUTER_API_KEY=sk-or-v1-...

### 4. Cerebras Wafer-Scale Engine Key (CEREBRAS_API_KEY)
- Available Models: llama3.3-70b, llama3.1-8b.
- How to Obtain: Visit Cerebras Cloud Console (https://cloud.cerebras.ai/) and create a key.

### 5. SambaNova Cloud Key (SAMBANOVA_API_KEY)
- Available Models: Meta-Llama-3.3-70B-Instruct, DeepSeek-R1-Distill-Llama-70B.
- How to Obtain: Visit SambaNova Cloud (https://cloud.sambanova.ai/) and generate a key.

### 6. Hugging Face Access Token (HF_API_KEY)
- Available Models: Qwen/Qwen2.5-Coder-32B-Instruct, mistralai/Mistral-7B-Instruct-v0.3.
- How to Obtain: Visit Hugging Face Tokens (https://huggingface.co/settings/tokens) and generate a Read token.

---

## Complete Environment Configuration Reference (.env)

### Backend Environment File (backend/.env)

```env
# SERVER & ENVIRONMENT SETTINGS
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production
CORS_ORIGINS=*

# DEFAULT PROVIDER & MODEL SELECTION
DEFAULT_PROVIDER=groq
DEFAULT_MODEL=llama-3.3-70b-versatile

# AI PROVIDER API KEYS (Configure at least one)
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
CEREBRAS_API_KEY=your_cerebras_api_key_here
SAMBANOVA_API_KEY=your_sambanova_api_key_here
HF_API_KEY=your_huggingface_token_here

# VECTOR STORE & STORAGE CONFIGURATION
MAX_FILE_SIZE=52428800
FAISS_PERSIST_DIR=faiss_index
MAX_VECTOR_SESSIONS=64
FAISS_SESSION_MAX_AGE_DAYS=3

# RATE LIMITING & SECURITY
RATE_LIMIT_UPLOAD_PER_MINUTE=8
RATE_LIMIT_ASK_PER_MINUTE=90
```

### Frontend Environment File (frontend/.env)

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## Local Quickstart & Execution Guide

Follow these steps to run ResearchPaperRAG natively on your local development machine.

### Prerequisites
- Python 3.11 or Python 3.12
- Node.js 18+ & npm 9+
- Git

### Step 1: Clone Repository
```bash
git clone https://github.com/AishikTokdar/ResearchPaperRAG.git
cd ResearchPaperRAG
```

### Step 2: Configure Backend & Install Python Dependencies
```bash
cd backend

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env from template and add your API key
cp .env.example .env
```

### Step 3: Launch Backend Server

#### Development Mode (Uvicorn with Auto-Reload):
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 4: Configure Frontend & Install Node Dependencies (New Terminal)
```bash
cd frontend

# Install Node dependencies
npm install

# Create frontend .env
cp .env.example .env

# Launch Vite development server
npm run dev -- --host 127.0.0.1 --port 5173
```

### Step 5: Open Web Application
- Research Gap Analyzer SPA: http://127.0.0.1:5173/chat
- Home Landing Page: http://127.0.0.1:5173/
- Swagger API Docs: http://127.0.0.1:8000/docs

---

## Production Deployment with Gunicorn & Uvicorn

For production deployments on Linux VPS, EC2, or Docker containers, run the FastAPI backend using Gunicorn with worker processes:

```bash
cd backend
source .venv/bin/activate

# Execute Gunicorn WSGI with 4 Uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Gunicorn Flags Explanation:
- -w 4: Runs 4 concurrent worker processes for high-concurrency request processing.
- -k uvicorn.workers.UvicornWorker: Uses Uvicorn's asynchronous worker class for FastAPI compatibility.
- --bind 0.0.0.0:8000: Binds server to port 8000 on all network interfaces.

---

## Docker & Containerization Guide

### Option A: Full-Stack Docker Compose (Recommended)
Launch both React frontend and FastAPI backend in isolated containers with a single command:

```bash
# 1. Ensure backend/.env exists with your API keys
cp backend/.env.example backend/.env

# 2. Build and launch containers
docker compose up --build
```

Access Points:
- React Frontend: http://localhost:5173
- FastAPI Backend: http://localhost:8000
- Interactive OpenAPI Sandbox: http://localhost:8000/docs

### Option B: Standalone Backend Docker Container
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

---

## Cloud Deployment Options

### Part A: Backend Deployment on Hugging Face Spaces (ZeroGPU Option)

Deploying the Python FastAPI backend on Hugging Face Spaces provides free hosting with hardware acceleration options (ZeroGPU or CPU Basic 16 GB RAM).

#### Step-by-Step Instructions:

1. **Create a New Space**:
   - Go to [Hugging Face Spaces](https://huggingface.co/new-space).
   - Enter Space Name: `researchpaperrag-backend`.
   - License: Select **MIT**.
   - SDK: Select **Gradio** (or Docker).
   - Hardware: Select **ZeroGPU** (or **CPU Basic 2 vCPU 16 GB RAM** free tier).

2. **Upload Repository Files**:
   - Push or upload all contents from the `backend/` folder into the root directory of your Hugging Face Space repository (`app.py`, `requirements.txt`, `app/` folder, etc.).

3. **Configure Backend Environment Variables & Secrets**:
   In your Hugging Face Space dashboard, navigate to **Settings -> Secrets and Variables**:
   
   - **Repository Secrets** (Add your API keys securely):
     - `GROQ_API_KEY`: Your Groq Cloud API key (`gsk_...`)
     - `GOOGLE_API_KEY`: Your Google Gemini API key (`AIzaSy...`)
     - `OPENROUTER_API_KEY`: Your OpenRouter API key (`sk-or-v1-...`)
     - `CEREBRAS_API_KEY`: Your Cerebras Cloud API key
     - `SAMBANOVA_API_KEY`: Your SambaNova Cloud API key
     - `HF_API_KEY`: Your Hugging Face user access token (`hf_...`)

   - **Variables** (Add public runtime configuration):
     - `DEFAULT_PROVIDER`: `groq`
     - `DEFAULT_MODEL`: `llama-3.3-70b-versatile`
     - `ENVIRONMENT`: `production`
     - `CORS_ORIGINS`: `*` (or your deployed Vercel URL)

4. **Verify Deployment & Obtain Public URL**:
   - Once Hugging Face finishes building the Space, the FastAPI backend will be live.
   - Copy your Space's public HTTPS URL from the Space header (e.g. `https://YOUR_USERNAME-researchpaperrag-backend.hf.space`).
   - Verify health by opening `https://YOUR_USERNAME-researchpaperrag-backend.hf.space/health` or `/docs` in your browser.

---

### Part B: Frontend Deployment on Vercel

Deploying the React 18 SPA frontend on Vercel distributes your user interface across global edge CDNs.

#### Step-by-Step Instructions:

1. **Create Vercel Project**:
   - Log in to your [Vercel Dashboard](https://vercel.com/) and click **Add New... -> Project**.
   - Import your `ResearchPaperRAG` GitHub repository.

2. **Configure Build Settings**:
   - **Framework Preset**: Select **Vite**.
   - **Root Directory**: Click edit and select `frontend`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

3. **Configure Frontend Environment Variables**:
   In the Vercel project deployment screen, expand **Environment Variables**:
   
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: `https://YOUR_USERNAME-researchpaperrag-backend.hf.space` *(Replace with the Hugging Face Space URL obtained in Part A)*

4. **Deploy**:
   - Click **Deploy**.
   - Vercel will build the frontend assets, compile TypeScript, and publish your production site to a custom URL (e.g. `https://research-paper-rag.vercel.app`).

5. **Test Full-Stack Connection**:
   - Open your Vercel URL in your browser.
   - Navigate to `/chat` and execute a topic search across academic APIs.
   - The React app will make REST API calls to your Hugging Face Space backend, synthesize 8-layer gap reports, and run grounded follow-up chat.

---

## REST API Reference & OpenAPI Specification

ResearchPaperRAG provides interactive OpenAPI / Swagger UI documentation at /docs.

| Method | Endpoint | Description | Request Payload / Params |
| :---: | :--- | :--- | :--- |
| GET | /health | Live backend health check status | None |
| GET | /api/search | Concurrent search across 6 academic APIs | query (string), limit (int) |
| POST | /api/analyze | 8-Layer structured RAG gap synthesis | topic (string), provider (string), model (string) |
| POST | /api/chat | Grounded follow-up Q&A chat | question (string), provider (string), model (string) |
| POST | /upload | Upload custom PDF documents (<= 50 MB) | files (multipart/form-data) |
| GET | /models | List pre-configured models & credential status | None |
| GET | /pipeline-info | 7-stage processing pipeline telemetry | None |
| GET | /docs | Interactive Swagger UI testing sandbox | None |

---

## Troubleshooting & FAQs

### Q1: The UI shows Offline at the top during long paper searches.
- Resolution: Updated use-health.ts includes a 3-consecutive-failure threshold and a 12-second timeout allowance. Ensure you are running the latest frontend build.

### Q2: How do I change the default AI model?
- Resolution: Open /chat, select your model from the "Select AI Model" dropdown, and click "Save Model". Alternatively, edit DEFAULT_MODEL in backend/.env.

### Q3: Do I need an API key to search academic literature?
- Resolution: No. All 6 search APIs (arXiv, Crossref, Semantic Scholar, OpenAlex, PubMed, DOAJ) are 100% free and open-access. API keys are only required for the LLM synthesis layer.

---

## Tech Stack Summary

| Layer | Component | Technologies |
| :--- | :--- | :--- |
| Frontend | User Interface | React 18, TypeScript 5.4, Vite, Tailwind CSS, Framer Motion, Lucide Icons, Sonner |
| Backend | API Web Service | FastAPI, Uvicorn, Gunicorn WSGI, Pydantic v2, Python 3.11+ |
| Vector Engine | Search & Storage | FAISS, Chroma, sentence-transformers/all-MiniLM-L6-v2 (Local CPU) |
| Academic APIs | Search Providers | arXiv API, Crossref REST API, Semantic Scholar Graph API, OpenAlex API, PubMed Entrez, DOAJ |
| AI Layer | LLM Providers | Groq LPU, Google Gemini, OpenRouter Free, Cerebras, SambaNova, Hugging Face |

---

## License & Attribution

This project is open-source and released under the MIT License.

Created and maintained by Aishik Tokdar (@AishikTokdar). Feel free to inspect, extend, and deploy ResearchPaperRAG for academic, personal, or commercial research workflows!
