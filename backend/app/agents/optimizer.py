from typing import Any

from langchain_core.documents import Document

from ..config import get_settings
from ..services.evidence import fit_evidence, rank_evidence
from .base_agent import BaseAgent


class OptimizerAgent(BaseAgent):
    def __init__(self, context_token_budget: int | None = None):
        super().__init__(
            name="optimizer", description="Reorders and trims context for optimal LLM prompting"
        )
        self.context_token_budget = context_token_budget or get_settings().context_token_budget

    def process(
        self,
        input_data: tuple[str, list[Document]],
        context: dict[str, Any],
    ) -> tuple[str, list[Document]]:
        question, chunks = input_data

        ranked = rank_evidence(question, chunks)
        fitted = fit_evidence(ranked, self.context_token_budget)[
            : context.get("retrieval_k", get_settings().retrieval_k)
        ]

        context["optimizer_input_chunks"] = len(chunks)
        context["optimizer_output_chunks"] = len(fitted)
        context["optimizer_token_budget"] = self.context_token_budget
        context["optimized_chunks"] = fitted

        return (question, fitted)
