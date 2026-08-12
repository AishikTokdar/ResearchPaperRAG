import gc
import logging
import os
from typing import Any, cast

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import warnings

try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from langchain_huggingface import HuggingFaceEmbeddings
except (ImportError, ModuleNotFoundError):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from ..config import AIProvider, get_embedding_fallback_chain, get_settings
from .embedding_clients import GeminiEmbeddings, GroqEmbeddings

logger = logging.getLogger(__name__)


class VectorStoreService:
    def __init__(self, session_id: str) -> None:
        self.settings = get_settings()
        self._session_id = session_id.strip()
        self.vectorstore: FAISS | None = None
        self.embeddings: Embeddings | None = None

        self._try_load_from_disk()

    @staticmethod
    def sessions_directory() -> str:
        settings = get_settings()
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            settings.faiss_persist_dir,
            "sessions",
        )

    @staticmethod
    def disk_path_for_session(session_id: str) -> str:
        return os.path.join(
            VectorStoreService.sessions_directory(),
            session_id.strip(),
        )

    def _resolve_api_key(self, provider: AIProvider) -> str | None:
        if provider.name == "openrouter":
            return provider.api_key or self.settings.openrouter_api_key
        if provider.name == "openai":
            return provider.api_key or self.settings.openai_direct_api_key
        if provider.name == "groq":
            return provider.api_key or self.settings.groq_api_key
        if provider.name == "gemini":
            return provider.api_key or self.settings.google_api_key
        if provider.name == "huggingface":
            return provider.api_key or self.settings.hf_api_key
        return provider.api_key

    def _make_local_cpu_embeddings(self, model: str) -> Embeddings:
        mk: dict[str, Any] = {"device": "cpu"}
        ek: dict[str, Any] = {"batch_size": 16, "normalize_embeddings": True}
        return HuggingFaceEmbeddings(model_name=model, model_kwargs=mk, encode_kwargs=ek)

    def _make_embeddings(self, provider: AIProvider, model: str) -> Embeddings:
        if provider.name == "huggingface":
            key = self._resolve_api_key(provider)
            mk: dict[str, Any] = {"device": "cpu"}
            if key:
                mk["token"] = key
            return HuggingFaceEmbeddings(model_name=model, model_kwargs=mk)
        if provider.name == "groq":
            key = self._resolve_api_key(provider)
            if not key:
                raise ValueError("GROQ_API_KEY missing")
            return GroqEmbeddings(
                api_key=key,
                model=model,
                base_url=provider.base_url.rstrip("/"),
            )
        if provider.name == "gemini":
            key = self._resolve_api_key(provider)
            if not key:
                raise ValueError("GOOGLE_API_KEY missing")
            return GeminiEmbeddings(api_key=key, model=model)
        key = self._resolve_api_key(provider)
        base_url = (
            self.settings.openrouter_api_base
            if provider.name == "openrouter"
            else provider.base_url
        )
        return OpenAIEmbeddings(
            base_url=base_url,
            model=model,
            api_key=cast(Any, key),
        )

    def _embedding_candidates(self) -> list[tuple[AIProvider, str]]:
        return get_embedding_fallback_chain()

    def _persist_path(self) -> str:
        return self.disk_path_for_session(self._session_id)

    def _try_load_from_disk(self) -> None:
        path = self._persist_path()
        index_file = os.path.join(path, "index.faiss")
        if not os.path.exists(index_file):
            return

        last_error: Exception | None = None
        for provider, model in self._embedding_candidates():
            try:
                emb = self._make_embeddings(provider, model)
                self.vectorstore = FAISS.load_local(
                    path,
                    emb,
                    allow_dangerous_deserialization=True,
                )
                self.embeddings = emb
                return
            except Exception as exc:
                last_error = exc

        try:
            emb = self._make_local_cpu_embeddings(
                "sentence-transformers/all-MiniLM-L6-v2"
            )
            self.vectorstore = FAISS.load_local(
                path,
                emb,
                allow_dangerous_deserialization=True,
            )
            self.embeddings = emb
            return
        except Exception:
            pass

    def save_to_disk(self) -> None:
        if self.vectorstore is None:
            return
        path = self._persist_path()
        os.makedirs(path, exist_ok=True)
        self.vectorstore.save_local(path)

    def create_from_documents(self, documents: list[Document]) -> int:
        gc.collect()
        candidates = self._embedding_candidates()

        last_error: Exception | None = None
        for provider, model in candidates:
            try:
                emb = self._make_embeddings(provider, model)
                self.vectorstore = FAISS.from_documents(documents, emb)
                self.embeddings = emb
                self.save_to_disk()
                gc.collect()
                return len(documents)
            except Exception as exc:
                last_error = exc

        try:
            emb = self._make_local_cpu_embeddings(
                "sentence-transformers/all-MiniLM-L6-v2"
            )
            self.vectorstore = FAISS.from_documents(documents, emb)
            self.embeddings = emb
            self.save_to_disk()
            gc.collect()
            return len(documents)
        except Exception as exc:
            last_error = exc

        err = last_error
        detail = f"{type(err).__name__}: {err!r}" if err else "unknown"
        raise RuntimeError(
            f"All embedding providers failed. Last error: {detail}"
        ) from err

    def similarity_search(self, query: str, k: int | None = None) -> list[Document]:
        if self.vectorstore is None:
            raise ValueError("Vector store not initialized. Upload a PDF first.")
        k = k or self.settings.retrieval_k
        return self.vectorstore.similarity_search(query, k=k)

    def get_retriever(self, k: int | None = None):
        if self.vectorstore is None:
            raise ValueError("Vector store not initialized. Upload a PDF first.")
        k = k or self.settings.retrieval_k
        return self.vectorstore.as_retriever(search_kwargs={"k": k})

    @property
    def is_ready(self) -> bool:
        return self.vectorstore is not None

    def clear(self) -> None:
        self.vectorstore = None
        self.embeddings = None
