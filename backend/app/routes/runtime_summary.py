"""
Runtime summary route providing system configuration and provider status.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..config import (
    AI_PROVIDERS,
    get_embedding_fallback_chain,
    get_settings,
    provider_has_credentials,
)
from ..models.schemas import RuntimeProviderRow, RuntimeSummaryResponse
from ..services.model_health import get_provider_status
from ..services.usage_counters import read_counters

router = APIRouter(tags=["Runtime Summary & Metrics"])

_PROVIDER_LABELS: dict[str, str] = {
    "openrouter": "OpenRouter",
    "groq": "Groq",
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "huggingface": "Hugging Face",
    "cerebras": "Cerebras",
    "sambanova": "SambaNova",
}


@router.get("/runtime-summary", response_model=RuntimeSummaryResponse)
def runtime_summary() -> RuntimeSummaryResponse:
    settings = get_settings()
    chain = get_embedding_fallback_chain()
    emb_names = {p.name for p, _ in chain}
    rows: list[RuntimeProviderRow] = []

    for name, prov in AI_PROVIDERS.items():
        has_creds = provider_has_credentials(prov)
        emb = name in emb_names
        models = prov.models or []
        st = get_provider_status(name, has_creds, models)
        llm_ready = st in ("working", "partial")

        rows.append(
            RuntimeProviderRow(
                id=name,
                display_name=_PROVIDER_LABELS.get(name, name.replace("_", " ").title()),
                llm_ready=llm_ready,
                embedding_ready=emb,
                status=st,
            )
        )

    working_n = sum(1 for r in rows if r.status == "working")
    partial_n = sum(1 for r in rows if r.status == "partial")
    unavail_n = sum(1 for r in rows if r.status in ("unavailable", "api_key_not_set", "invalid_api_key"))
    llm_ready_n = sum(1 for r in rows if r.llm_ready)

    if llm_ready_n == 0:
        overall = "error"
    elif working_n > 0 and unavail_n == 0 and partial_n == 0:
        overall = "ok"
    elif (working_n > 0 or partial_n > 0) and (partial_n > 0 or unavail_n > 0):
        overall = "degraded"
    else:
        overall = "ok" if (working_n > 0 or partial_n > 0) else "error"

    total_pdf, total_chats = read_counters()

    return RuntimeSummaryResponse(
        status=overall,
        providers=len(rows),
        working=working_n,
        app_version=settings.app_version,
        default_model=settings.default_model,
        providers_detail=rows,
        embedding_chain_steps=len(chain),
        llm_providers_ready=llm_ready_n,
        rate_limit_upload_per_minute=settings.rate_limit_upload_per_minute,
        rate_limit_ask_per_minute=settings.rate_limit_ask_per_minute,
        max_vector_sessions=settings.max_vector_sessions,
        faiss_session_max_age_days=settings.faiss_session_max_age_days,
        total_pdf_uploads=total_pdf,
        total_chat_completions=total_chats,
    )
