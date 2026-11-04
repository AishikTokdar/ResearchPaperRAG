"""
Preprocessor Agent

Cleans and formats retrieved document chunks before they are sent
to the Optimizer/Synthesizer.  Strips whitespace noise, normalizes
unicode, and collapses redundant newlines while preserving complete passages.
"""

import re
import unicodedata
from typing import Any

from langchain_core.documents import Document

from .base_agent import BaseAgent


class PreprocessorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="preprocessor", description="Cleans and normalizes document chunks")

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        text = unicodedata.normalize("NFC", text)
        replacements = {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "-",
            "\u2026": "...",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def process(self, input_data: list[Document], context: dict[str, Any]) -> list[Document]:
        cleaned: list[Document] = []
        chars_before = 0
        chars_after = 0

        for doc in input_data:
            raw = doc.page_content
            chars_before += len(raw)

            text = self._normalize_unicode(raw)
            text = self._normalize_whitespace(text)
            chars_after += len(text)

            cleaned.append(Document(page_content=text, metadata={**doc.metadata}))

        context["preprocessor_chars_before"] = chars_before
        context["preprocessor_chars_after"] = chars_after
        return cleaned
