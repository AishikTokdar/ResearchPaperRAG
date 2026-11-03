# Hugging Face backend + Cloudflare Pages frontend

## Hugging Face Gradio Space

Upload the contents of the entire `backend` folder directly to the root of your Gradio Space, as before. Its `README.md` already contains the SDK metadata; default `requirements.txt` includes Gradio/Spaces and the API dependency profile. **No packaging script is required.** Keep `app.py`, `app/` and both requirements files at the Space root. Exclude local secrets, virtual environments, indexes and caches.

The entrypoint serves the real FastAPI routes on port 7860 and keeps Gradio mounted at `/`. Its configuration and API metadata are available at `/config` and `/gradio_api/info`. Keep the existing Space SDK settings and launcher behavior; a separate `/gradio/` route is not required. MiniLM remains local inference. The separate `gradio_app.py` compatibility PDF UI is also retained, but use `app.py` for the Cloudflare-connected research API.

In Space **Settings → Variables and secrets** configure:

| Name | Type | Value |
| --- | --- | --- |
| `GOOGLE_API_KEY` or another supported provider key | Secret | Your real server-side key |
| `CORS_ORIGINS` | Variable | `https://YOUR-PROJECT.pages.dev` plus exact custom frontend origins, comma separated |
| `ALLOWED_HOSTS` | Variable | `localhost,127.0.0.1,YOUR-SPACE.hf.space` (add any custom API hostname) |
| `MAX_CONCURRENT_REQUESTS` | Variable | Start with `2` on small hardware; measure before increasing |

The platform-provided `SPACE_HOST` is also accepted automatically after validating its `.hf.space` hostname. Use the actual runtime domain from your Space, not the `huggingface.co/spaces/...` repository page. Do not use wildcard CORS values; add preview deployment origins explicitly if needed. API keys stay on Hugging Face, never in frontend settings.

Confirm `https://YOUR-SPACE.hf.space/health`, `/docs`, `/config` and `/gradio_api/info` respond. Browser access requires a publicly reachable Space or a separately configured authenticated gateway; never embed an HF access token in frontend assets. Sleeping/restarting Spaces may cold-start and lose in-memory sessions; search/analyze again after restart. Default local disk is not a durability promise. Gradio's optional dependency advisory constraints remain documented in the dependency review.

## Cloudflare Pages

### Drag and drop

1. Set `VITE_API_BASE_URL=https://YOUR-SPACE.hf.space` in `frontend/.env.local` before building.
2. Inside `frontend`, run `npm ci` once (or when dependencies change), then `npm run build`.
3. Drag **the `frontend/dist` folder** to Cloudflare Pages Direct Upload.

Cloudflare cannot compile React/TypeScript when uploading the raw source folder. Dashboard environment variables do not rebuild already uploaded files. To upload source and have Cloudflare build automatically, use Git integration below. See [Cloudflare Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/).

### Automatic builds via Git

Connect the source Git repository using Pages with:

| Setting | Value |
| --- | --- |
| Root directory | `frontend` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| `NODE_VERSION` | `24` |
| `VITE_API_BASE_URL` | `https://YOUR-SPACE.hf.space` |

Set `VITE_API_BASE_URL` for production and any preview environment you use, then rebuild. It is a public build-time origin, without `/api`, `/gradio`, or a trailing route. Leaving it blank is appropriate for the included local Docker/Nginx deployment, **not** for this separately hosted Pages setup. Keep all provider keys out of Pages variables/assets.

`public/_redirects` supplies SPA navigation for `/chat` and `/api-status`; `wrangler.jsonc` declares `dist` for optional direct uploads. Pages serves static assets; browsers call Hugging Face directly, including SSE and uploads. No Pages Function or API proxy is required. Confirm search, a small PDF report and a follow-up from the real Pages URL after deployment; CORS preflight must allow that exact origin and `X-Chat-Session-Id`.

## Other supported methods

- Local Docker: follow [deployment](DEPLOYMENT.md); `docker compose --env-file backend/.env up --build -d` uses the same-origin Nginx proxy.
- Local Python/Vite or a single-worker remote Uvicorn service: follow the [main setup](../README.md) and [backend setup](../backend/README.md). Configure HTTPS, hosts and CORS for remote services.
- A Hugging Face **Docker** Space may use the root API Dockerfile, with root README metadata `sdk: docker` and `app_port: 7860`. That profile is API-only; use the prepared Gradio bundle when the Gradio SDK/interface is desired.

Reference: [HF configuration](https://huggingface.co/docs/hub/spaces-config-reference), [HF environment/lifecycle](https://huggingface.co/docs/hub/spaces-overview), [Cloudflare React/Pages](https://developers.cloudflare.com/pages/framework-guides/deploy-a-react-site/).
