import hashlib
import json
import logging
import os
import shutil
import tempfile
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from langchain_huggingface import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from ..config import AIProvider, get_embedding_fallback_chain, get_settings
from .chunking import LOCAL_EMBEDDING_MODEL
from .embedding_clients import GeminiEmbeddings, GroqEmbeddings
from .hybrid_retrieval import HybridIndex

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def get_local_embeddings(model: str) -> Embeddings:
    return HuggingFaceEmbeddings(
        model_name=model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"batch_size": 16, "normalize_embeddings": True},
    )


class VectorStoreService:
    def __init__(self, session_id: str) -> None:
        self.settings = get_settings()
        self._session_id = session_id.strip()
        self.vectorstore: FAISS | None = None
        self.embeddings: Embeddings | None = None
        self._embedding_spec: dict[str, str] | None = None
        self._write_lock = threading.Lock()
        self._hybrid: HybridIndex | None = None
        self._read_state: tuple[FAISS, HybridIndex] | None = None

        self._try_load_from_disk()

    @property
    def session_id(self) -> str:
        return self._session_id

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
        return get_local_embeddings(model)

    def _make_embeddings(self, provider: AIProvider, model: str) -> Embeddings:
        if provider.name == "huggingface":
            key = self._resolve_api_key(provider)
            mk: dict[str, Any] = {"device": "cpu"}
            if key:
                mk["token"] = key
            ek: dict[str, Any] = {"normalize_embeddings": True}
            return HuggingFaceEmbeddings(model_name=model, model_kwargs=mk, encode_kwargs=ek)

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
        options: dict[str, Any] = {
            "base_url": base_url,
            "model": model,
            "api_key": key,
            "max_retries": 0,
            "timeout": 30,
        }
        return OpenAIEmbeddings(**options)

    def _embedding_candidates(self) -> list[tuple[AIProvider, str]]:
        return get_embedding_fallback_chain()

    def _persist_path(self) -> str:
        return self.disk_path_for_session(self._session_id)

    def _try_load_from_disk(self) -> None:
        # Never load the old pickle docstore, even when an index.faiss exists.
        path = Path(self._persist_path())
        manifest = path / "metadata.json"
        if not manifest.is_file():
            return
        try:
            if (
                manifest.stat().st_size > 10000000
                or (path / "index.faiss").stat().st_size > 100000000
            ):
                return
            data = json.loads(manifest.read_text(encoding="utf-8"))
            index_bytes = (path / "index.faiss").read_bytes()
            if hashlib.sha256(index_bytes).hexdigest() != data["index_sha256"]:
                return
            spec = data["embedding"]
            if spec["provider"] == "local":
                emb = self._make_local_cpu_embeddings(spec["model"])
            else:
                candidate = next(
                    (
                        (p, m)
                        for p, m in self._embedding_candidates()
                        if p.name == spec["provider"] and m == spec["model"]
                    ),
                    None,
                )
                if candidate is None:
                    return  # Never substitute an incompatible embedding space.
                emb = self._make_embeddings(*candidate)
            index = faiss.read_index(str(path / "index.faiss"))
            documents = {key: Document(**value) for key, value in data["documents"].items()}
            mapping = {int(key): value for key, value in data["mapping"].items()}
            self.vectorstore = FAISS(emb, index, InMemoryDocstore(documents), mapping)
            self.embeddings = emb
            self._embedding_spec = spec
        except (OSError, ValueError, KeyError, TypeError, RuntimeError):
            logger.warning("Session index could not be safely restored; upload documents again")

    def save_to_disk(self, store: FAISS | None = None, spec: dict[str, str] | None = None) -> None:
        store = store if store is not None else self.vectorstore
        spec = spec if spec is not None else self._embedding_spec
        if store is None or spec is None:
            return
        path = Path(self._persist_path())
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=path) as temporary:
            temp = Path(temporary)
            faiss.write_index(store.index, str(temp / "index.faiss"))
            data = {
                "embedding": spec,
                "index_sha256": hashlib.sha256((temp / "index.faiss").read_bytes()).hexdigest(),
                "mapping": store.index_to_docstore_id,
                "documents": {
                    key: {"page_content": doc.page_content, "metadata": doc.metadata}
                    for key, doc in cast(InMemoryDocstore, store.docstore)._dict.items()
                },
            }
            (temp / "metadata.json").write_text(json.dumps(data), encoding="utf-8")
            os.replace(temp / "index.faiss", path / "index.faiss")
            os.replace(temp / "metadata.json", path / "metadata.json")

    def create_from_documents(self, documents: list[Document]) -> int:
        with self._write_lock:
            candidates = self._embedding_candidates() if self.settings.embedding_use_remote else []
            embeddings: list[tuple[Embeddings, dict[str, str]]] = []
            for provider, model in candidates:
                try:
                    embeddings.append(
                        (
                            self._make_embeddings(provider, model),
                            {"provider": provider.name, "model": model},
                        )
                    )
                except Exception:
                    logger.warning("Embedding initialization failed for %s", provider.name)
            local_model = LOCAL_EMBEDDING_MODEL
            # Construct local embeddings only if remote indexing has not succeeded.
            for emb, spec in embeddings:
                try:
                    store = FAISS.from_documents(documents, emb)
                    self.save_to_disk(store, spec)
                    self.vectorstore, self.embeddings, self._embedding_spec = store, emb, spec
                    self._hybrid = HybridIndex(documents)
                    self._read_state = (store, self._hybrid)
                    return len(documents)
                except Exception:
                    logger.warning("Remote embedding index failed; trying next configured backend")
            emb = self._make_local_cpu_embeddings(local_model)
            store = FAISS.from_documents(documents, emb)
            spec = {"provider": "local", "model": local_model}
            self.save_to_disk(store, spec)
            self.vectorstore, self.embeddings, self._embedding_spec = store, emb, spec
            self._hybrid = HybridIndex(documents)
            self._read_state = (store, self._hybrid)
            return len(documents)

    def discard_persisted_index_if_idle(self) -> None:
        if not self._write_lock.acquire(blocking=False):
            return
        try:
            path = Path(self._persist_path())
            root = Path(self.sessions_directory()).resolve()
            if not path.is_symlink() and path.resolve().parent == root and path.is_dir():
                shutil.rmtree(path)
        except OSError:
            logger.warning("Could not remove evicted session index")
        finally:
            self._write_lock.release()

    def similarity_search(self, query: str, k: int | None = None) -> list[Document]:
        if self.vectorstore is None:
            raise ValueError("Vector store not initialized. Upload a PDF first.")
        k = k or self.settings.retrieval_k
        state = self._read_state
        store = self.vectorstore
        if state is None or state[0] is not store:
            documents = [
                store.docstore.search(doc_id) for doc_id in store.index_to_docstore_id.values()
            ]
            state = (store, HybridIndex([doc for doc in documents if isinstance(doc, Document)]))
            self._read_state = state
        # One immutable store/lexical-index pair per read, even during a replacement upload.
        return state[1].search(state[0], query, k=max(30, k))[:k]

    @property
    def document_count(self) -> int:
        store = self.vectorstore
        if store is None:
            return 0
        documents = [
            store.docstore.search(doc_id) for doc_id in store.index_to_docstore_id.values()
        ]
        return len(
            {
                str(doc.metadata.get("document_id") or doc.metadata.get("source_file", "document"))
                for doc in documents
                if isinstance(doc, Document)
            }
        )

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
        self._hybrid = None
        self._read_state = None
