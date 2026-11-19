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

_MULTI_NEWLINE = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[ \t]+")
_UNICODE_MAP = str.maketrans({
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2026": "...",
})


class PreprocessorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="preprocessor", description="Cleans and normalizes document chunks")

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        if "\r" in text:
            text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = _MULTI_NEWLINE.sub("\n\n", text)
        text = _MULTI_SPACE.sub(" ", text)
        return text.strip()

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        return unicodedata.normalize("NFC", text).translate(_UNICODE_MAP)

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
