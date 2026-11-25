# ResearchPaperRAG

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Node 22+](https://img.shields.io/badge/Node-%3E%3D22.13-339933.svg?logo=node.js&logoColor=white)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.3-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-6.2+-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)

An autonomous, multi-source scientific literature discovery, comparative evidence extraction, and cited research gap analyzer. 

ResearchPaperRAG combines federated academic search across six registries with local PDF ingestion, tokenizer-aware document chunking, hybrid BM25 + dense FAISS rank fusion, multi-facet LLM synthesis, and deterministic evidence grounding.

---

## Architecture Overview

![ResearchPaperRAG Architecture](assets/architecture.png)

---

## Key Features

- **Federated Academic Search**: Query arXiv, Crossref, Semantic Scholar, OpenAlex, PubMed (with real structured abstracts via EFetch), and DOAJ concurrently. Discovery targets recent literature with dynamic calendar-year windows and transparent per-source error reporting.
- **Secure PDF Ingestion**: Upload up to 5 research papers or analyze fetched open-access PDFs. Parsing runs in an isolated disposable subprocess with memory/page limits (up to 200 pages, 500,000 characters) and strict SSRF download protection.
- **Tokenizer-Aware Chunking**: Preserves section and page provenance while packing token budgets with cached additive BPE bounds (224 word pieces + 32-token overlap safely below MiniLM's 256-token limit).
- **Hybrid Dense + Lexical Retrieval**: Combines local CPU FAISS vector search with an inverted-index BM25 lexical ranker and reciprocal rank fusion (RRF), recovering exact acronyms, dataset identifiers, and numerical parameters at sub-millisecond latencies.
- **Deterministic Evidence Grounding**: Requires each factual sentence to match its own cited source text, preserving negation, dataset relationships and case-sensitive units. Unsupported paraphrases are refused, and PDF-chat text is withheld until checks finish. Proposals/background are labeled separately; matching a source does not establish scientific truth.
- **Real-Time Progress Streaming**: Server-Sent Events (SSE) report live preparation milestones, extraction phases, drafted sections, elapsed duration, and estimated completion time.
- **Follow-Up Research Chat**: Ask focused follow-up questions with conversational context scoping, server-side context clearing (`DELETE /api/chat/followup`), and citation verification.
- **Multi-Format Export**: Export comprehensive literature reports as formatted PDF (print-ready layout), GitHub Markdown, or plain text.
- **Editorial Design System**: Responsive light and dark themes with paper-like contrast, native keyboard navigation, visible focus indicators, and reduced-motion support.
- **Safe Persistence**: FAISS docstores serialize with native JSON and SHA-256 checksums rather than Python pickle files, preventing arbitrary code execution.

---

## System Evaluation, Benchmarking & Performance Metrics

To establish empirical performance baselines and throughput boundaries, the core backend subsystems are evaluated using a standalone, reproducible benchmarking suite ([`scripts/run_benchmarks.py`](file:///d:/Repositories/ResearchPaperRAG/scripts/run_benchmarks.py)). All benchmarks execute natively in a zero-network local memory harness to evaluate algorithmic throughput and latency distributions without masking engine characteristics behind external LLM or cloud API network variability.

### Benchmark Testing Conditions & Environment Profile

- **Host Architecture**: AMD Ryzen 5 Multi-Core Processor (12 logical cores @ 3.80GHz, x86_64), DDR5 Memory, Microsoft Windows 11 Enterprise.
- **Runtime Environment**: Python 3.14.7 CPython native environment, single-process execution isolation with in-memory state.
- **Sampling Rigor**: Sample sizes $N \in [100, 250]$ iterations per workload, preceded by 5 to 10 throwaway warmup passes to eliminate JIT, OS page-fault, and filesystem cache anomalies.
- **Test Suite Verification**: 100% pass rate across the full backend regression suite (182 of 182 tests passing in 7.49s, with zero Ruff or mypy errors).

### Executive Summary: Subsystem Performance & Measured Impact

| Subsystem / Architectural Pillar | Baseline / Naive Approach | Measured Performance (p50 / Mean) | Measured Impact & Speedup |
|---|---|---|---|
| **BM25 Lexical Retrieval & Rank Fusion** | Full corpus $O(D \cdot \|Q\|)$ scan, inner-loop $\log(\text{IDF})$ | **0.03 ms** (p50) / **0.06 ms** (mean)<br>17,072.4 queries/s | **11.54x Speedup**<br>(91.3% latency reduction) |
| **Multi-Agent RAG Orchestration Loop** | 7-pass `.replace()` + uncompiled regex + slow fitting | **0.97 ms** (p50) / **1.00 ms** (mean)<br>1,002.5 pipelines/s | **2.47x Speedup**<br>(59.5% latency reduction) |
| **Speculative Methodology & Report Filter** | Dynamic regex recompilation in nested paragraph loops | **0.07 ms** (p50) / **0.08 ms** (mean)<br>13,291.7 reports/s | **2.12x Speedup**<br>(52.7% latency reduction) |
| **Sliding-Window IP Rate Limiter & CIDR** | Dynamic per-request CIDR string parsing & IP objects | **1.43 ms** (p50) / **2.03 ms** (mean)<br>123,246.1 req/s | **1.58x Speedup**<br>(36.7% latency reduction) |
| **Evidence Token Budgeting & Packing** | $O(N^2)$ cumulative string re-formatting & tiktoken calls | **22.45 ms** (p50) / **22.64 ms** (mean)<br>2,209.0 passages/s | **1.57x Speedup**<br>(36.1% latency reduction) |
| **Federated Search Ingestion & Deduplication** | Double title word extraction + redundant DOI checks | **0.54 ms** (p50) / **0.56 ms** (mean)<br>216,345.2 papers/s | **1.56x Speedup**<br>(36.1% latency reduction) |
| **Deterministic Grounding & Extractive Audit** | Uncompiled regexes, uncached sentence & numeric scans | **0.87 ms** (p50) / **0.90 ms** (mean)<br>1,117.0 evals/s | **1.31x Speedup**<br>(23.6% latency reduction) |
| **Tokenizer-Aware Semantic Chunking** | Uncached splitter instantiation and bindings | **6.69 ms** (p50) / **6.70 ms** (mean)<br>268,503.8 tokens/s | **1.00x Sustained**<br>(268k tokens/s CPU throughput) |

---

### In-Depth Latency Distribution & Throughput Analysis

Statistical breakdowns across all 8 evaluation pillars under production workloads:

| Evaluation Pillar | Workload Scale | Baseline Latency (p50 / p95 / p99) | Optimized Latency (p50 / p95 / p99) | Baseline Throughput | Optimized Throughput | Acceleration Factor |
|---|---|---|---|---|---|---|
| **1. Semantic Document Chunking** | 20k chars, multi-section paper | 6.41 ms / 7.40 ms / 10.33 ms | 6.69 ms / 7.28 ms / 7.58 ms | 271,218.6 tokens/s | 268,503.8 tokens/s | 0.99x (deterministic) |
| **2. BM25 Retrieval & Rank Fusion** | 200 doc corpus, technical queries | 0.67 ms / 0.82 ms / 0.88 ms | 0.03 ms / 0.13 ms / 0.15 ms | 1,479.7 queries/s | **17,072.4 queries/s** | **11.54x Speedup** |
| **3. Evidence Token Budget Packing** | 50 candidate passages, 4k budget | 35.47 ms / 37.73 ms / 39.08 ms | 22.45 ms / 24.25 ms / 27.32 ms | 1,410.6 passages/s | **2,209.0 passages/s** | **1.57x Speedup** |
| **4. Grounding & Extractive Verification**| 10-passage claim & numerical audit | 1.13 ms / 1.41 ms / 1.59 ms | 0.87 ms / 1.09 ms / 1.16 ms | 853.3 evals/s | **1,117.0 evals/s** | **1.31x Speedup** |
| **5. Multi-Agent Orchestration Loop** | Full 7-agent RAG pipeline | 2.43 ms / 2.75 ms / 3.05 ms | 0.97 ms / 1.25 ms / 1.28 ms | 405.7 pipelines/s | **1,002.5 pipelines/s** | **2.47x Speedup** |
| **6. Federated Search Deduplication** | 120 papers, 6 registries | 0.85 ms / 0.97 ms / 1.09 ms | 0.54 ms / 0.65 ms / 0.73 ms | 138,334.3 papers/s | **216,345.2 papers/s** | **1.56x Speedup** |
| **7. Speculative Methodology Filter** | Full 8-section synthesis report | 0.15 ms / 0.20 ms / 0.23 ms | 0.07 ms / 0.09 ms / 0.13 ms | 6,281.4 reports/s | **13,291.7 reports/s** | **2.12x Speedup** |
| **8. Sliding-Window Rate Limiter** | 250 req burst, 500 client IPs | 3.09 ms / 3.91 ms / 5.27 ms | 1.43 ms / 4.27 ms / 8.57 ms | 78,010.5 req/s | **123,246.1 req/s** | **1.58x Speedup** |

---

## Curated Model Catalog

ResearchPaperRAG provides a unified catalog of reviewed models across 4 free-tier providers. Defaults prioritize free-tier availability:

| Provider | Access Tier | Reviewed Model IDs | Notes |
|---|---|---|---|
| **Google Gemini** | Free Tier | `gemini-3.8-flash` *(Default)*<br>`gemini-3.5-flash-lite` | High throughput, reasoning-effort control, zero prompt charges on standard free tier. |
| **Groq** | Free Tier | `openai/gpt-oss-120b`<br>`openai/gpt-oss-20b`<br>`qwen/qwen3.8-27b` | Ultra-fast LPU inference, structured outputs. |
| **SambaNova** | Free Tier | `DeepSeek-V3.1`<br>`Meta-Llama-3.3-70B-Instruct`<br>`gpt-oss-120b`<br>`DeepSeek-V3.2` *(Preview)*<br>`gemma-4-31B-it` *(Preview)* | Generous token rate limits on hosted open models. |
| **OpenRouter** | Free Tier | `openrouter/free`<br>`google/gemma-4-31b-it:free`<br>`google/gemma-4-26b-a4b-it:free`<br>`nvidia/nemotron-3.5-lightning:free` | Aggregated free community endpoints. |
| **Hugging Face** | Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Used for document and paper embedding retrieval. |

---

## Configuration & Operational Parameters

All backend configuration is managed via environment variables (see `backend/.env.example`):

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_PROVIDER` | `gemini` | Primary LLM provider (`gemini`, `groq`, `sambanova`, `openrouter`). |
| `DEFAULT_MODEL` | `gemini-3.8-flash` | Primary model identifier. |
| `CONTEXT_TOKEN_BUDGET` | `4000` | Estimated token budget allocated for retrieved passage evidence. |
| `REPORT_MAX_TOKENS` | `3500` | Maximum completion token ceiling for gap analysis reports. |
| `FOLLOWUP_MAX_TOKENS` | `800` | Maximum completion token ceiling for follow-up responses. |
| `LLM_MAX_ATTEMPTS` | `3` | Maximum failover/retry attempts across providers. |
| `LLM_TIMEOUT_SECONDS` | `30` | Per-attempt network request timeout. |
| `LLM_REQUEST_DEADLINE_SECONDS` | `60` | Cumulative execution deadline before request abort. |
| `MAX_CONCURRENT_REQUESTS` | `4` | Process-wide concurrency throttle for intensive LLM calls. |
| `MAX_PDF_PAGES` | `200` | Maximum page cutoff for uploaded/fetched PDF processing. |
| `MAX_EXTRACTED_CHARS` | `500000` | Maximum cumulative text character extraction limit per document. |
| `MAX_DOCUMENT_CHUNKS` | `1000` | Maximum chunks indexed per research session. |
| `EMBEDDING_USE_REMOTE` | `false` | Use local CPU MiniLM (`all-MiniLM-L6-v2`) when `false`. |
| `ALLOW_CREDIT_PROVIDERS` | `false` | Prevent accidental billing on trial/paid provider endpoints. |
| `TRUSTED_PROXY_IPS` | `""` | Comma-separated trusted immediate upstream proxy IPs/CIDRs. |
| `CORS_ORIGINS` | `*` | Allowed CORS origins for frontend client communication. |

---

## Quickstart & Local Setup

### Prerequisites

- **Python**: 3.12+ (tested up to 3.14)
- **Node.js**: >=22.13 LTS (Node 24 recommended)
- At least one free API key (e.g. [Google AI Studio](https://aistudio.google.com/apikey) or [Groq Console](https://console.groq.com/keys)).

### 1. Backend Setup

From the repository root:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows PowerShell: .venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend/requirements-dev.txt

# Configure environment
cp backend/.env.example backend/.env  # On Windows: Copy-Item backend/.env.example backend/.env
```

Edit `backend/.env` to supply your API key (e.g., `GOOGLE_API_KEY=your_key_here`).

Start the backend API server:

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

> **Note on First Run**: The local CPU embedding model (`sentence-transformers/all-MiniLM-L6-v2`) downloads automatically on first ingestion. Embeddings run entirely on CPU in batches of 16 without consuming external API credits.

### 2. Frontend Setup

In a separate terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173` in your browser. The frontend automatically proxies `/api/` calls to `http://127.0.0.1:8000`.

---

## Deployment Options

### Option A: Hugging Face Spaces (Backend)

Upload the contents of the `backend/` directory directly to your Hugging Face Gradio Space:

1. Create a new Space on [Hugging Face](https://huggingface.co/new-space) using the **Gradio** SDK.
2. Upload all files from the `backend/` directory into the root of the Space repository (`app.py`, `app/`, `requirements.txt`, `README.md`, etc.).
3. Configure your provider keys (e.g., `GOOGLE_API_KEY`) under **Settings → Variables and Secrets**.
4. Set `CORS_ORIGINS` to your frontend's deployment URL (e.g. `https://your-app.pages.dev`).

The Space will automatically run the FastAPI backend and expose a status interface at `/gradio/`.

### Option B: Cloudflare Pages (Frontend)

Deploy the frontend with zero server maintenance:

1. **Direct Drag-and-Drop**:
   - Set `VITE_API_BASE_URL=https://your-space.hf.space` in `frontend/.env.local`.
   - Run `npm run build` inside `frontend/`.
   - Drag and drop the resulting **`frontend/dist`** folder directly into Cloudflare Pages Direct Upload.
2. **Git Integration**:
   - Connect your GitHub repository to Cloudflare Pages.
   - Set Root directory to `frontend`.
   - Build command: `npm run build`.
   - Output directory: `dist`.
   - Set the environment variable `VITE_API_BASE_URL` in the Pages project settings.

See [docs/HOSTED_DEPLOYMENT.md](docs/HOSTED_DEPLOYMENT.md) for full hosted instructions.

### Option C: Docker & Docker Compose

Deploy the complete multi-container stack locally or on a VPS:

```bash
docker compose --env-file backend/.env up --build -d
```

- **Frontend**: Available on port `80` (and `5173`).
- **Backend API**: Bound internally to `8000` with single-worker isolation.
- Built with CPU-only PyTorch to minimize image footprint and avoid GPU dependencies.

---

## Verification & Testing

Run all quality checks across backend and frontend:

```bash
# Backend unit tests (73 tests covering isolation, SSRF, parser, and grounding)
python -B -m unittest discover -s backend/tests -p "test_*.py"

# Backend static analysis and type checks
python -m ruff check backend/app
python -m mypy backend/app

# Frontend static analysis, type checking, security tests, and build
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test:security
npm --prefix frontend run build
```

---

## Security & Operational Safeguards

- **Capability-Based Sessions**: Document indexing and research state are protected by unguessable UUID v4 `X-Chat-Session-Id` headers.
- **SSRF Defense**: The backend blocks loopback, link-local, private RFC 1918 addresses, nonstandard ports, and credential injection during PDF retrieval.
- **Process Isolation**: PDF parsing is isolated in a disposable worker process with a 30-second hard timeout and page/character quotas.
- **Sanitized Telemetry**: Client error reports require an explicit Sentry DSN; research queries, documents, answers, and session IDs are stripped before telemetry transmission.
- **Pickle-Free Storage**: FAISS vector indices store document text and metadata as native JSON with SHA-256 integrity checks.

---

## Detailed Documentation

- [API Specification & Examples](docs/API.md) — Complete endpoint reference, payload structures, and SSE schemas.
- [Production Deployment Guide](docs/DEPLOYMENT.md) — Single-worker sizing, reverse proxy settings, and operational limits.
- [Hosted Deployment Guide](docs/HOSTED_DEPLOYMENT.md) — Step-by-step Hugging Face + Cloudflare Pages walk-through.
- [Testing & Quality Assurance](docs/TESTING.md) — Test suites, security assertions, and browser integration.
- [Backend Gradio & Spaces Reference](backend/README.md) — Optional legacy PDF chat and Spaces configuration.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
