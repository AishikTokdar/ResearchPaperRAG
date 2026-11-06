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

`tests/test_report_presentation.py` checks labeled general guidance for missing/rejected sections, strict-mode isolation, retained valid passages, compact page citations and source lists. Frontend regressions cover proposal-table separators/first rows, export headings, duplicate citations, and guidance paragraphs after lists. Report-completion regressions ensure missing sections receive targeted model guidance without resending full document contents, while numeric claims/citations in that guidance are rejected and provider failure preserves the report. At most one follow-on pass covers only sections still missing; accepted sections are retained. Complete reports and interrupted drafts do not trigger extra completion. Provider tests verify alternative providers/models are considered before extra keys that may share a quota.

`backend/tests/integration_server.py` is a loopback-only fixture. Never deploy it: it substitutes external generation/download/embedding boundaries and exposes a test PDF route. Other app/parser/FAISS/session/SSE behavior is real.

`tests/test_five_source_reports.py` checks all five source identities through context budgeting, metadata-only coverage, restoration of omitted source summaries and source-list generation. It also verifies abstract preference over bibliography passages, rejection of unselected bibliography titles as summary entries, targeted model completion, retained table headers, safe guidance formatting, and rejection of invented statistical/latency targets. Sequential list labels and recognizable model versions in qualitative guidance are not treated as experimental metrics. Provider failure produces an explicit partial report instead of canned analysis. A local browser run on 2026-11-05 submitted five actual paper IDs for educational RAG chatbots and verified all five source URLs, all eight sections and zero static fallback paragraphs in the generated Markdown. TXT/PDF downloads and mobile reflow passed; all three PDF pages were rendered and visually inspected. The deterministic browser integration additionally checks each selected fetched-paper title and the uploaded PDF remain in the report.

## Frontend

### Live report-size matrix — 2026-11-06

The local production frontend was exercised with real academic search, local MiniLM embeddings and live Groq generation for each selection count. Sources with available abstracts were preferred for the depth check, including educational, image-generation, tourism and nursing RAG papers. Each successful run completed all eight sections, retained every selected source, showed no browser JavaScript errors, contained no canned paragraphs or retrieved-excerpt replacements, and downloaded MD, plain TXT and PDF. These are observed samples rather than guaranteed word counts for every future input.

| Selected papers | Report words (approximately) | PDF pages | Complete sections |
| --- | ---: | ---: | ---: |
| 2 | 1,689 | 5 | 8 |
| 3 | 1,857 | 7 | 8 |
| 4 | 2,016 | 6 | 8 |
| 5 | 2,218 | 7 | 8 |

The tests exposed real provider quota failures before successful retests. Recovery now honors seconds/milliseconds retry hints asynchronously for streamed reports, or in a worker for completion, within the same bounded attempt/deadline budget. An outage remains a visible partial report, never filler; an empty index fails instead of returning a placeholder report. Deterministic regressions check count-specific depth instructions, model-written expansion preserving findings, absence of stock report-body replacements, and nonblocking quota waits. Final verification passed 132 backend tests, Ruff and mypy, plus the full deterministic browser integration (search, mixed ingestion, report, follow-up, clearing, exports, runtime/proxy contracts and responsive layouts).

Detailed-report verification increased the default report output budget to 6,000 tokens and removed the short-report prompt limits. A live five-source run produced approximately 1,700 words across five PDF pages with all eight sections and no static fallback paragraphs. MD/TXT/PDF downloads passed. The unchanged live Markdown was re-exported after pagination fixes; all five PDF pages were inspected for heading/table placement, guidance labels and nested citation links. Backend verification passed 126 tests, Ruff and mypy; frontend verification passed 22 tests, TypeScript, lint and production build. Actual length varies with available evidence and model output rather than being padded to a fixed word count.

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

Workspace usability checks preserve the report topic when the next search is edited, prevent unchanged model saves from clearing work, retain failed follow-up drafts and keep provider filtering separate from model selection. These were reproduced and rechecked interactively in the browser; populated workspace reflow was measured at 320, 375, 768 and 1440 pixels, with keyboard Escape/focus checks on the model picker.

Export checks cover plain TXT without Markdown decoration, preserved headings/table contents/source URLs, and actual MD/TXT/PDF browser downloads in dark mode. PDF changes were additionally checked by rendering every page of a downloaded multi-page report and inspecting text visibility, table rows, page transitions and clickable link annotations.

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

## Local verification — 2026-11-04

The local frontend was exercised against the unmocked local backend with real academic search, local MiniLM embeddings, mixed paper/PDF analysis, all eight report sections, cited follow-ups, model selection, clearing and MD/TXT/PDF/clipboard exports. PDF pages were rendered for visual inspection, and layouts were checked at 320, 375, 768 and 1440 pixels. Invalid uploads and independent-session isolation were also checked. Live Gemini failures exercised successful Groq fallback; this does not certify every catalog model or guarantee provider availability.

The Gradio entrypoint was checked separately from the standalone FastAPI entrypoint. Root-route regression coverage ensures a mounted UI receives `/` while standalone API status remains available. Additional regressions cover clearing unsent follow-up drafts, avoiding duplicate guidance labels after rejected report passages, and preventing proposal labels from bypassing strict follow-up citation checks. The deterministic browser suite additionally covers delayed-response races and error recovery.

The author query `Aishik Tokdar` was reproduced in the local browser with the top two results: dynamic spectrum management using Deep Q-Learning, and hybrid CNN-BiLSTM-BiGRU EEG impairment detection. The former had metadata-only coverage; it was previously dropped before generation. The revised live report retained both sources and used a small topic-guidance generation for rejected sections. Markdown downloads were inspected for all eight sections, source links, valid table headers and labeled guidance. Tests also reject fabricated paper-attribution statements and unsupported numeric targets in proposed-project rows. Live output quality remains model-dependent; guidance is not presented as verified paper findings.
