"""Session-bound search, trusted paper ingestion, and grounded literature synthesis."""

import asyncio
import json
import logging
import threading
import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from ..config import DEFAULT_MODEL, get_settings
from ..services.analysis_progress import prepare_analysis
from ..services.gap_analyzer_engine import GapAnalyzerEngine
from ..services.ip_rate_limit import check_ask_rate_limit, check_upload_rate_limit
from ..services.paper_fetcher import PaperFetcher
from ..services.request_limits import run_bounded_worker
from ..services.research_sessions import ResearchSession, ResearchSessionRegistry
from .upload import require_session_id

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Research Gap Analyzer"])
fetcher = PaperFetcher()
sessions = ResearchSessionRegistry()


def research_session(session_id: Annotated[str, Depends(require_session_id)]) -> ResearchSession:
    return sessions.get(session_id, remember=False)


class PaperSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit_per_source: int = Field(default=3, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Query cannot be blank")
        return value.strip()


class SelectedPaper(BaseModel):
    id: str = Field(min_length=1, max_length=300)


class IngestPapersRequest(BaseModel):
    fetched_papers: list[SelectedPaper] = Field(min_length=1, max_length=5)


class AnalyzeGapsRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=2000)
    provider: str = Field(default="gemini", max_length=40)
    model_name: str = Field(default=DEFAULT_MODEL, max_length=150)
    api_key: None = None


class ChatFollowupRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    provider: str = Field(default="gemini", max_length=40)
    model_name: str = Field(default=DEFAULT_MODEL, max_length=150)
    api_key: None = None


@router.post("/api/papers/search", dependencies=[Depends(check_ask_rate_limit)])
def search_papers(req: PaperSearchRequest, session: ResearchSession = Depends(research_session)):
    try:
        source_status: list[dict[str, Any]] = []
        papers = fetcher.search_all(req.query, req.limit_per_source, source_status=source_status)
        if not session.lock.acquire(blocking=False):
            raise HTTPException(409, "Another ingestion is active in this session.")
        try:
            for paper in papers:
                session.papers[paper["id"]] = dict(paper)
            while len(session.papers) > 100:
                del session.papers[next(iter(session.papers))]
            if papers:
                sessions.activate(session)
        finally:
            session.lock.release()
        return {
            "query": req.query,
            "total_found": len(papers),
            "papers": papers,
            "source_status": source_status,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Paper search is temporarily unavailable.") from None


@router.post("/api/papers/ingest", dependencies=[Depends(check_upload_rate_limit)])
def ingest_papers(req: IngestPapersRequest, session: ResearchSession = Depends(research_session)):
    if not session.lock.acquire(blocking=False):
        raise HTTPException(409, "Another ingestion is active in this session.")
    try:
        ids = list(dict.fromkeys(p.id for p in req.fetched_papers))
        if any(paper_id not in session.papers for paper_id in ids):
            raise HTTPException(
                400, "Search for these papers in this session before ingesting them."
            )
        selected = [dict(session.papers[paper_id]) for paper_id in ids]
        papers_with_text = [(paper, fetcher.download_and_extract_text(paper)) for paper in selected]
        engine = GapAnalyzerEngine()
        count = engine.process_and_index_papers(papers_with_text)
        session.engine = engine
        return {"status": "success", "indexed_papers_count": len(selected), "chunks_created": count}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    except Exception:
        raise HTTPException(502, "Unable to index the selected papers. Please retry.") from None
    finally:
        session.lock.release()


def get_engine(session: ResearchSession) -> GapAnalyzerEngine:
    engine = session.engine
    if engine is None:
        raise HTTPException(400, "Load papers in this session first.")
    return engine


@router.post("/api/analyze/gaps", dependencies=[Depends(check_ask_rate_limit)])
def analyze_research_gaps(
    req: AnalyzeGapsRequest, session: ResearchSession = Depends(research_session)
):
    engine = get_engine(session)
    if not req.topic.strip():
        raise HTTPException(400, "Topic cannot be blank.")
    try:
        report = engine.generate_gap_report(req.topic, req.provider, req.model_name)
        return {"topic": req.topic, "report": report}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    except Exception:
        raise HTTPException(
            503, "Report generation is temporarily unavailable. Please retry."
        ) from None


@router.post("/api/chat/followup", dependencies=[Depends(check_ask_rate_limit)])
def chat_followup(req: ChatFollowupRequest, session: ResearchSession = Depends(research_session)):
    engine = get_engine(session)
    if not req.question.strip():
        raise HTTPException(400, "Question cannot be blank.")
    try:
        answer = engine.ask_followup(req.question, req.provider, req.model_name)
        return {"question": req.question, "answer": answer}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    except Exception:
        raise HTTPException(503, "The answer could not be generated. Please retry.") from None


@router.delete("/api/chat/followup", dependencies=[Depends(check_ask_rate_limit)])
def clear_followup(session: ResearchSession = Depends(research_session)):
    try:
        get_engine(session).clear_followup()
        return {"status": "cleared"}
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None


@router.post(
    "/api/analyze/stream",
    dependencies=[Depends(check_ask_rate_limit), Depends(check_upload_rate_limit)],
)
async def analyze_with_progress(
    topic: Annotated[str, Form(min_length=1, max_length=2000)],
    provider: Annotated[str, Form(max_length=40)] = "gemini",
    model_name: Annotated[str, Form(max_length=150)] = DEFAULT_MODEL,
    paper_ids: Annotated[str, Form(max_length=2000)] = "[]",
    files: list[UploadFile] = File(default=[]),
    session: ResearchSession = Depends(research_session),
):
    if not topic.strip():
        raise HTTPException(400, "Topic cannot be blank.")
    try:
        GapAnalyzerEngine._validate_model(provider, model_name, None)
        selected_ids = json.loads(paper_ids)
        if not isinstance(selected_ids, list) or any(
            not isinstance(value, str) for value in selected_ids
        ):
            raise ValueError("Invalid paper IDs")
        selected_ids = list(dict.fromkeys(selected_ids))
        if not 1 <= len(selected_ids) + len(files) <= 5:
            raise ValueError("Select between one and five papers")
    except (ValueError, TypeError):
        raise HTTPException(400, "Select one to five papers and a supported model.") from None
    if not session.lock.acquire(blocking=False):
        raise HTTPException(409, "Another ingestion is active in this session.")
    try:
        if any(value not in session.papers for value in selected_ids):
            raise HTTPException(
                400, "Search for these papers in this session before analyzing them."
            )
        papers = [dict(session.papers[value]) for value in selected_ids]
    finally:
        session.lock.release()
    uploads = []
    total_bytes = 0
    try:
        for file in files:
            name = file.filename or "document.pdf"
            if not name.lower().endswith(".pdf"):
                raise HTTPException(400, "Only PDF uploads are supported.")
            data = bytearray()
            while block := await file.read(65536):
                total_bytes += len(block)
                if total_bytes > get_settings().max_file_size:
                    raise HTTPException(413, "Combined PDFs exceed the upload limit.")
                data.extend(block)
            if not data.startswith(b"%PDF-"):
                raise HTTPException(400, "An uploaded file is not a PDF.")
            uploads.append((name, bytes(data)))
    finally:
        for file in files:
            await file.close()
    sessions.activate(session)
    return StreamingResponse(
        _analysis_events(session, papers, uploads, topic.strip(), provider, model_name),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


async def _analysis_events(session, papers, uploads, topic, provider, model_name):
    started = time.monotonic()
    queue: asyncio.Queue = asyncio.Queue(maxsize=64)
    cancelled = threading.Event()
    loop = asyncio.get_running_loop()

    def emit(progress):
        if cancelled.is_set():
            return

        def deliver():
            if not cancelled.is_set() and not queue.full():
                queue.put_nowait(("progress", progress))

        loop.call_soon_threadsafe(deliver)

    async def produce():
        try:
            emit(
                {
                    "stage": "prepare",
                    "percent": 3,
                    "message": "Request validated; preparing source documents",
                }
            )
            engine = await run_bounded_worker(
                prepare_analysis, session, papers, uploads, emit, cancelled
            )
            report = ""
            final = {}
            async for progress in engine.stream_gap_report(topic, provider, model_name):
                if "report" in progress:
                    report = progress["report"]
                    final = progress
                await queue.put(
                    ("progress", {key: value for key, value in progress.items() if key != "report"})
                )
            if not report.strip():
                raise RuntimeError("Analysis finished without a report")
            await queue.put(
                (
                    "done",
                    {
                        **final,
                        "stage": "complete",
                        "percent": 100,
                        "message": "Report complete"
                        if not final.get("limited")
                        else "Report complete with limited evidence",
                        "report": report,
                        "elapsed_seconds": round(time.monotonic() - started, 1),
                    },
                )
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Streamed research analysis failed")
            await queue.put(
                (
                    "error",
                    {
                        "message": "Analysis could not be completed. Please retry or check your selected sources."
                    },
                )
            )

    task = asyncio.create_task(produce())
    try:
        while True:
            try:
                event, payload = await asyncio.wait_for(queue.get(), timeout=10)
            except TimeoutError:
                event, payload = (
                    "heartbeat",
                    {"elapsed_seconds": round(time.monotonic() - started, 1)},
                )
            payload = {**payload, "elapsed_seconds": round(time.monotonic() - started, 1)}
            yield f"event: {event}\ndata: {json.dumps(payload)}\n\n"
            if event in {"done", "error"}:
                break
    finally:
        cancelled.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
