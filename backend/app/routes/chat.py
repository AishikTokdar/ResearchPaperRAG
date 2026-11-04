"""
Chat Routes

Endpoints for asking questions and receiving AI answers (JSON and SSE streaming).
"""

import json
import logging
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from ..agents.base_agent import AgentResult
from ..agents.pipeline import AgentPipeline
from ..models import AnswerResponse, QuestionRequest
from ..services.ip_rate_limit import check_ask_rate_limit
from ..services.llm_service import LLMService
from ..services.usage_counters import increment_chat_completions
from ..services.vector_store import VectorStoreService
from .upload import get_vector_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["RAG Chat & Reasoning"])

_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def set_llm_service(llm_service: LLMService):
    global _llm_service
    _llm_service = llm_service


@router.post("/ask", response_model=AnswerResponse)
async def ask_question(
    request: QuestionRequest,
    _: None = Depends(check_ask_rate_limit),
    vector_service: VectorStoreService = Depends(get_vector_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    if not vector_service.is_ready:
        raise HTTPException(
            status_code=400,
            detail="No PDF has been loaded. Please upload a PDF first.",
        )

    try:
        pipeline = AgentPipeline(vector_service, llm_service)
        result = await run_in_threadpool(
            pipeline.run,
            question=request.question,
            model=request.model,
            include_sources=request.include_sources,
            hybrid_mode=request.hybrid_mode,
        )

        if not result.success:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate answer. Please try again shortly.",
            )

        increment_chat_completions()

        return AnswerResponse(
            answer=result.answer or "",
            model_used=result.model_used,
            processing_time=result.processing_time,
            sources=result.sources,
            warnings=result.context.get("warnings"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing question")
        raise HTTPException(
            status_code=500,
            detail="Unable to process the question. Please try again shortly.",
        ) from e


async def _stream_pipeline(
    question: str,
    model: str | None,
    include_sources: bool,
    hybrid_mode: bool,
    vector_service: VectorStoreService,
    llm_service: LLMService,
) -> AsyncGenerator[str, None]:
    start = time.time()

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    yield sse("status", {"stage": "starting", "message": "Pipeline started"})

    try:
        pipeline = AgentPipeline(vector_service, llm_service)

        context: dict = {
            "question": question,
            "model": model,
            "include_sources": include_sources,
            "hybrid_mode": hybrid_mode,
            "retrieval_k": pipeline.retrieval_k,
        }
        results: list[AgentResult] = []
        total_ms = 0.0

        ok, chunks, ms, err = await run_in_threadpool(
            pipeline._step, pipeline.extractor, question, context, results
        )
        total_ms += ms
        if not ok:
            yield sse("error", {"message": "The response could not be completed. Please retry."})
            return

        ok, filtered, ms, err = await run_in_threadpool(
            pipeline._step, pipeline.analyzer, chunks, context, results
        )
        total_ms += ms
        if not ok:
            yield sse("error", {"message": "The response could not be completed. Please retry."})
            return

        ok, cleaned, ms, err = await run_in_threadpool(
            pipeline._step, pipeline.preprocessor, filtered, context, results
        )
        total_ms += ms
        if not ok:
            yield sse("error", {"message": "The response could not be completed. Please retry."})
            return

        ok, optimised_pair, ms, err = await run_in_threadpool(
            pipeline._step, pipeline.optimizer, (question, cleaned), context, results
        )
        total_ms += ms
        if not ok:
            yield sse("error", {"message": "The response could not be completed. Please retry."})
            return

        stream_question, optimised_chunks = optimised_pair
        answer = ""
        model_used = None
        stream_warnings: list[str] = []
        async for event in llm_service.stream_answer_with_failover(
            question=stream_question,
            context_docs=optimised_chunks,
            model=model,
            hybrid_mode=hybrid_mode,
        ):
            if event.get("type") == "status":
                yield sse("status", event)
            elif event.get("type") == "warning":
                msg = event.get("message", "")
                if msg:
                    stream_warnings.append(msg)
                    yield sse("warning", {"message": msg})
            elif event.get("type") == "token":
                content = event.get("content", "")
                answer += content
                yield sse("token", {"content": content})
            elif event.get("type") == "complete":
                model_used = event.get("model_used")
                answer = event.get("answer", answer)
                if event.get("warnings"):
                    for w in event.get("warnings") or []:
                        if w not in stream_warnings:
                            stream_warnings.append(w)

        context["model_used"] = model_used
        context["answer_length"] = len(answer)

        ok, validated, ms, err = await run_in_threadpool(
            pipeline._step, pipeline.validator, answer, context, results
        )
        total_ms += ms
        if not ok:
            yield sse("error", {"message": "The response could not be completed. Please retry."})
            return

        ok, assembled, ms, err = await run_in_threadpool(
            pipeline._step, pipeline.assembler, validated, context, results
        )
        total_ms += ms
        if not ok:
            yield sse("error", {"message": "The response could not be completed. Please retry."})
            return

        increment_chat_completions()

        yield sse(
            "done",
            {
                "answer": assembled.get("answer", answer),
                "model_used": assembled.get("model_used") or context.get("model_used"),
                "processing_time": round(total_ms / 1000, 3)
                if total_ms > 0
                else round(time.time() - start, 3),
                "sources": assembled.get("sources"),
                "warnings": stream_warnings if stream_warnings else None,
            },
        )

    except Exception:
        logger.exception("Streaming pipeline error")
        yield sse("error", {"message": "The response could not be completed. Please retry."})


@router.post("/ask/stream")
async def ask_question_stream(
    request: QuestionRequest,
    _: None = Depends(check_ask_rate_limit),
    vector_service: VectorStoreService = Depends(get_vector_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    if not vector_service.is_ready:
        raise HTTPException(
            status_code=400,
            detail="No PDF has been loaded. Please upload a PDF first.",
        )

    return StreamingResponse(
        _stream_pipeline(
            question=request.question,
            model=request.model,
            include_sources=request.include_sources,
            hybrid_mode=request.hybrid_mode,
            vector_service=vector_service,
            llm_service=llm_service,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
