"""
Pydantic Schemas

Request and response models for the API.
These ensure type safety and automatic validation.

FastAPI uses these models to build OpenAPI ``components.schemas`` — compare with ``/docs`` while learning.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

# ============================================================================
# Request Models
# ============================================================================


class QuestionRequest(BaseModel):
    """
    Request body for asking questions about uploaded PDFs.

    Attributes:
        question: The user's question about the document
        model: Optional model override (uses default if not specified)
        include_sources: Whether to include source chunks in response
        hybrid_mode: Whether to enable Hybrid Brain Mode (PDF + AI Pretrained Knowledge - NotebookLM style)
        knowledge_mode: "hybrid" (PDF + General AI Knowledge) or "strict" (PDF Only)
    """

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


# ============================================================================
# Response Models
# ============================================================================


class AnswerResponse(BaseModel):
    """
    Response containing the AI-generated answer.

    Attributes:
        answer: The generated answer text
        model_used: Which model generated the response
        sources: Optional list of source chunks used
        processing_time: Time taken to generate response
    """

    answer: str
    model_used: str | None = None
    sources: list[str] | None = None
    processing_time: float | None = None
    warnings: list[str] | None = None


class DocumentFileMeta(BaseModel):
    """
    Metadata for a single uploaded document.
    """

    file_name: str
    page_count: int
    chunks_created: int


class UploadResponse(BaseModel):
    """
    Response after PDF upload and processing.

    Attributes:
        message: Success message
        chunks_created: Total number of text chunks created across all uploaded files
        file_name: Name of primary uploaded file
        files: Metadata list of all active uploaded documents
        total_files: Total active document count
    """

    message: str
    chunks_created: int
    file_name: str | None = None
    files: list[DocumentFileMeta] = []
    total_files: int = 0


class StatusResponse(BaseModel):
    """
    System status response.

    Attributes:
        status: Current status (running, error, etc.)
        message: Human-readable status message
        pdf_loaded: Whether a PDF is currently loaded
        model: Currently configured model
        documents_loaded: Count of active loaded documents
        server_boot_id: Unique UUID generated on each backend server startup
    """

    status: str = "running"
    message: str
    pdf_loaded: bool = False
    model: str | None = None
    documents_loaded: int = 0
    server_boot_id: str | None = None


class ModelInfo(BaseModel):
    """
    Information about an available AI model.
    """

    id: str
    name: str
    provider: str
    is_default: bool = False
    is_available: bool = True
    access_tier: str = "free"
    is_preview: bool = False
    api_key_env: str | None = None


class ModelsResponse(BaseModel):
    """
    Response listing available models.

    Attributes:
        models: List of available models
        default_model: Current default model ID
    """

    models: list[ModelInfo]
    default_model: str


class RuntimeProviderRow(BaseModel):
    """One row in the public runtime / provider dashboard."""

    id: str
    display_name: str
    llm_ready: bool
    embedding_ready: bool
    status: str


class RuntimeSummaryResponse(BaseModel):
    """Aggregated provider health for ``GET /runtime-summary`` (SPA dashboard)."""

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
    """
    Standard error response.

    Attributes:
        detail: Error message
        error_code: Optional error code for programmatic handling
    """

    detail: str
    error_code: str | None = None


class AgentStepInfo(BaseModel):
    """
    Information about an agent pipeline step.

    Used for debugging and transparency about RAG process.

    Attributes:
        agent: Name of the agent
        input_summary: Summary of input data
        output_summary: Summary of output data
        duration_ms: Processing time in milliseconds
    """

    agent: str
    input_summary: str
    output_summary: str
    duration_ms: float
