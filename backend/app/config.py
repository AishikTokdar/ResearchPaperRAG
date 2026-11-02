import json
import os
import re
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


_DEFAULT_CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]


class AIProvider:
    """
    Configuration for an AI provider.

    Attributes:
        name: Provider identifier
        base_url: API endpoint URL
        api_key_env: Environment variable name for API key
        models: List of supported model identifiers
        is_enabled: Whether this provider has a valid key
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key_env: str,
        models: list[str],
        embedding_model: str | None = None,
        is_openai_compatible: bool = True,
        access_tier: str = "free",
        model_names: dict[str, str] | None = None,
        preview_models: set[str] | None = None,
    ):
        self.name = name
        self.base_url = base_url
        self.api_key_env = api_key_env
        self.models = models
        self.embedding_model = embedding_model
        self.is_openai_compatible = is_openai_compatible
        self.access_tier = access_tier
        self.model_names = model_names or {}
        self.preview_models = preview_models or set()
        self._api_key: str | None = None

    @property
    def api_key(self) -> str | None:
        """Get API key from environment."""
        if self._api_key is None:
            self._api_key = os.getenv(self.api_key_env)
            if not self._api_key and self.name == "openrouter":
                self._api_key = os.getenv("OPENAI_API_KEY")
        return self._api_key

    @property
    def is_enabled(self) -> bool:
        """Check if provider has valid API key."""
        return bool(self.api_key)


MODEL_CATALOG = json.loads(Path(__file__).with_name("model_catalog.json").read_text(encoding="utf-8"))
DEFAULT_MODEL: str = MODEL_CATALOG["default_model"]
DEFAULT_PROVIDER: str = MODEL_CATALOG["default_provider"]
AI_PROVIDERS: dict[str, AIProvider] = {
    item["name"]: AIProvider(
        name=item["name"], base_url=item["base_url"], api_key_env=item["api_key_env"],
        models=[m["id"] for m in item["models"]], embedding_model=item["embedding_model"],
        access_tier=item["access_tier"], model_names={m["id"]: m["name"] for m in item["models"]},
        preview_models={m["id"] for m in item["models"] if m["preview"]},
    ) for item in MODEL_CATALOG["providers"]
}
PROVIDER_PRIORITY: list[str] = [item["name"] for item in MODEL_CATALOG["providers"]]


class Settings(BaseSettings):
    app_name: str = "ResearchPaperRAG API"
    app_version: str = "2.0.0"
    debug: bool = False
    openrouter_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "OPENAI_API_KEY"),
    )
    openrouter_api_base: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices("OPENROUTER_API_BASE", "OPENAI_API_BASE"),
    )
    groq_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GROQ_API_KEY", "GROQ_API_KEYS"),
    )
    groq_api_keys: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GROQ_API_KEYS"),
    )
    google_api_key: str | None = None
    hf_api_key: str | None = None
    openai_direct_api_key: str | None = None

    embedding_openai_direct: bool = Field(default=False)
    embedding_use_remote: bool = False

    default_model: str = DEFAULT_MODEL
    default_provider: str = DEFAULT_PROVIDER
    allow_credit_providers: bool = False
    temperature: float = 0.0
    max_tokens: int = 2048

    embedding_chunk_tokens: int = Field(default=224, ge=32, le=254)
    embedding_overlap_tokens: int = Field(default=32, ge=0, le=64)
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_k: int = 4
    context_token_budget: int = Field(default=4000, ge=512, le=16000)
    report_max_tokens: int = Field(default=3500, ge=512, le=8192)
    followup_max_tokens: int = Field(default=800, ge=128, le=4096)
    llm_max_attempts: int = Field(default=3, ge=1, le=6)
    llm_timeout_seconds: float = Field(default=30, ge=1, le=120)
    llm_request_deadline_seconds: float = Field(default=60, ge=1, le=180)
    max_concurrent_requests: int = Field(default=4, ge=1, le=32)
    max_pdf_pages: int = Field(default=200, ge=1, le=1000)
    pdf_memory_limit_mb: int = Field(default=512, ge=128, le=4096)
    max_extracted_chars: int = Field(default=500000, ge=1000, le=2000000)
    max_document_chunks: int = Field(default=1000, ge=10, le=5000)
    # Comma-separated IPs/CIDRs of reverse proxies allowed to supply X-Real-IP.
    trusted_proxy_ips: str = ""
    allowed_hosts: str = "localhost,127.0.0.1,[::1],testserver"
    telemetry_tunnel_dsn: str | None = None

    faiss_persist_dir: str = "faiss_index"
    max_vector_sessions: int = Field(default=64, ge=4, le=10_000)
    faiss_session_max_age_days: int = Field(default=3, ge=0, le=365)

    rate_limit_upload_per_minute: int = Field(default=8, ge=0, le=500)
    rate_limit_ask_per_minute: int = Field(default=90, ge=0, le=5000)
    cors_origins_csv: str | None = Field(
        default=None,
        validation_alias="CORS_ORIGINS",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        raw = self.cors_origins_csv
        if not raw or not raw.strip():
            return list(_DEFAULT_CORS_ORIGINS)
        parts = [p.strip().rstrip("/") for p in raw.split(",") if p.strip()]
        if "*" in parts or "*" in raw:
            return ["*"]
        return parts if parts else list(_DEFAULT_CORS_ORIGINS)

    # File upload settings
    max_file_size: int = 50 * 1024 * 1024  # 50MB

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def migrate_retired_default(self) -> "Settings":
        provider = AI_PROVIDERS.get(self.default_provider)
        if provider is not None and self.default_model not in provider.models:
            self.default_model = provider.models[0]
        return self



@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def get_all_provider_api_keys(provider_name: str, custom_key: str | None = None) -> list[str]:
    """
    Extract all API keys for any given provider from:
    1. Custom passed API key (single string or comma/semicolon/space-separated list)
    2. Settings & Environment variables for that provider (single or comma-separated)

    Supports env variables:
    - gemini: GOOGLE_API_KEY, GOOGLE_API_KEYS, GEMINI_API_KEY, GEMINI_API_KEYS
    - groq: GROQ_API_KEY, GROQ_API_KEYS
    - cerebras: CEREBRAS_API_KEY, CEREBRAS_API_KEYS
    - sambanova: SAMBANOVA_API_KEY, SAMBANOVA_API_KEYS
    - huggingface: HF_API_KEY, HF_API_KEYS, HUGGINGFACE_API_KEY
    - openrouter: OPENROUTER_API_KEY, OPENROUTER_API_KEYS, OPENAI_API_KEY
    - openai: OPENAI_DIRECT_API_KEY, OPENAI_API_KEY

    Returns a list of unique non-empty key strings.
    """
    settings = get_settings()
    keys: list[str] = []
    seen: set[str] = set()

    def add_key_str(raw: str | None):
        if not raw:
            return
        for part in re.split(r"[,;\s]+", raw):
            k = part.strip()
            if k and k not in seen:
                seen.add(k)
                keys.append(k)

    add_key_str(custom_key)

    pname = (provider_name or "").lower().strip()
    if pname == "gemini":
        add_key_str(settings.google_api_key)
        add_key_str(os.getenv("GOOGLE_API_KEYS"))
        add_key_str(os.getenv("GOOGLE_API_KEY"))
        add_key_str(os.getenv("GEMINI_API_KEYS"))
        add_key_str(os.getenv("GEMINI_API_KEY"))
    elif pname == "groq":
        add_key_str(getattr(settings, "groq_api_keys", None))
        add_key_str(settings.groq_api_key)
        add_key_str(os.getenv("GROQ_API_KEYS"))
        add_key_str(os.getenv("GROQ_API_KEY"))
    elif pname == "sambanova":
        add_key_str(os.getenv("SAMBANOVA_API_KEYS"))
        add_key_str(os.getenv("SAMBANOVA_API_KEY"))
    elif pname == "huggingface":
        add_key_str(settings.hf_api_key)
        add_key_str(os.getenv("HF_API_KEYS"))
        add_key_str(os.getenv("HF_API_KEY"))
        add_key_str(os.getenv("HUGGINGFACE_API_KEY"))
    elif pname == "openrouter":
        add_key_str(settings.openrouter_api_key)
        add_key_str(os.getenv("OPENROUTER_API_KEYS"))
        add_key_str(os.getenv("OPENROUTER_API_KEY"))
        add_key_str(os.getenv("OPENAI_API_KEY"))
    elif pname == "openai":
        add_key_str(settings.openai_direct_api_key)
        add_key_str(os.getenv("OPENAI_API_KEY"))
    else:
        env_base = pname.upper()
        add_key_str(os.getenv(f"{env_base}_API_KEYS"))
        add_key_str(os.getenv(f"{env_base}_API_KEY"))

    return keys


def get_all_groq_api_keys(custom_key: str | None = None) -> list[str]:
    """Backward-compatible helper for Groq API keys."""
    return get_all_provider_api_keys("groq", custom_key)


def provider_is_allowed(provider: AIProvider) -> bool:
    """Credit/trial providers require an explicit server-side opt-in."""
    return provider.access_tier == "free" or get_settings().allow_credit_providers


def provider_has_credentials(provider: AIProvider) -> bool:
    """True if LLM calls can authenticate (env + pydantic Settings + multi-keys)."""
    return provider_is_allowed(provider) and bool(get_all_provider_api_keys(provider.name, provider.api_key))


def get_available_providers() -> list[str]:
    """Get list of providers with valid API keys."""
    return [name for name, provider in AI_PROVIDERS.items() if provider_has_credentials(provider)]


def get_provider(name: str) -> AIProvider | None:
    """Get provider configuration by name."""
    return AI_PROVIDERS.get(name)


def get_default_provider() -> AIProvider:
    """Get the default or first available provider."""
    settings = get_settings()

    default = AI_PROVIDERS.get(settings.default_provider)
    if default and provider_has_credentials(default):
        return default

    for name in PROVIDER_PRIORITY:
        provider = AI_PROVIDERS.get(name)
        if provider and provider_has_credentials(provider):
            return provider

    return AI_PROVIDERS["openrouter"]


def get_fallback_chain() -> list[AIProvider]:
    """Return an ordered list of providers that have credentials for LLM calls."""
    return [
        AI_PROVIDERS[name]
        for name in PROVIDER_PRIORITY
        if name in AI_PROVIDERS and provider_has_credentials(AI_PROVIDERS[name])
    ]


def get_embedding_fallback_chain() -> list[tuple[AIProvider, str]]:
    """
    Ordered embedding backends to try (upload / index build).

    Puts the configured default provider first when it defines an embedding model,
    then walks PROVIDER_PRIORITY (Groq is skipped because it has no embedding model; Gemini and Hugging Face are used when configured).
    Direct OpenAI embeddings run only if embedding_openai_direct is true.
    """
    chain: list[tuple[AIProvider, str]] = []
    seen: set[tuple[str, str]] = set()
    settings = get_settings()

    def has_embedding_key(provider: AIProvider) -> bool:
        if provider.name == "openrouter":
            return bool(provider.api_key or settings.openrouter_api_key)
        if provider.name == "openai":
            if not settings.embedding_openai_direct:
                return False
            return bool(provider.api_key or settings.openai_direct_api_key)
        if provider.name == "groq":
            if not provider.embedding_model:
                return False
            return bool(provider.api_key or settings.groq_api_key)
        if provider.name == "gemini":
            return bool(provider.api_key or settings.google_api_key)
        if provider.name == "huggingface":
            return bool(provider.api_key or settings.hf_api_key)
        return provider.is_enabled

    def append_provider(provider: AIProvider | None) -> None:
        if provider is None or not provider_is_allowed(provider) or not has_embedding_key(provider):
            return
        model = provider.embedding_model
        if not model:
            return
        sig = (provider.base_url, model)
        if sig in seen:
            return
        seen.add(sig)
        chain.append((provider, model))

    append_provider(AI_PROVIDERS.get(settings.default_provider))

    for name in PROVIDER_PRIORITY:
        append_provider(AI_PROVIDERS.get(name))

    gem = AI_PROVIDERS.get("gemini")
    if gem and has_embedding_key(gem):
        m2 = "gemini-embedding-2"
        sig = (gem.base_url, m2)
        if sig not in seen:
            seen.add(sig)
            chain.append((gem, m2))

    return chain
