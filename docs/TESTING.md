# Verification

## Backend

Activate Python and install `backend/requirements-dev.txt`. From the repository root:

```sh
python -B scripts/check_backend.py
# Or automatically select the repository virtual environment:
node scripts/check-backend.mjs
```

Run `python -B scripts/audit_core.py --output core-audit.json` to audit the installed API-only dependency closure. It excludes unrelated optional packages, checks installed version ranges and produces a platform-specific snapshot, not a reproducible release lock.

The checker runs Ruff, mypy and unittest discovery from `backend`. `BACKEND_PYTHON` selects another interpreter for the Node launcher. The main commands work without Bash on Windows.

Tests cover session isolation/eviction, safe downloads, body/resource limits, CORS/hosts, provider serialization, real MiniLM token bounds, PDF subprocesses, FAISS persistence/retrieval, JSON/SSE chat, mixed-source reports, follow-up/clear, cache invalidation and cancellation/backpressure. Generation/download boundaries are deterministic. The tokenizer may download initially; tests do not download embedding weights or consume paid inference.

`tests/test_report_resilience.py` checks compound citations, equivalent numeric formats, unsupported/uncited passages, retained report sections, valid Markdown tables, hostile exponents, empty section headings, cache eligibility, abstract coverage, provider interruption and preservation of short PDF results. These are deterministic regressions, not a live-provider quality benchmark.

`backend/tests/integration_server.py` is a loopback-only fixture. Never deploy it: it substitutes external generation/download/embedding boundaries and exposes a test PDF route. Other app/parser/FAISS/session/SSE behavior is real.

## Frontend

```sh
cd frontend
npm ci
npm run typecheck
npm run lint
npm run test:security
npm run build
```

Node tests cover export injection, SSE framing/interruption, trusted ingestion contracts, progress, notice removal, telemetry, production API origin safety and stable/reset session capabilities.

Request-lifecycle regressions check readable streamed validation errors, propagated cancellation, and late PDF-chat answers after clearing. Browser integration also delays real search/clear responses to check PDF selection capacity during an in-flight search and prevent a new follow-up while chat history is being cleared.

## Browser with the real backend

Install Playwright as a local test tool:

```sh
cd frontend
npm install --no-save --package-lock=false playwright@1.64.1
npx playwright install chromium
```

From the root start `PYTHONPATH=backend python -B backend/tests/integration_server.py`. PowerShell: set `$env:PYTHONPATH='backend'` first. It listens on loopback port 8999.

Build with empty `VITE_API_BASE_URL` to use the production same-origin behavior, then start the preview proxy:

```sh
# from frontend, POSIX shell
VITE_API_BASE_URL= npm run build
VITE_DEV_PROXY_TARGET=http://127.0.0.1:8999 npm run preview -- --host 127.0.0.1 --port 5188 --strictPort
# another terminal, from frontend
npm run test:browser
```

PowerShell users set the named `$env:` variables before commands. `FRONTEND_URL` selects another test origin. `PLAYWRIGHT_MODULE_PATH` can point to an existing Playwright module; `CHROME_PATH` selects installed Chrome.

The browser test covers production URL handling, search, uppercase PDF upload, mixed sources, report completion, follow-up/clear, runtime values, proxy paths and 320/768/1440 widths. External boundaries remain fixtures, proving integration rather than live answer quality. Broader mocked checks during the audit covered keyboard navigation, reduced motion, cancellation/errors, clipboard and PDF/MD/TXT downloads.

## Deployment checks

Run `docker compose --env-file backend/.env config --quiet`, build the images, then `nginx -t` in the frontend container. Test HTTPS and real SSE delivery. Docker startup and Linux memory-limit behavior need Linux/Docker; local Python/TypeScript success does not prove those properties.

CI runs backend checks, frontend checks/build and deterministic browser integration. A separate Docker job verifies builds/configuration. Live provider checks and realistic load/quality benchmarks remain release-environment checks.
