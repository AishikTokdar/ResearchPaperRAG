"""Regressions for report-wide refusals and permissive citation/number checks."""

import asyncio
import unittest
from unittest.mock import MagicMock

from langchain_core.documents import Document

from app.config import DEFAULT_MODEL
from app.services.evidence import OMITTED_PASSAGE, format_evidence, ground_answer
from app.services.gap_analyzer_engine import REPORT_SECTIONS, GapAnalyzerEngine


class EvidenceValidationTests(unittest.TestCase):
    def setUp(self):
        self.docs = [
            Document(
                page_content="Accuracy was 91.0 % over 1,000 samples at 0.001 seconds.",
                metadata={
                    "paper_title": "EEG evaluation",
                    "year": "2025",
                    "paper_id": "internal-99",
                    "source": "https://example.org/98",
                },
            ),
            Document(page_content="The baseline accuracy was 80%."),
        ]
        self.citations = format_evidence(self.docs)[1]

    def check(self, answer, **kwargs):
        return ground_answer(answer, self.citations, self.docs, **kwargs)

    def test_equivalent_numeric_formats_and_list_ordinals_are_supported(self):
        answer = "1. Accuracy was 91% over 1000 samples at 1e-3 seconds [E1]."
        self.assertIn("91%", self.check(answer))
        self.assertNotIn("cannot", self.check(answer))

    def test_compound_citations_keep_every_evidence_id(self):
        for refs in ("[E1, E2]", "[E1; E2]", "【E1; E2】", "[e1; e2]"):
            with self.subTest(refs=refs):
                self.assertNotIn("cannot", self.check(f"Accuracy was 91% versus 80% {refs}."))
        self.assertIn("not supplied", self.check("Accuracy was 91% [E1; E999]."))

    def test_numbers_require_the_cited_passage_even_in_hybrid_mode(self):
        for answer in (
            "Accuracy was 80% [E1].",
            "Accuracy was 99% [E1].",
            "There were 3 participants [E1].",
            "Published in 2030 [E1].",
            "There were 99 participants [E1].",
            "There were 98 participants [E1].",
        ):
            with self.subTest(answer=answer):
                self.assertIn("numerical claim", self.check(answer, allow_background=True))
        self.assertNotIn("cannot", self.check("Published in 2025 [E1]."))

    def test_leading_statistic_and_percent_units_are_not_discarded(self):
        self.assertIn("numerical claim", self.check("99% accuracy was measured [E1]."))
        self.assertIn("numerical claim", self.check("Accuracy was 91 [E1]."))

    def test_report_retains_good_passages_and_headings_without_invalid_claim(self):
        answer = "## 1. Literature Summary\nAccuracy was 91% [E1].\n\n## 2. Trend Detection\nAccuracy was 99% [E1].\n\n## 3. Common Methods\nSupported methods [E2]."
        result = self.check(answer, preserve_valid_blocks=True)
        self.assertIn("91%", result)
        self.assertIn("## 2. Trend Detection", result)
        self.assertIn("## 3. Common Methods", result)
        self.assertIn("Supported methods", result)
        self.assertIn(OMITTED_PASSAGE, result)
        self.assertNotIn("99%", result)
        self.assertNotIn("I cannot verify", result)

    def test_paper_numbers_are_not_guessed_as_passage_ids(self):
        result = self.check("Accuracy was 91% [Paper 1].", preserve_valid_blocks=True)
        self.assertIn(OMITTED_PASSAGE, result)
        self.assertNotIn("91%", result)

    def test_uncited_text_does_not_bypass_grounding_by_length_or_section_name(self):
        for heading in ("Literature Summary", "Limitations", "Research Gaps"):
            answer = f"## {heading}\n" + "An unsupported finding is claimed here. " * 8
            self.assertIn("did not cite", self.check(answer, allow_background=True))
        self.assertIn(
            "General explanation",
            self.check("## Background knowledge\nGeneral explanation.", allow_background=True),
        )

    def test_hypothesis_table_is_allowed_only_in_report_proposal_section(self):
        table = "| Proposed Title | Core Idea | Expected Outcome (hypothesis) |\n| --- | --- | --- |\n| Proposed project | Evaluate robustness | May improve generalization |"
        report = f"## 8. Novel Paper Suggestions\n\n{table}"
        self.assertNotIn("cannot", self.check(report, allow_proposals=True))
        self.assertIn("did not cite", self.check(report))
        self.assertIn(
            "did not cite",
            self.check(
                report.replace("Novel Paper Suggestions", "Common Methods"), allow_proposals=True
            ),
        )

    def test_tables_keep_markdown_rows_when_one_row_is_omitted(self):
        table = "| Method | Accuracy |\n| --- | --- |\n| Supported [E1] | 91% |\n| Unsupported [E1] | 99% |\n| Baseline [E2] | 80% |"
        result = self.check(table, preserve_valid_blocks=True)
        self.assertIn("| Method | Accuracy |\n| --- | --- |\n| Supported", result)
        self.assertNotIn("99%", result)
        self.assertIn(OMITTED_PASSAGE, result)
        self.assertTrue(all(line.startswith("|") for line in result.splitlines()))
        self.assertIn("| Baseline", result)

    def test_hostile_exponent_is_bounded_and_url_digits_are_not_metrics(self):
        self.assertIn("numerical claim", self.check("Accuracy was 1e999999999% [E1]."))
        docs = [Document(page_content="See https://example.org/123456 for the study.")]
        result = ground_answer(
            "There were 123456 participants [E1].", format_evidence(docs)[1], docs
        )
        self.assertIn("numerical claim", result)


class ReportIntegrationTests(unittest.TestCase):
    def test_stream_and_sync_keep_valid_sections_mark_partial_and_do_not_cache(self):
        engine = GapAnalyzerEngine()
        docs = [Document(page_content="Accuracy was 91%.", metadata={"source_file": "paper.pdf"})]
        engine.vector_store = object()
        engine._report_documents = MagicMock(return_value=docs)
        report = "\n\n".join(
            f"## {i}. {title}\nAccuracy was {99 if i == 2 else 91}% [E1]."
            for i, title in enumerate(REPORT_SECTIONS, 1)
        )
        engine.llm.generate_text = MagicMock(return_value=(report, "fixture", []))
        sync_result = engine.generate_gap_report("EEG", "gemini", DEFAULT_MODEL)
        calls = []

        async def stream(*args):
            calls.append(args)
            yield {"type": "complete", "answer": report, "warnings": []}

        engine.llm.stream_text = stream

        async def collect():
            return [
                event async for event in engine.stream_gap_report("EEG", "gemini", DEFAULT_MODEL)
            ]

        first, second = asyncio.run(collect())[-1], asyncio.run(collect())[-1]
        self.assertEqual(first["report"], sync_result)
        self.assertEqual(first["report"], second["report"])
        self.assertTrue(first["limited"])
        self.assertNotIn(2, first["sections_completed"])
        self.assertIn(8, first["sections_completed"])
        # Invalid model completion must be disclosed, not disguised as canned analysis.
        self.assertIn("> Partial report:", first["report"])
        self.assertIn("Trend Detection", first["report"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(engine._cache), 0)

    def test_followup_does_not_enable_background_bypass(self):
        engine = GapAnalyzerEngine()
        engine.llm.generate_text = MagicMock(
            return_value=(
                "## Background knowledge\n" + "Unsupported assertion. " * 40,
                "fixture",
                [],
            )
        )
        result = engine._cached_generate(
            "system",
            "question",
            [Document(page_content="Evidence")],
            DEFAULT_MODEL,
            "paper_followup",
            800,
        )
        self.assertIn("did not cite", result)
        self.assertFalse(engine._cache)


if __name__ == "__main__":
    unittest.main()
