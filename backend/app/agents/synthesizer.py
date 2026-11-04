"""
Synthesizer Agent

Generates the final answer using the LLM based on
the filtered context and question.
"""

from typing import Any

from langchain_core.documents import Document

from ..services.llm_service import LLMService
from .base_agent import BaseAgent


class SynthesizerAgent(BaseAgent):
    def __init__(self, llm_service: LLMService):
        super().__init__(name="synthesizer", description="Generates answers using LLM")
        self.llm_service = llm_service

    def process(self, input_data: tuple[str, list[Document]], context: dict[str, Any]) -> str:
        question, chunks = input_data
        model = context.get("model")

        answer, model_used, processing_time, warnings = self.llm_service.generate_answer(
            question=question,
            context_docs=chunks,
            model=model,
            hybrid_mode=context.get("hybrid_mode", False),
        )

        context["warnings"] = warnings
        context["model_used"] = model_used
        context["llm_processing_time"] = processing_time
        context["answer_length"] = len(answer)

        return answer
