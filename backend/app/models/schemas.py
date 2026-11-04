"""
Pydantic Schemas

Request and response models for the API.
These ensure type safety and automatic validation.

FastAPI uses these models to build OpenAPI ``components.schemas`` — compare with ``/docs`` while learning.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    model: str | None = Field(default=None, max_length=150)
    include_sources: bool = True
    hybrid_mode: bool = False
    knowledge_mode: Literal["hybrid", "strict"] = "strict"

    @model_validator(mode="after")
    def align_mode(self):
        if "knowledge_mode" in self.model_fields_set:
            if "hybrid_mode" in self.model_fields_set and self.hybrid_mode != (
                self.knowledge_mode == "hybrid"
            ):
                raise ValueError("Conflicting knowledge modes")
            self.hybrid_mode = self.knowledge_mode == "hybrid"
        else:
            self.knowledge_mode = "hybrid" if self.hybrid_mode else "strict"
        if not self.question.strip():
            raise ValueError("Question cannot be blank")
        return self


class AnswerResponse(BaseModel):
    answer: str
    model_used: str | None = None
    sources: list[str] | None = None
    processing_time: float | None = None
    warnings: list[str] | None = None


class DocumentFileMeta(BaseModel):
    file_name: str
    page_count: int
    chunks_created: int


class UploadResponse(BaseModel):
    message: str
    chunks_created: int
    file_name: str | None = None
    files: list[DocumentFileMeta] = []
    total_files: int = 0


class StatusResponse(BaseModel):
    status: str = "running"
    message: str
    pdf_loaded: bool = False
    model: str | None = None
    documents_loaded: int = 0
    server_boot_id: str | None = None


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    is_default: bool = False
    is_available: bool = True
    access_tier: str = "free"
    is_preview: bool = False
    api_key_env: str | None = None


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
    default_model: str


class RuntimeProviderRow(BaseModel):
    id: str
    display_name: str
    llm_ready: bool
    embedding_ready: bool
    status: str


class RuntimeSummaryResponse(BaseModel):
    status: str
    providers: int
    working: int
    app_version: str
    default_model: str
    providers_detail: list[RuntimeProviderRow]
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_chunk_tokens: int = 224
    embedding_overlap_tokens: int = 32
    embedding_mode: str = "local"
    pipeline_agents: int = 7
    embedding_chain_steps: int = 0
    llm_providers_ready: int = 0
    rate_limit_upload_per_minute: int = 0
    rate_limit_ask_per_minute: int = 0
    max_vector_sessions: int = 0
    faiss_session_max_age_days: int = 0
    total_pdf_uploads: int = 0
    total_chat_completions: int = 0


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None


class AgentStepInfo(BaseModel):
    agent: str
    input_summary: str
    output_summary: str
    duration_ms: float
