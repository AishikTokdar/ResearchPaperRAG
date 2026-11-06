# API reference

Use an API origin such as `http://127.0.0.1:8000` in development, or the frontend origin behind the included production proxy. Do not append another `/api` to that origin: research endpoints already include it. Interactive schema: `/docs`, `/redoc`, `/openapi.json`.

## Sessions and errors

All document/research routes require `X-Chat-Session-Id: <UUID v4>`. Keep this capability private and use HTTPS. Read-only health/configuration endpoints require no session. JSON errors normally contain `detail`. Typical codes: 400 invalid input/session/source state, 409 conflicting ingestion/conversation, 413 body/file limit, 422 schema validation, 429 quota/capacity, 502 upstream discovery/ingestion failure, 503 temporary generation/indexing failure. SSE errors use an `error` event after headers have been sent; HTTP 200 alone does not mean generation succeeded.

## Routes

| Method/path | Input | Result / frontend integration |
| --- | --- | --- |
| GET `/`, `/health` | none | API process liveness; not a provider-connectivity guarantee |
| GET `/models` | none | Catalog and configured availability; model selector |
| GET `/runtime-summary` | none | Provider policy/status, live token chunk sizes, counters; status page |
| GET `/pipeline-info` | none | Seven deterministic/generative PDF chat stages; not eight report sections |
| POST `/api/papers/search` | JSON `query`, optional `limit_per_source` (1–10) | `papers`, `total_found`, `source_status`; workspace search |
| POST `/api/papers/ingest` | JSON `fetched_papers: [{id}]`, 1–5 | Compatibility research index; only server-known IDs are trusted |
| POST `/api/analyze/gaps` | JSON `topic`, optional `provider`, `model_name` | Compatibility JSON `report` from that session's research engine |
| POST `/api/analyze/stream` | Multipart `topic`, `provider`, `model_name`, JSON-string `paper_ids`, optional repeated `files` | Main workspace preparation + report SSE; 1–5 combined sources |
| POST `/api/chat/followup` | JSON `question`, optional `provider`, `model_name` | `answer`, based on the last research engine; workspace follow-up |
| DELETE `/api/chat/followup` | session header | Clear server conversation context while retaining the research index/report topic |
| POST `/upload` | Multipart repeated `files`, 1–3 PDFs | Legacy PDF index and per-file page/chunk counts |
| GET `/status` | session header | Legacy PDF readiness, document count and boot ID |
| POST `/ask` | JSON `question`, optional `model`, `include_sources`, `knowledge_mode` | Legacy grounded JSON answer and source labels |
| POST `/ask/stream` | same JSON | Legacy token SSE plus final verified answer |
| POST `/api/oversight` | Sentry envelope | Optional relay; 404 unless `TELEMETRY_TUNNEL_DSN` is configured; only that exact DSN is accepted |

A search is not a full-text availability guarantee. `source_status` distinguishes `ok`, `timeout`, and `unavailable`. The server validates fetched PDFs independently of client-provided URLs. Missing full text falls back to explicitly scoped abstracts/metadata; metadata-only records cannot support synthesis.

Questions are limited to 2,000 characters, search queries to 500, and combined uploaded PDF bytes to 50 MiB. Defaults also limit PDFs to 200 pages, 500,000 extracted characters and 1,000 indexed chunks per selection. Downloaded source PDFs have a separate 15 MiB download cap. Parser jobs have a 30-second timeout and Unix address-space/CPU limits. These limits can reject a selection rather than silently discarding its ending.

## Research example

```sh
SID=00000000-0000-4000-8000-000000000001
curl -H "X-Chat-Session-Id: $SID" -H 'Content-Type: application/json'   -d '{"query":"retrieval evaluation","limit_per_source":3}' http://127.0.0.1:8000/api/papers/search
# Use IDs actually returned by that search:
curl -N -H "X-Chat-Session-Id: $SID" -F 'topic=retrieval evaluation'   -F 'provider=gemini' -F 'model_name=gemini-3.8-flash'   -F 'paper_ids=["<server-returned-id>"]' -F 'files=@paper.pdf'   http://127.0.0.1:8000/api/analyze/stream
```

For uploads alone use `paper_ids=[]`. PowerShell users should invoke `curl.exe` with suitable shell quoting, or use an HTTP client; the examples above use POSIX shell syntax. Never send caller API keys: request fields reject them.

## Streaming contracts

Research SSE emits `progress`, `heartbeat`, `done`, `error`. Progress includes weighted milestone `percent`, stage/message, elapsed seconds and, when observed, current/completed sections and drafted word counts. Milestone percentages and ETA are estimates. Only `done` means completion and carries the final grounded report; `limited` marks partial/insufficient evidence. EOF without `done`/`error` is an interruption. Disconnects cancel generation and signal preparation cancellation between documents/stages; already running CPU work retains its worker slot until exit.

Reports retain independently supported passages when another passage fails citation or numeric validation. Rejected, missing or thin sections can receive bounded guidance generation using selected titles, coverage, short source overviews and requested section names. Its output budget scales with the requested sections, capped at 2,800 tokens per call; full texts are not resent. A second pass covers only sections still requiring completion, retaining accepted text and stopping on a provider outage. This reuses the successful model, with normal bounded failover. Accepted advice is labeled “General guidance (not findings from the selected papers)”. Sequential list markers and model versions in qualitative advice are distinguished from unsupported result metrics. If completion remains unavailable, real source reports retain supported material and all selected records, with one partial-report notice naming unfinished sections; canned paragraphs are not substituted as completed analysis. Partial/guidance-bearing reports are not cached. Abstract-only, metadata-only and partial-PDF coverage sets `limited` on both fresh and cached responses. Clearly labeled proposals and the hypothesis table are suggestions rather than established findings; invented numerical targets and unrelated uncited source claims remain blocked. An empty source index fails analysis instead of returning a completed placeholder report.

Report depth scales by selection count. The overall target is 2,200–3,000 words where evidence supports it, with approximately 450–650 words per substantive paper for two selections, 350–500 for three, 280–400 for four, and 220–350 for five across the report. These are model instructions rather than guaranteed lengths. Short real-source reports can receive model-written expansion in thin analysis sections, preserving supported findings. `REPORT_MAX_TOKENS` defaults to 6,000 (up to 8,192); an existing environment value overrides that default. No canned prose or retrieved-excerpt summaries are injected into report bodies. Source links are retained separately in Selected sources and the Sources appendix. Unavailable or rejected completion is disclosed once as a partial report. More detail consumes tokens and can take longer. Completion may honor a short provider retry hint (numeric `Retry-After` or an explicit seconds hint in the error, capped at 30 seconds) within the existing attempt/deadline budget, in a worker rather than the SSE event loop.

An author name or other discovery query is not treated as a requirement that all selected papers share one research subject. Report context reserves an initial passage for each selection, including metadata-only records. The model is instructed to summarize every selection; the application retains all source records in Selected sources and the Sources appendix without inserting stock summaries or quoted-excerpt replacements into the report body. Reports distinguish different domains and offer domain-specific research guidance rather than forcing common methods or contradictions. Metadata supports bibliographic details, not experimental findings. Different tasks or scores do not establish a contradiction, and a single paper does not establish a field-wide trend.

If a provider interrupts an already-started research report, the backend validates the draft locally and returns the supported portion with an incomplete-report warning and `limited: true`. It does not append a second provider's output or spend another generation call to repair the draft. Failure before usable text still uses bounded failover. Legacy PDF chat retains its interruption error contract. A provider or proxy connection loss before the browser receives a terminal event remains an interruption, not successful completion.

PDF chat SSE emits `status`, `token`, optional `warning`, `done`, `error`. Tokens are provisional. `done.answer` replaces them with the citation-checked answer and includes model, time, sources and warnings. Do not concatenate a failed partial response with another model's answer.

## Knowledge modes and availability

Legacy PDF chat defaults to `knowledge_mode: "strict"`; `hybrid_mode` remains supported and conflicting fields are rejected. Hybrid background knowledge is labeled separately and is not attributed to documents. Research report findings and follow-ups remain evidence-grounded. Reports can additionally contain explicitly labeled general research guidance and proposed projects, which are not findings from the selected papers. Citations/numeric checks are deterministic guards, not an entailment guarantee.

Model availability means credentials/policy and recent observed failures, not a live probe or unlimited free quota. Providers marked `disabled` require explicit credit-provider opt-in. No provider calls are made just to render `/models` or the status page. The main report starts with one generation with bounded failover; targeted completion/expansion can add model calls as described above. Progress tracking itself makes no additional LLM requests.

Report citations use short source numbers with page references where available. A Sources appendix retains each full paper title and link. Copy/download and on-screen formatting preserve table separators and separate guidance paragraphs from preceding lists.
