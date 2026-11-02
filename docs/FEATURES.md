# Feature and integration map

The main product route is `/chat`. Compatibility PDF APIs/components and optional Gradio are separate; they do not share an index with the research workspace.

| Feature | Frontend | Backend / data | Verification |
| --- | --- | --- | --- |
| Topic search and partial failures | `pages/chat.tsx`, `lib/api.ts` | `/api/papers/search`, six source adapters, session catalog | SDK/PubMed fixtures, ranking/dedup/error tests, real browser search |
| Selection and abstracts | `pages/chat.tsx` | Server-trusted IDs, maximum five combined sources | Browser selection, tampering/session tests |
| PDFs and mixed sources | `pages/chat.tsx` | `/api/analyze/stream`, parser, MiniLM tokenizer, FAISS/BM25 | Actual PDF subprocess, API integration and mixed-source browser test |
| Progress, ETA, sections, stop | Progress panel, `analysis-progress.ts`, `sse.ts` | Actual preparation/index milestones, observed headings, heartbeat/cancellation | Protocol, progress, worker-capacity and browser checks |
| Eight report sections | `report-renderer.tsx` | Three retrieval facets, source diversity, one generation with bounded fallback | Complete API workflow and browser rendering; fixture generation, not scientific evaluation |
| Grounding / limited sources | Report renderer | Citation IDs, factual-block/numeric checks, evidence scopes | Unknown/uncited/invented-number rejection, abstract/partial PDF tests |
| Follow-up / Clear Chat | Workspace | POST/DELETE `/api/chat/followup`, bounded server history | API integration, history bounds, clear/reset tests |
| Clear Session | Workspace, `chat-session.ts` | Fresh capability; old server state no longer addressed | Storage/session tests; retention is not immediate erasure |
| Copy / PDF / Markdown / text | Report renderer | Client-side exports, escaped HTML, HTTP(S) links | Injection tests and browser downloads |
| Models | Model selector | `/models`, shared catalog, server-only credentials | Catalog sync, access-tier/provider tests, keyboard navigation |
| Service status | `pages/api-status.tsx` | `/runtime-summary`, current chunk settings/provider policy | Schema and real browser status checks |
| Theme, motion, navigation | Layout/theme, Framer Motion | Browser preferences/storage | Responsive and reduced-motion checks |
| Legacy PDF chat | Chat components/hooks (not main workspace route) | `/upload`, `/status`, `/ask`, `/ask/stream`, seven-stage pipeline | Real parser/FAISS/JSON/SSE integration |
| Optional Gradio/Spaces | `backend/app.py`, `backend/gradio_app.py` | Separate dependency profile | Interface construction smoke checks; no live inference verification |
| Error monitoring | `lib/sentry.ts` | Explicit DSN, optional restricted relay | Privacy/destination tests; no production telemetry sent |

## State and retention

Research engines are session-local, in memory, LRU-bounded by `MAX_VECTOR_SESSIONS`, and expire after 24 hours idle. Restart loses research selections/history/cache: search/analyze again. Matching preparation can reuse its index for one hour. Complete, verified, warning-free reports use a 32-entry engine cache. Evidence, model, prompt and limits participate in cache identity.

Legacy PDF indexes persist under `FAISS_PERSIST_DIR/sessions/<uuid>` using native FAISS and JSON. LRU eviction removes idle disk state when safe. Startup cleanup removes indexes older than `FAISS_SESSION_MAX_AGE_DAYS` (default three); it is not a continuous deletion timer. Incompatible/old indexes need re-upload. Active reads retain an immutable store/index pair during replacement uploads.

Browser capabilities are in localStorage and shared by tabs in that profile. Blocked storage uses a stable in-memory capability until reload. Clear Chat resets conversation while retaining evidence. Clear Session rotates the capability and clears the workspace; old data follows the retention rules above.

## Scope

Tests establish these paths and guards with deterministic external boundaries. They do not verify every account's quota, publisher access, OCR accuracy, citation entailment, hosting capacity or scientific quality. See the deployment and testing guides.
