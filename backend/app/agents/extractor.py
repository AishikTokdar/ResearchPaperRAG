"""
Extractor Agent

Retrieves relevant document chunks from the vector store
based on the user's question.
"""

from typing import Any

from langchain_core.documents import Document

from ..services.vector_store import VectorStoreService
from .base_agent import BaseAgent


class ExtractorAgent(BaseAgent):
    def __init__(self, vector_service: VectorStoreService, k: int = 4):
        super().__init__(
            name="extractor", description="Retrieves relevant document chunks from vector store"
        )
        self.vector_service = vector_service
        self.k = k

    def process(self, input_data: str, context: dict[str, Any]) -> list[Document]:
        question = input_data
        k = context.get("retrieval_k", self.k)

        chunks = self.vector_service.similarity_search(question, k=min(k * 3, 60))

        context["retrieved_chunks"] = len(chunks)
        context["chunk_sources"] = [chunk.metadata.get("page", "N/A") for chunk in chunks]

        return chunks
