"""
Analyzer Agent

Analyzes the retrieved chunks for relevance and quality.
Filters out low-quality or irrelevant chunks.
"""

from typing import Any

from langchain_core.documents import Document

from .base_agent import BaseAgent


class AnalyzerAgent(BaseAgent):
    def __init__(self, min_content_length: int = 1):
        super().__init__(
            name="analyzer", description="Analyzes and filters retrieved chunks for quality"
        )
        self.min_content_length = min_content_length

    def process(self, input_data: list[Document], context: dict[str, Any]) -> list[Document]:
        chunks = input_data

        filtered_chunks = []
        seen_content = set()

        for chunk in chunks:
            content = chunk.page_content.strip()

            if len(content) < self.min_content_length:
                continue

            content_hash = (
                chunk.metadata.get("source_file"),
                " ".join(content.split()),
            )
            if content_hash in seen_content:
                continue

            seen_content.add(content_hash)
            filtered_chunks.append(chunk)

        context["original_chunks"] = len(chunks)
        context["filtered_chunks"] = len(filtered_chunks)
        context["chunks_removed"] = len(chunks) - len(filtered_chunks)

        return filtered_chunks
