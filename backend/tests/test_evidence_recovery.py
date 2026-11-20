"""Recovery must find source text, not merely a matching number or topic."""

import asyncio
import unittest
from unittest.mock import MagicMock

from langchain_core.documents import Document

from app.config import DEFAULT_MODEL
from app.services.evidence import OMITTED_PASSAGE, format_evidence, ground_answer, recover_report_evidence
from app.services.gap_analyzer_engine import REPORT_SECTIONS, GapAnalyzerEngine


def passage(text, paper="a", page=0, scope="full_text"):
    return Document(page_content=text, metadata={"paper_id": paper, "paper_title": f"Study {paper}",
                    "source": f"https://example.org/{paper}", "page": page, "evidence_scope": scope})


class EvidenceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.overview = passage("This study evaluates educational retrieval.")
        self.result = passage("The measured accuracy was 91%. The experiment evaluated educational retrieval.", page=4)

    def validate(self, answer, selected=None, candidates=None, **kwargs):
        fixed, docs = recover_report_evidence(answer, selected or [self.overview],
                                               candidates if candidates is not None else [self.result], **kwargs)
        checked = ground_answer(fixed, format_evidence(docs)[1], docs, preserve_valid_blocks=True)
        return fixed, docs, checked

    def test_claim_recovers_same_paper_passage_with_correct_page(self):
        raw = "## 1. Literature Summary\nThe measured accuracy was 91% [E1]."
        fixed, docs, checked = self.validate(raw)
        self.assertIn("[E2]", fixed)
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[1].page_content, "The measured accuracy was 91%.")
        self.assertIn("Study a - Page 5", checked)
        self.assertIn("91%", checked)
        self.assertNotIn(OMITTED_PASSAGE, checked)
        # Existing evidence IDs are never reordered.
        self.assertIs(docs[0], self.overview)
        self.assertEqual(recover_report_evidence(fixed, docs, [self.result]), (fixed, docs))

    def test_unique_exact_uncited_source_statement_can_recover(self):
        fixed, _, checked = self.validate("The measured accuracy was 91%.")
        self.assertIn("[E2]", fixed)
        self.assertNotIn(OMITTED_PASSAGE, checked)

    def test_missing_citation_requires_unique_paper(self):
        other = passage(self.result.page_content, paper="b")
        raw = "The measured accuracy was 91%."
        fixed, docs, checked = self.validate(raw, selected=[self.overview, passage("Other study overview.", "b")],
                                              candidates=[self.result, other])
        self.assertEqual(raw, fixed)
        self.assertEqual(len(docs), 2)
        self.assertIn(OMITTED_PASSAGE, checked)

    def test_wrong_paper_citation_cannot_borrow_another_papers_result(self):
        other = passage(self.result.page_content, paper="b")
        raw = "The measured accuracy was 91% [E1]."
        fixed, _, checked = self.validate(raw, selected=[self.overview, passage("Other overview.", "b")],
                                          candidates=[other])
        self.assertEqual(fixed, raw)
        self.assertIn(OMITTED_PASSAGE, checked)

    def test_paper_title_attribution_cannot_borrow_another_papers_result(self):
        selected = [self.overview, passage("Other study overview.", "b")]
        for label in ("Study a", "An invented paper title"):
            with self.subTest(label=label):
                raw = f"**{label}** – The measured accuracy was 91%."
                fixed, docs, _ = self.validate(raw, selected=selected,
                                               candidates=[passage(self.result.page_content, "b")])
                self.assertEqual(fixed, raw)
                self.assertEqual(len(docs), 2)
        raw = "**Study a** – The measured accuracy was 91%."
        _, _, checked = self.validate(raw)
        self.assertIn("91%", checked)
        self.assertNotIn(OMITTED_PASSAGE, checked)

    def test_matching_number_is_not_evidence_for_another_metric_or_negation(self):
        for text in ("The measured accuracy was not 91%.", "The measured recall was 91%.",
                     "The measured accuracy was 99%.", "The measured accuracy was 91% on an external dataset."):
            with self.subTest(text=text):
                fixed, docs, _ = self.validate(text + " [E1].")
                self.assertEqual(len(docs), 1)
                self.assertNotIn("[E2]", fixed)

    def test_metadata_unselected_sources_and_invalid_ids_are_not_recovery_evidence(self):
        for candidate in (passage(self.result.page_content, paper="unselected"),
                          passage(self.result.page_content, scope="metadata_only")):
            with self.subTest(candidate=candidate.metadata):
                _, docs, checked = self.validate("The measured accuracy was 91% [E1].", candidates=[candidate])
                self.assertEqual(len(docs), 1)
                self.assertIn(OMITTED_PASSAGE, checked)
        fixed, docs, _ = self.validate("The measured accuracy was 91% [E999].")
        self.assertIn("[E999]", fixed)
        self.assertEqual(len(docs), 1)

    def test_recovery_budget_is_bounded_and_existing_text_is_unchanged_without_match(self):
        raw = "## 1. Literature Summary\nThe measured accuracy was 91% [E1]."
        fixed, docs, checked = self.validate(raw, max_recovery_tokens=1)
        self.assertEqual(fixed, raw)
        self.assertEqual(len(docs), 1)
        self.assertIn(OMITTED_PASSAGE, checked)
        already_supported = "## 1. Literature Summary\n\nEducational retrieval is evaluated [E1]."
        fixed, docs, _ = self.validate(already_supported)
        self.assertEqual(fixed, already_supported)
        self.assertEqual(len(docs), 1)

    def test_table_rows_are_not_rewritten_by_sentence_recovery(self):
        raw = "| Measure | Value |\n| --- | --- |\n| Accuracy [E1] | 91% |"
        fixed, docs, _ = self.validate(raw)
        self.assertEqual(fixed, raw)
        self.assertEqual(len(docs), 1)

    def test_batch_uses_indexed_passages_before_recording_rejection(self):
        feedback = []
        raw = "## 1. Literature Summary\nThe measured accuracy was 91% [E1]."
        checked = GapAnalyzerEngine._validated_batch(raw, [self.overview], (1,), feedback, [self.result])
        self.assertIn("91%", checked)
        self.assertIn("Page 5", checked)
        self.assertFalse(feedback)

    def test_sync_and_stream_recover_indexed_evidence_without_a_repair_call(self):
        report = "\n\n".join(f"## {n}. {title}\nThe measured accuracy was 91% [E1]."
                              for n, title in enumerate(REPORT_SECTIONS, 1))
        for streaming in (False, True):
            with self.subTest(streaming=streaming):
                engine = GapAnalyzerEngine()
                engine.vector_store = object()
                engine.documents = [self.overview, self.result]
                engine._report_documents = MagicMock(return_value=[self.overview])
                engine.llm.generate_text = MagicMock(return_value=(report, DEFAULT_MODEL, []))
                if streaming:
                    async def stream(*args):
                        yield {"type": "complete", "answer": report, "model_used": DEFAULT_MODEL, "warnings": []}
                    engine.llm.stream_text = stream

                    async def collect():
                        return [event async for event in engine.stream_gap_report("Any topic", "gemini", DEFAULT_MODEL)]
                    result = asyncio.run(collect())[-1]["report"]
                    engine.llm.generate_text.assert_not_called()
                else:
                    result = engine.generate_gap_report("Any topic", "gemini", DEFAULT_MODEL)
                    engine.llm.generate_text.assert_called_once()
                self.assertIn("91%", result)
                self.assertIn("p. 5", result)
                self.assertNotIn("Partial report:", result)
                self.assertNotIn(OMITTED_PASSAGE, result)


if __name__ == "__main__":
    unittest.main()
