"""
Validator Agent

Validates the generated answer for quality and relevance.
Can flag low-confidence or potentially incorrect responses.
"""

from typing import Any

from .base_agent import BaseAgent

_FAILURE_INDICATORS = (
    "i cannot find",
    "i don't have information",
    "not mentioned in the document",
    "no information available",
)


class ValidatorAgent(BaseAgent):
    def __init__(self, min_answer_length: int = 10, max_answer_length: int = 5000):
        super().__init__(name="validator", description="Validates generated answers for quality")
        self.min_answer_length = min_answer_length
        self.max_answer_length = max_answer_length

    def process(self, input_data: str, context: dict[str, Any]) -> str:
        answer = input_data

        validation_issues = []

        if len(answer) < self.min_answer_length:
            validation_issues.append("answer_too_short")

        if len(answer) > self.max_answer_length:
            validation_issues.append("answer_long")

        answer_lower = answer.casefold()
        is_uncertain = any(indicator in answer_lower for indicator in _FAILURE_INDICATORS)

        context["validation_passed"] = len(validation_issues) == 0
        context["validation_issues"] = validation_issues
        context["is_uncertain_answer"] = is_uncertain

        return answer
