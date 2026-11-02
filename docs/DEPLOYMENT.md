# Deployment and operations

For split Hugging Face Gradio backend / Cloudflare Pages frontend hosting, follow [the hosted deployment guide](HOSTED_DEPLOYMENT.md). Local Docker and standalone Uvicorn instructions below remain supported.

## Supported deployment

Use one FastAPI/Uvicorn worker behind the Nginx frontend. Docker uses Python 3.12, CPU-only Torch, an unprivileged API user, Node 24 for builds and Nginx 1.30. Sessions, quotas, failure state and research caches are in-process: multiple workers/replicas require external state, coordinated quotas and routing.

This is a hardened single-instance application, not an account-authenticated multi-tenant service. A UUID session is a bearer capability. CORS does not stop scripts/curl. Protect sensitive documents/provider budgets with TLS, edge authentication and quotas; keep the backend private. Never put private API keys in `VITE_*` settings.

## Compose

1. Copy `backend/.env.example` to `backend/.env`, set a real generation key, list public hostnames plus `localhost,127.0.0.1,backend` for probes in `ALLOWED_HOSTS` (without scheme/port), and explicit browser origins in `CORS_ORIGINS`. Avoid wildcards.
2. Run `docker compose --env-file backend/.env config --quiet`, then `docker compose --env-file backend/.env up --build -d`. The CLI env file supplies Compose interpolation as well as runtime configuration.
3. Frontend ports are 80 and 5173. Backend host port 8000 binds to loopback; internal traffic uses `backend:8000`.
4. Configure the public TLS/access-control proxy. For per-client quotas, set `TRUSTED_PROXY_IPS` to the immediate trusted proxy IP/CIDR; it must overwrite `X-Real-IP`. Nginx overwrites forwarding headers. Uvicorn proxy rewriting is disabled so the application's trust check sees the actual peer.
5. Persist `faiss_data` and `hf_cache`; protect their permissions/backups. Compose bounds the API to 3 GiB, two CPUs and a PID limit. Tune against measured hardware/corpus usage. Unix parser children have their own address-space/CPU limit; Windows needs host resource controls in addition to the timeout.

Nginx preserves API paths, including research routes, `/ask/stream`, `/status`, `/models`, `/runtime-summary`, `/pipeline-info`, docs and schema. `/api-status` is a SPA route. SSE buffering/cache are off, upload allowance is 51 MiB including multipart overhead, and read timeout is 300 seconds between chunks. Configure upstream proxies/CDNs likewise. See [Nginx proxy documentation](https://nginx.org/en/docs/http/ngx_http_proxy_module.html).

Empty production `VITE_API_BASE_URL` means same origin. Split hosting needs an explicit HTTPS API origin without `/api`, plus matching API CORS/hosts. Browser URL/storage overrides cannot redirect production traffic. Docker contexts exclude secrets, dependencies, user documents/indexes and caches.

## Dependencies

`backend/requirements-api.txt` is the API-only profile used by Docker, core development and audits. Default `backend/requirements.txt` adds Gradio/Spaces so the entire backend folder can be uploaded directly to a Gradio Space. `requirements-gradio.txt` is an alias for that full profile. The documented Gradio/Pillow advisory constraint applies to the full profile; primary API Docker images exclude it.

The installed 98-package API closure audited clean after security updates to AnyIO, filelock, setuptools and urllib3; reproduce using `python scripts/audit_core.py`. This is an installed Windows environment result, not an unbuilt Linux image result.

Python requirements have reviewed major bounds but are not a fully locked transitive environment. Before release, resolve/audit an exact target-platform environment and preserve its lock/SBOM/image digest. Run `pip-audit` there and `npm audit --omit=dev` for frontend runtime dependencies. A developer environment containing optional packages is not the release image. Earlier development-tool advisories remain recorded in the project documentation.

## Defaults

| Control | Default |
| --- | --- |
| Expensive HTTP requests / CPU workers | 4 each; disconnect cannot release a running CPU slot |
| Upload quota | 8/IP/60s, includes status/ingestion |
| Ask/search/report quota | 90/IP/60s |
| JSON body | 128 KiB |
| Uploaded PDFs | 50 MiB combined; five research sources or three legacy PDFs |
| Parser | 200 pages, 500,000 characters, 30s, 512 MiB Unix address space, 10 MB page stream |
| Indexed selection | 1,000 chunks |
| MiniLM chunk / overlap | 224 / 32 word pieces, bounded below 256-token model limit |
| Evidence / report / follow-up | 4,000 estimated evidence tokens / 3,500 / 800 output tokens |
| Generation | Three attempts maximum, 30s attempt timeout, 60s request budget |
| Source sessions | 64, with LRU/idle retention |

Evidence budgeting estimates provider input usage; prompts/questions and up to 256 conversational tokens are additional. Measure provider-reported usage before claiming savings. Preparation cancellation is checked between stages; running parser/embedding work keeps its slot until exit. OS/container limits remain necessary: a parser process is not a complete security sandbox.

## Operations and recovery

- `/health` is liveness. Runtime status means configured credentials/policy/recent failures, not a live provider probe. Confirm an authorized real generation before release.
- Cold ingestion may download model/tokenizer weights. Provision Hugging Face and tiktoken caches for offline operation; test permissions as UID 10001.
- Observe bounded provider-failure and `llm_usage` logs; do not enable prompt/evidence logging. Counter storage is best-effort and must not break answers/status.
- Re-upload corrupt/incompatible legacy indexes. Research state must be searched/analyzed after restart. Do not enable unsafe pickle loading.
- Quotas, model retirements and academic outages are external failures; limited-source messages/errors are expected. Do not repeatedly regenerate without improving evidence.
- Stop traffic before the 40-second graceful shutdown period. Interrupted writes are rejected by index integrity checks on restore.
- Telemetry requires an explicit frontend DSN; replay/traces/logs/default PII are off. The legacy relay requires one exact `TELEMETRY_TUNNEL_DSN`.

## Release checks still required

Run the testing guide, build both Docker contexts on Linux, audit exact dependencies, check the real HTTPS/proxy deployment, validate configured provider quotas with authorization, and measure concurrent ingestion/generation memory and p95 latency.

The local Windows audit validated Nginx syntax but could not run its listeners or Docker. Built frontend/API integration used Vite's equivalent path-preserving preview proxy. No live inference quota was consumed. Universal production certification is not claimed.
