import gc
import os
import tempfile
from dataclasses import dataclass

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import get_settings


@dataclass
class ProcessedPDF:
    chunks: list[Document]
    file_name: str
    total_pages: int
    total_chunks: int


class PDFProcessor:
    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None
    ):
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
    
    def process_file(self, file_path: str, file_name: str = "document.pdf") -> ProcessedPDF:
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        if not documents:
            raise ValueError("PDF appears to be empty or could not be parsed")
        
        for doc in documents:
            doc.metadata["source_file"] = file_name
        
        chunks = self.text_splitter.split_documents(documents)
        
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)
        
        return ProcessedPDF(
            chunks=chunks,
            file_name=file_name,
            total_pages=len(documents),
            total_chunks=len(chunks)
        )
    
    def process_uploaded_file(self, file_content: bytes, file_name: str) -> ProcessedPDF:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        try:
            result = self.process_file(tmp_path, file_name)
            return result
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            gc.collect()
