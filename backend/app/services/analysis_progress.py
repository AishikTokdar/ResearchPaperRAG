"""Real preparation milestones shared by the analysis progress stream."""

import hashlib
import json
import threading
import time
from collections.abc import Callable
from typing import Any

from ..config import get_settings
from .gap_analyzer_engine import GapAnalyzerEngine
from .paper_fetcher import PaperFetcher
from .pdf_processor import PDFProcessor
from .research_sessions import ResearchSession


def prepare_analysis(
    session: ResearchSession,
    papers: list[dict[str, Any]],
    uploads: list[tuple[str, bytes]],
    emit: Callable[[dict[str, Any]], None],
    cancelled: threading.Event,
) -> GapAnalyzerEngine:
    if not session.lock.acquire(blocking=False):
        raise ValueError("Another ingestion is active in this session")
    try:
        if cancelled.is_set():
            raise InterruptedError("Analysis cancelled")
        settings = get_settings()
        profile = [
            settings.embedding_chunk_tokens,
            settings.embedding_overlap_tokens,
            settings.max_pdf_pages,
            settings.max_extracted_chars,
        ]
        identity = json.dumps(
            {
                "papers": [
                    {k: v for k, v in paper.items() if k != "evidence_scope"} for paper in papers
                ],
                "uploads": [(name, hashlib.sha256(data).hexdigest()) for name, data in uploads],
                "profile": profile,
            },
            sort_keys=True,
        )
        key = hashlib.sha256(identity.encode()).hexdigest()
        if (
            session.engine is not None
            and session.prepared_key == key
            and time.monotonic() - session.prepared_at < 3600
        ):
            emit(
                {
                    "stage": "index",
                    "percent": 40,
                    "message": "Reusing this session's prepared sources and index",
                }
            )
            return session.engine
        total = len(papers) + len(uploads)
        fetched = []
        uploaded = []
        fetcher = PaperFetcher()
        processor = PDFProcessor()
        for index, paper in enumerate(papers):
            if cancelled.is_set():
                raise InterruptedError("Analysis cancelled")
            emit(
                {
                    "stage": "sources",
                    "percent": 5 + round(index / total * 25),
                    "message": f"Reading paper {index + 1} of {total}",
                    "document_name": paper.get("title", "Research paper"),
                    "documents_completed": index,
                    "documents_total": total,
                }
            )
            text = fetcher.download_and_extract_text(paper)
            fetched.append((paper, text))
        for index, (name, data) in enumerate(uploads, start=len(papers)):
            if cancelled.is_set():
                raise InterruptedError("Analysis cancelled")
            emit(
                {
                    "stage": "sources",
                    "percent": 5 + round(index / total * 25),
                    "message": f"Extracting PDF {index + 1} of {total}",
                    "document_name": name,
                    "documents_completed": index,
                    "documents_total": total,
                }
            )
            result = processor.process_uploaded_file(data, name)
            paper = {
                "id": "upload_" + hashlib.sha256(name.encode() + data).hexdigest(),
                "title": name,
                "evidence_scope": "partial_full_text"
                if any(
                    doc.metadata.get("evidence_scope") == "partial_full_text"
                    for doc in result.chunks
                )
                else "full_text",
            }
            for doc in result.chunks:
                doc.metadata.update(
                    {
                        "paper_id": paper["id"],
                        "paper_title": name,
                        "evidence_scope": paper["evidence_scope"],
                    }
                )
            uploaded.append((paper, result.chunks))
        if cancelled.is_set():
            raise InterruptedError("Analysis cancelled")
        emit(
            {
                "stage": "index",
                "percent": 30,
                "message": "Organizing source passages for indexing",
                "documents_completed": total,
                "documents_total": total,
            }
        )
        engine = GapAnalyzerEngine()
        engine.process_and_index_papers(fetched, uploaded_papers=uploaded, on_progress=emit)
        if cancelled.is_set():
            raise InterruptedError("Analysis cancelled")
        session.engine = engine
        session.prepared_key, session.prepared_at = key, time.monotonic()
        return engine
    finally:
        session.lock.release()
