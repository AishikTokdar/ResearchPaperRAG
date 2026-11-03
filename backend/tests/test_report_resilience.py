"""Offline regressions for refusals, incomplete reports and lost PDF evidence."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document
from langchain_core.messages import AIMessageChunk

from app.agents.analyzer import AnalyzerAgent
from app.config import AI_PROVIDERS, DEFAULT_MODEL
from app.services.evidence import OMITTED_PASSAGE, format_evidence, ground_answer
from app.services.gap_analyzer_engine import REPORT_SECTIONS, GapAnalyzerEngine
from app.services.llm_service import LLMService


class GroundingTests(unittest.TestCase):
    def setUp(self):
        self.docs = [Document(page_content="Accuracy was 91.0 % on 1,000 samples at 0.001 seconds.",
                              metadata={"year": "2025", "paper_id": "internal-99", "source": "https://example.org/98"}),
                     Document(page_content="The baseline accuracy was 80%.")]
        self.citations = format_evidence(self.docs)[1]

    def check(self, answer, **options):
        return ground_answer(answer, self.citations, self.docs, **options)

    def test_equivalent_notation_and_list_ordinals_pass(self):
        self.assertNotIn("cannot", self.check("1. Accuracy was 91% on 1000 samples at 1e-3 seconds [E1]."))

    def test_compound_citations_keep_all_references(self):
        for refs in ("[E1, E2]", "[E1; E2]", "【E1; E2】", "[e1; e2]"):
            self.assertNotIn("cannot", self.check(f"Accuracy was 91% versus 80% {refs}."))
        self.assertIn("not supplied", self.check("Result [E1; E999]."))

    def test_numbers_cannot_come_from_another_source_or_internal_metadata(self):
        for claim in ("Accuracy was 80%", "There were 99 participants", "There were 98 participants", "Published in 2030"):
            self.assertIn("numerical claim", self.check(f"{claim} [E1].", allow_background=True))
        self.assertNotIn("cannot", self.check("Published in 2025 [E1]."))

    def test_leading_statistics_and_fractional_values_are_checked(self):
        for claim in ("99% accuracy was measured", "Accuracy was .99", "Accuracy was 91"):
            self.assertIn("numerical claim", self.check(f"{claim} [E1]."))

    def test_bad_passage_does_not_erase_valid_sections(self):
        text = "## 1. Literature Summary\nAccuracy was 91% [E1].\n\n## 2. Trend Detection\nAccuracy was 99% [E1].\n\n## 3. Common Methods\nBaseline [E2]."
        result = self.check(text, preserve_valid_blocks=True)
        self.assertIn("91%", result)
        self.assertIn("## 2. Trend Detection", result)
        self.assertIn("Baseline", result)
        self.assertIn(OMITTED_PASSAGE, result)
        self.assertNotIn("99%", result)

    def test_hybrid_background_cannot_excuse_uncited_source_claims(self):
        for heading in ("Literature Summary", "Research Gaps", "Limitations"):
            text = f"## {heading}\n" + "Unsupported source finding. " * 40
            self.assertIn("did not cite", self.check(text, allow_background=True))
        self.assertIn("Explanation", self.check("## Background knowledge\nExplanation.", allow_background=True))

    def test_paper_numbers_are_not_passage_ids(self):
        self.assertIn("not supplied", self.check("Accuracy was 91% [Paper 1]."))

    def test_hypothesis_table_is_explicitly_scoped(self):
        table = "| Proposed Title | Core Idea | Expected Outcome (hypothesis) |\n| --- | --- | --- |\n| Proposed research | Test robustness | May improve generalization |"
        self.assertNotIn("cannot", self.check(f"## 8. Novel Paper Suggestions\n{table}", allow_proposals=True))
        self.assertIn("did not cite", self.check(f"## 3. Common Methods\n{table}", allow_proposals=True))

    def test_rejected_table_row_does_not_break_table_layout(self):
        table = "| Method | Accuracy |\n| --- | --- |\n| Test [E1] | 91% |\n| Bad [E1] | 99% |\n| Baseline [E2] | 80% |"
        result = self.check(table, preserve_valid_blocks=True)
        self.assertIn("| Method | Accuracy |\n| --- | --- |\n| Test", result)
        self.assertNotIn("99%", result)
        self.assertTrue(all(line.startswith("|") for line in result.splitlines()))

    def test_hostile_exponents_are_bounded_and_url_digits_are_not_results(self):
        self.assertIn("numerical claim", self.check("Accuracy was 1e999999999% [E1]."))
        docs = [Document(page_content="See https://example.org/123456 for this study.")]
        self.assertIn("numerical claim", ground_answer("There were 123456 participants [E1].", format_evidence(docs)[1], docs))


class ReportTests(unittest.TestCase):
    def engine(self, scope="full_text"):
        engine = GapAnalyzerEngine()
        engine.vector_store = object()
        engine._report_documents = MagicMock(return_value=[Document(page_content="Accuracy was 91%.", metadata={"evidence_scope": scope})])
        return engine

    def collect(self, engine):
        async def run():
            return [event async for event in engine.stream_gap_report("EEG", "gemini", DEFAULT_MODEL)]
        return asyncio.run(run())[-1]

    def report(self, bad_section=None):
        return "\n\n".join(f"## {i}. {title}\nAccuracy was {99 if i == bad_section else 91}% [E1]." for i, title in enumerate(REPORT_SECTIONS, 1))

    def mock_stream(self, engine, report, warnings=None):
        async def stream(*args):
            yield {"type": "complete", "answer": report, "warnings": warnings or []}
        engine.llm.stream_text = stream

    def test_partial_report_keeps_valid_sections_and_is_never_cached(self):
        engine = self.engine()
        self.mock_stream(engine, self.report(2))
        first, second = self.collect(engine), self.collect(engine)
        self.assertEqual(first["report"], second["report"])
        self.assertIn("General guidance (not findings", first["report"])
        self.assertTrue(first["limited"])
        self.assertNotIn(2, first["sections_completed"])
        self.assertIn(8, first["sections_completed"])
        self.assertFalse(engine._cache)

    def test_empty_last_heading_does_not_qualify_for_cache_or_completion(self):
        engine = self.engine()
        report = self.report().split("## 8.")[0] + "## 8. Novel Paper Suggestions\n"
        self.mock_stream(engine, report)
        event = self.collect(engine)
        self.assertTrue(event["limited"])
        self.assertNotIn(8, event["sections_completed"])
        self.assertFalse(engine._cache)

    def test_abstract_coverage_is_limited_on_fresh_and_cached_reports(self):
        engine = self.engine("abstract_only")
        self.mock_stream(engine, self.report())
        for _ in range(2):
            event = self.collect(engine)
            self.assertTrue(event["limited"])
            self.assertIn("abstracts only", event["report"])
        self.assertTrue(engine._cache)

    def test_bad_interrupted_last_section_does_not_uncomplete_earlier_section(self):
        engine = self.engine()
        self.mock_stream(engine, self.report(8), ["Generation was interrupted"])
        event = self.collect(engine)
        self.assertIn(7, event["sections_completed"])
        self.assertNotIn(8, event["sections_completed"])

    def test_successful_fallback_does_not_mark_a_complete_report_as_incomplete(self):
        engine = self.engine()
        self.mock_stream(engine, self.report(), ["A fallback model was used."])
        event = self.collect(engine)
        self.assertEqual(event["sections_completed"], list(range(1, 9)))
        self.assertFalse(event["limited"])
        self.assertIn("A fallback model was used.", event["report"])

    def test_streaming_fallback_is_disclosed_in_the_final_response(self):
        service = LLMService()
        class BrokenLLM:
            async def astream(self, *args, **kwargs):
                raise RuntimeError("temporary provider failure")
                yield  # Make this an async iterator, matching provider streaming.
        class WorkingLLM:
            async def astream(self, *args, **kwargs):
                yield AIMessageChunk(content="Supported answer [E1].")
        async def run():
            attempts = [(AI_PROVIDERS["gemini"], "fixture", "key", 2.0, "sig", i) for i in (1, 2)]
            with patch.object(service, "_attempts", return_value=iter(attempts)), patch.object(service, "_build_llm_with_key", side_effect=[BrokenLLM(), WorkingLLM()]), patch.object(service, "_failure"):
                return [event async for event in service.stream_text([], DEFAULT_MODEL, "gap_report_stream", 100)]
        events = asyncio.run(run())
        self.assertEqual(events[-1]["type"], "complete")
        self.assertIn("A fallback model was used.", events[-1]["warnings"])

    def test_attached_citations_are_separated_from_bold_and_plain_text(self):
        from app.services.evidence import resolve_citations
        for answer in ("ORCHID-RIVER[E1].", "**ORCHID-RIVER**[E1].", "`ORCHID-RIVER`[E1]."):
            with self.subTest(answer=answer):
                resolved = resolve_citations(answer, {"E1": "[qa-fixture.pdf - Page 1]"})
                self.assertIn(" [qa-fixture.pdf - Page 1]", resolved)

    def test_synchronous_report_uses_same_grounding_policy(self):
        engine = self.engine()
        engine.llm.generate_text = MagicMock(return_value=(self.report(2), "fixture", []))
        report = engine.generate_gap_report("EEG", "gemini", DEFAULT_MODEL)
        self.assertIn("91%", report)
        self.assertIn("General guidance (not findings", report)
        self.assertFalse(engine._cache)

    def test_interrupted_provider_retains_report_without_calling_fallback(self):
        engine = self.engine()
        draft = "## 1. Literature Summary\nAccuracy was 91% [E1].\n\n## 2. Trend Detection\nUnfinished"
        class BrokenLLM:
            async def astream(self, *args, **kwargs):
                yield AIMessageChunk(content=draft)
                raise RuntimeError("private network diagnostics")
        attempts = [(AI_PROVIDERS["gemini"], "fixture", "key", 2.0, "signature", i) for i in (1, 2)]
        with patch.object(engine.llm, "_attempts", return_value=iter(attempts)), patch.object(engine.llm, "_build_llm_with_key", return_value=BrokenLLM()) as build, patch.object(engine.llm, "_failure"):
            event = self.collect(engine)
        self.assertTrue(event["limited"])
        self.assertIn(1, event["sections_completed"])
        self.assertIn("91%", event["report"])
        self.assertIn("interrupted", event["report"])
        self.assertNotIn("private network", event["report"])
        self.assertEqual(build.call_count, 1)
        self.assertFalse(engine._cache)

    def test_short_pdf_results_survive_analysis(self):
        short = Document(page_content="Accuracy: 91%.", metadata={"page": 4})
        long = Document(page_content="Methods and introductory material. " * 10)
        self.assertIn(short, AnalyzerAgent().process([short, long], {}))

    def test_whitespace_only_stream_retries_without_false_completion(self):
        service = LLMService()
        class EmptyLLM:
            async def astream(self, *args, **kwargs):
                yield AIMessageChunk(content="   ")
        async def run():
            attempt = (AI_PROVIDERS["gemini"], "fixture", "key", 2.0, "sig", 1)
            with patch.object(service, "_attempts", return_value=iter([attempt])), patch.object(service, "_build_llm_with_key", return_value=EmptyLLM()), patch.object(service, "_failure"):
                return [event async for event in service.stream_text([], DEFAULT_MODEL, "gap_report_stream", 100)]
        # Whitespace is not a usable partial draft.
        with self.assertRaises(RuntimeError):
            asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
