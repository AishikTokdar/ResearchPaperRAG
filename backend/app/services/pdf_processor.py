import gc
import hashlib
import os
import tempfile
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import get_settings
from .chunking import split_documents
from .pdf_extraction import extract_pdf


@dataclass
class ProcessedPDF:
    chunks: list[Document]
    file_name: str
    total_pages: int
    total_chunks: int


class PDFProcessor:
    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        settings = get_settings()
        self._legacy_splitter = (
            RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
                if chunk_overlap is not None
                else min(settings.chunk_overlap, chunk_size - 1),
            )
            if chunk_size is not None
            else None
        )
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def process_file(self, file_path: str, file_name: str = "document.pdf") -> ProcessedPDF:
        settings = get_settings()
        parsed = extract_pdf(file_path)
        documents = [
            Document(
                page_content=page["text"],
                metadata={
                    "page": page["page"],
                    "evidence_scope": "full_text" if parsed["complete"] else "partial_full_text",
                },
            )
            for page in parsed["pages"]
        ]

        for doc in documents:
            doc.metadata["source_file"] = file_name

        if self._legacy_splitter is not None:
            documents = self._legacy_splitter.split_documents(documents)
        chunks = split_documents(
            documents, settings.embedding_chunk_tokens, settings.embedding_overlap_tokens
        )

        if len(chunks) > settings.max_document_chunks:
            raise ValueError("PDF exceeds the chunk limit")

        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)

        return ProcessedPDF(
            chunks=chunks,
            file_name=file_name,
            total_pages=parsed["total_pages"],
            total_chunks=len(chunks),
        )

    def process_uploaded_file(self, file_content: bytes, file_name: str) -> ProcessedPDF:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name

        try:
            result = self.process_file(tmp_path, file_name)
            document_id = hashlib.sha256(file_name.encode() + file_content).hexdigest()
            for chunk in result.chunks:
                chunk.metadata["document_id"] = document_id
            return result
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            gc.collect()
