# Live API integration check

Checked on 2026-11-03 with the current local production frontend at `http://127.0.0.1:5188` pointing directly to `https://aishiktokdar-researchpaperrag.hf.space`. External search, downloading, embedding and generation were real, rather than fixture replacements. Uploaded documents were explicitly labeled synthetic QA material, not research studies.

| Workflow | Observed result |
| --- | --- |
| Health, models, runtime configuration, schema and pipeline information | Successful responses; local MiniLM configuration reported |
| Browser CORS | Local frontend preflight and requests succeeded |
| Academic search | Twelve papers returned for the review query |
| Mixed-source research report | A fetched paper and uploaded QA PDF were ingested; progress streamed and the report displayed |
| Grounded follow-up | Correctly retrieved the QA document's distinctive validation marker; provider fallback succeeded |
| PDF-only research report | Generated and displayed through the live analysis endpoint |
| Markdown, TXT and PDF exports | Downloaded successfully from the local frontend using a live-generated report; headings retained, TXT free of Markdown headings, PDF signature valid |
| Legacy PDF API | Upload and readiness succeeded; JSON and SSE questions returned the correct marker with source references, using `openai/gpt-oss-20b` |
| Session handling | Follow-up history clearing succeeded; browser reset rotated the session ID; a fresh session could not query another session's papers |
| Normal invalid inputs | Blank search rejected with 422; invalid PDF rejected with 400 and readable frontend feedback |
| API documentation | `/docs` and `/redoc` responded |
| Existing root-mounted Gradio | `/config` and `/gradio_api/info` responded; no `/gradio/` mount is required |

The live checks exposed two small response issues, fixed in local source:

- Evidence labels could touch the previous word or closing bold markup. Resolution now inserts spacing, including the bold-marker pattern observed in the live response.
- Streamed generation did not consistently disclose fallback use. Its final warning now matches JSON generation, and a successful fallback alone does not mark a complete report as incomplete.

Backend lint, type checks and 112 offline regression tests passed after those fixes. These local changes require a backend redeploy to affect the hosted API. `backend/app.py` and `backend/README.md` remain unchanged; the existing root-mounted setup is preserved.

The deployment accepted a CORS preflight from an unrelated origin (`https://unrelated-origin.example`). Review the hosted `CORS_ORIGINS` variable and restrict it to intended frontend origins for production. No deployment variables or secrets were changed.

This check exercises the main workflows, not every configured model or optional integration. The `/models` configuration listing does not establish that every model has usable quota, and successful requests do not certify scientific answer quality.
