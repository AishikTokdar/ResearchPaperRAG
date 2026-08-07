from fastapi import APIRouter, Response

from ..config import get_settings
from ..models import ModelInfo, ModelsResponse, StatusResponse
from ..services.llm_service import LLMService

router = APIRouter(tags=["Health & Operations"])


@router.get("/", response_model=StatusResponse)
async def root():
    return StatusResponse(
        status="running",
        message="ResearchPaperRAG API is ready. See /docs and /redoc for the full backend reference."
    )


@router.head("/", include_in_schema=False)
async def root_head():
    return Response(status_code=200)


@router.get("/health", response_model=StatusResponse)
async def health_check():
    from ..main import SERVER_BOOT_ID

    settings = get_settings()
    return StatusResponse(
        status="healthy",
        message="All systems operational. The backend API is ready.",
        model=settings.default_model,
        server_boot_id=SERVER_BOOT_ID,
    )


@router.head("/health", include_in_schema=False)
async def health_head():
    return Response(status_code=200)


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    settings = get_settings()
    models = LLMService.get_available_models()
    
    model_infos = [
        ModelInfo(
            id=m["id"],
            name=m["name"],
            provider=m["provider"],
            is_default=m["is_default"],
            is_available=m.get("is_available", True),
            api_key_env=m.get("api_key_env"),
        )
        for m in models
    ]
    
    return ModelsResponse(
        models=model_infos,
        default_model=settings.default_model
    )


@router.get("/pipeline-info")
async def pipeline_info():
    stages: list[dict] = [
        {
            "order": 1,
            "name": "Extractor",
            "description": "Retrieves relevant document chunks from the FAISS vector store via similarity search.",
        },
        {
            "order": 2,
            "name": "Analyzer",
            "description": "Filters duplicates and low-quality chunks; scores remaining chunks for relevance.",
        },
        {
            "order": 3,
            "name": "Preprocessor",
            "description": "Normalizes unicode, collapses whitespace, and trims excessively long chunks.",
        },
        {
            "order": 4,
            "name": "Optimizer",
            "description": "Reorders chunks by relevance and trims combined context to fit the token budget.",
        },
        {
            "order": 5,
            "name": "Synthesizer",
            "description": "Generates a comprehensive answer using the selected LLM and optimized context.",
        },
        {
            "order": 6,
            "name": "Validator",
            "description": "Quality-checks length, coherence, and uncertainty markers in the answer.",
        },
        {
            "order": 7,
            "name": "Assembler",
            "description": "Packages answer with source citations, model info, and pipeline telemetry.",
        },
    ]
    return {"pipeline": stages, "total_agents": len(stages)}
