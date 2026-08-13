import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from ..services.paper_fetcher import PaperFetcher
from ..services.gap_analyzer_engine import GapAnalyzerEngine

router = APIRouter(tags=["Research Gap Analyzer"])

fetcher = PaperFetcher()
analyzer_engine = GapAnalyzerEngine()


def _process_ingest_sync(fetched_papers: List[Dict[str, Any]]) -> tuple[int, int]:
    selected_papers = fetched_papers[:5]
    fetched_with_text = []
    for paper in selected_papers:
        full_text = fetcher.download_and_extract_text(paper)
        fetched_with_text.append((paper, full_text))

    num_chunks = analyzer_engine.process_and_index_papers(fetched_papers_with_text=fetched_with_text)
    return len(selected_papers), num_chunks


class PaperSearchRequest(BaseModel):
    query: str
    limit_per_source: Optional[int] = 3


class IngestPapersRequest(BaseModel):
    fetched_papers: List[Dict[str, Any]]


class AnalyzeGapsRequest(BaseModel):
    topic: str
    provider: Optional[str] = "gemini"
    model_name: Optional[str] = "gemini-3.6-flash"
    api_key: Optional[str] = None


class ChatFollowupRequest(BaseModel):
    question: str
    provider: Optional[str] = "gemini"
    model_name: Optional[str] = "gemini-3.6-flash"
    api_key: Optional[str] = None


@router.post("/api/papers/search")
async def search_papers(req: PaperSearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        papers = await asyncio.to_thread(
            fetcher.search_all, query=req.query, limit_per_source=req.limit_per_source or 3
        )
        return {"query": req.query, "total_found": len(papers), "papers": papers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch papers: {str(e)}")


@router.post("/api/papers/ingest")
async def ingest_papers(
    req: IngestPapersRequest
):
    try:
        count, num_chunks = await asyncio.to_thread(_process_ingest_sync, req.fetched_papers)
        return {
            "status": "success",
            "indexed_papers_count": count,
            "chunks_created": num_chunks,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest papers: {str(e)}")


@router.post("/api/analyze/gaps")
async def analyze_research_gaps(req: AnalyzeGapsRequest):
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")
    try:
        report = await asyncio.to_thread(
            analyzer_engine.generate_gap_report,
            topic=req.topic,
            provider=req.provider or "gemini",
            model_name=req.model_name or "gemini-3.6-flash",
            api_key=req.api_key,
        )
        return {"topic": req.topic, "report": report}
    except Exception as e:
        fallback_msg = (
            "> [SERVICE TEMPORARILY BUSY] The system encountered a temporary error while synthesizing the report. "
            "Please try again in a few moments or verify your backend API key settings."
        )
        return {"topic": req.topic, "report": fallback_msg}


@router.post("/api/chat/followup")
async def chat_followup(req: ChatFollowupRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        answer = await asyncio.to_thread(
            analyzer_engine.ask_followup,
            question=req.question,
            provider=req.provider or "gemini",
            model_name=req.model_name or "gemini-3.6-flash",
            api_key=req.api_key,
        )
        return {"question": req.question, "answer": answer}
    except Exception as e:
        fallback_msg = (
            "> [SERVICE TEMPORARILY BUSY] The system encountered a temporary error processing your question. "
            "Please try asking your question again in a few moments."
        )
        return {"question": req.question, "answer": fallback_msg}

