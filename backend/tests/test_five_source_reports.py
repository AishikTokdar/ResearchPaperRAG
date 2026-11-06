"""Five selections must remain visible after budgeting, validation and rendering."""

import asyncio
import unittest
from unittest.mock import MagicMock

from langchain_core.documents import Document

from app.config import DEFAULT_MODEL
from app.services.evidence import OMITTED_PASSAGE, format_evidence, ground_answer, token_count
from app.services.gap_analyzer_engine import GapAnalyzerEngine, REPORT_SECTIONS
from app.services.report_presentation import (
    GUIDANCE,
    compact_report_citations,
    complete_report_sections,
    ensure_source_summaries,
    parse_model_guidance,
    sections_needing_guidance,
)


def sources():
    return [Document(page_content=f"Study {i} evaluates educational chatbot retrieval. Its source-specific objective is curriculum coverage.",
                     metadata={"paper_id": f"paper-{i}", "paper_title": f"Educational chatbot study {i}",
                               "source": f"https://example.org/paper-{i}",
                               "evidence_scope": "metadata_only" if i == 5 else "abstract_only"})
            for i in range(1, 6)]


class FiveSourceReportTests(unittest.TestCase):
    def test_no_source_content_cannot_be_reported_as_a_completed_placeholder(self):
        engine = GapAnalyzerEngine()
        engine.vector_store = object()
        engine._report_documents = MagicMock(return_value=[])
        with self.assertRaises(ValueError):
            engine.generate_gap_report("education")

        async def collect():
            return [event async for event in engine.stream_gap_report("education", "gemini", DEFAULT_MODEL)]
        with self.assertRaises(ValueError):
            asyncio.run(collect())

    def test_depth_allocation_increases_per_paper_for_smaller_selections(self):
        engine = GapAnalyzerEngine()
        for count, allocation in [(2, "450–650"), (3, "350–500"), (4, "280–400"), (5, "220–350")]:
            with self.subTest(count=count):
                prompt = engine._report_prompt(sources()[:count])
                self.assertIn(f"{count} selected papers", prompt)
                self.assertIn(allocation, prompt)

    def test_no_static_fallback_or_quoted_extracts_in_engine_output(self):
        engine = GapAnalyzerEngine()
        engine.documents = sources()
        engine.llm.generate_text = MagicMock(side_effect=RuntimeError("unavailable"))
        result = engine._complete_report("## 1. Literature Summary\nModel-written summary.", "education", sources(), DEFAULT_MODEL)
        self.assertIn("Model-written summary.", result)
        self.assertNotIn("Retrieved excerpt:", result)
        self.assertNotIn("Bibliographic record retrieved", result)
        self.assertFalse(any(text in result for text in GUIDANCE))

    def test_short_report_expands_with_model_prose_preserving_existing_findings(self):
        engine = GapAnalyzerEngine()
        docs = sources()[:2]
        engine.documents = docs
        engine.paper_metadata_list = [{"id": doc.metadata["paper_id"]} for doc in docs]
        report = "\n\n".join(f"## {i}. {title}\nOriginal supported finding [Study](https://example.org/paper-1)." for i, title in enumerate(REPORT_SECTIONS, 1))
        completion = "\n\n".join(f"## {i}. {REPORT_SECTIONS[i-1]}\nEvaluate curriculum alignment through independent educational review and held-out retrieval tasks." for i in range(2, 8))
        engine.llm.generate_text = MagicMock(return_value=(completion, "fixture", []))
        result = engine._complete_report(report, "education", docs, DEFAULT_MODEL)
        engine.llm.generate_text.assert_called_once()
        self.assertIn("Original supported finding", result)
        self.assertIn("Evaluate curriculum alignment", result)
        self.assertNotIn("Retrieved excerpt:", result)
        self.assertFalse(any(text in result for text in GUIDANCE))

    def test_budget_keeps_all_five_including_metadata_only_selection(self):
        engine = GapAnalyzerEngine()
        docs = sources()
        engine.documents = docs
        engine._get_balanced_documents = MagicMock(return_value=docs)
        chosen = engine._report_documents("educational RAG chatbots")
        self.assertEqual({doc.metadata["paper_id"] for doc in chosen}, {f"paper-{i}" for i in range(1, 6)})
        self.assertLessEqual(token_count(format_evidence(chosen)[0]), 4000)

    def test_source_abstract_precedes_bibliography_and_retains_source_identity(self):
        engine = GapAnalyzerEngine()
        doc = Document(page_content="References: Other survey https://example.org/a 2024. Other paper https://example.org/b 2025. More https://example.org/c 2026.",
                       metadata={"paper_id": "selected", "paper_title": "Selected education study", "page": 12, "evidence_scope": "full_text"})
        engine.documents = [doc]
        engine.paper_metadata_list = [{"id": "selected", "abstract": "<jats:p>This study evaluates curriculum-aligned retrieval for educational chatbots.</jats:p>"}]
        overview = engine._source_overviews([doc])[0]
        self.assertEqual(overview.metadata["paper_id"], "selected")
        self.assertNotIn("page", overview.metadata)
        self.assertNotIn("<jats", overview.page_content)
        self.assertIn("curriculum-aligned", overview.page_content)
        self.assertTrue(engine._reference_heavy(doc.page_content))
        self.assertFalse(engine._reference_heavy(overview.page_content))

    def test_omitted_summaries_and_source_list_recover_every_selection(self):
        docs = sources()
        citations = format_evidence(docs)[1]
        draft = "## 1. Literature Summary\n\n" + "\n\n".join(f"Supported summary {citations[f'E{i}']}" for i in (1, 2, 3))
        restored = ensure_source_summaries(draft + "\n\n## 2. Trend Detection\nExisting analysis.", docs)
        rendered = compact_report_citations(restored)
        self.assertIn("Retrieved excerpt:", rendered)
        self.assertIn("Bibliographic record retrieved", rendered)
        self.assertIn("Existing analysis.", rendered)
        for i in range(1, 6):
            self.assertIn(f"Educational chatbot study {i}", rendered)
            self.assertIn(f"**Source {i}:**", rendered)
        self.assertEqual(ensure_source_summaries(restored, docs), restored)

    def test_bibliography_titles_do_not_become_selected_paper_summaries(self):
        docs = sources()
        draft = "## 1. Literature Summary\n\n- **Educational chatbot study 1** — Supported source summary [Study](https://example.org/paper-1).\n\n- **An unselected systematic survey from the bibliography** — Unselected study described as a selection [Study](https://example.org/paper-1)."
        result = ensure_source_summaries(draft, docs)
        self.assertIn("Supported source summary", result)
        self.assertNotIn("unselected systematic survey", result)
        for i in range(1, 6):
            self.assertIn(f"paper-{i}", result)

    def test_model_completes_only_rejected_sections_without_full_paper_resend(self):
        engine = GapAnalyzerEngine()
        docs = sources()
        engine.documents = docs
        valid = "\n\n".join(f"## {i}. {title}\nSupported content [Study](https://example.org/paper-1)." for i, title in enumerate(REPORT_SECTIONS, 1))
        report = valid.replace("## 6. Research Gaps\nSupported content [Study](https://example.org/paper-1).", f"## 6. Research Gaps\n{OMITTED_PASSAGE}.")
        engine.llm.generate_text = MagicMock(return_value=("## 6. Research Gaps\nEvaluate curriculum coverage and multilingual retrieval separately from answer faithfulness, using held-out course materials to identify where educational chatbots fail.", "fixture", []))
        result = engine._complete_report(report, "education", docs, DEFAULT_MODEL)
        engine.llm.generate_text.assert_called_once()
        args = engine.llm.generate_text.call_args.args
        self.assertEqual(args[2], "")
        self.assertEqual(args[4], "report_guidance")
        self.assertNotIn("## 1.", args[1])
        self.assertIn("held-out course materials", result)
        self.assertNotIn(GUIDANCE[5], result)
        self.assertEqual(len(sections_needing_guidance(result)), 0)

    def test_guidance_parser_handles_bold_labels_and_blocks_unsupported_claims(self):
        response = "## 6. Research Gaps\n**General guidance:** Evaluate multilingual retrieval separately from answer faithfulness.\n\n## 7. Future Directions\nThe paper reports superior accuracy."
        parsed = parse_model_guidance(response, [6, 7])
        self.assertEqual(list(parsed), [6])
        self.assertIn("multilingual retrieval", parsed[6])

    def test_long_completion_retries_only_omitted_sections_once(self):
        engine = GapAnalyzerEngine()
        engine.documents = sources()
        report = "\n\n".join(
            f"## {i}. {title}\n" + (OMITTED_PASSAGE if i in (6, 8) else "Supported content [Study](https://example.org/paper-1).")
            for i, title in enumerate(REPORT_SECTIONS, 1)
        )
        engine.llm.generate_text = MagicMock(side_effect=[
            ("## 6. Research Gaps\nEvaluate curriculum coverage using held-out course material.", "fixture", []),
            ("## 8. Novel Paper Suggestions\nDesign a curriculum-aware retrieval benchmark with independent evaluation.", "fixture", []),
        ])
        result = engine._complete_report(report, "education", sources(), DEFAULT_MODEL)
        self.assertEqual(engine.llm.generate_text.call_count, 2)
        second = engine.llm.generate_text.call_args_list[1].args[1]
        self.assertIn("## 8.", second)
        self.assertNotIn("## 6.", second)
        self.assertIn("held-out course material", result)
        self.assertIn("curriculum-aware retrieval benchmark", result)
        self.assertNotIn("> Partial report:", result)

    def test_guidance_outage_is_partial_report_not_canned_success(self):
        engine = GapAnalyzerEngine()
        engine.documents = sources()
        engine.llm.generate_text = MagicMock(side_effect=RuntimeError("API quota exhausted"))
        result = engine._complete_report("## 1. Literature Summary\nSupported summary.", "education", sources(), DEFAULT_MODEL)
        self.assertIn("> Partial report:", result)
        self.assertIn("Common Methods", result)
        self.assertIn("Supported summary.", result)
        self.assertNotIn(GUIDANCE[2], result)
        self.assertNotIn("API quota exhausted", result)
        for i in range(1, 6):
            self.assertIn(f"Educational chatbot study {i}", result)

    def test_guidance_keeps_numbered_steps_and_model_names_but_not_result_metrics(self):
        text = "Compare (1) dense retrieval and (2) sparse retrieval before conditioning GPT-4.1 on the selected passages."
        parsed = parse_model_guidance(f"## 3. Common Methods\n{text}", [3])
        self.assertEqual(parsed[3], text)
        for claim in ("Accuracy reaches 99%.", "Latency below 1 s.", "Improvement with p < 0.05."):
            self.assertEqual(parse_model_guidance(f"## 3. Common Methods\n{claim}", [3]), {})

    def test_valid_tables_survive_but_rejected_empty_tables_do_not(self):
        table = "| Method | Role |\n| --- | --- |\n| Retrieval | Evidence selection |"
        self.assertIn(table, complete_report_sections(f"## 3. Common Methods\n{table}"))
        bad = f"| Method | Role |\n| --- | --- |\n| {OMITTED_PASSAGE} | — |"
        self.assertNotIn("| Method | Role |", complete_report_sections(f"## 3. Common Methods\n{bad}"))

    def test_project_suggestions_cannot_promise_uncited_significance_or_latency(self):
        table = "## 8. Novel Paper Suggestions\n| Proposed Title | Core Idea | Expected Outcome (hypothesis) |\n| --- | --- | --- |\n| Proposed research | Classroom trial | Scores improve with p < 0.05 |\n| Proposed research | Quantize models | Latency below 1 s |"
        result = ground_answer(table, {}, [], allow_proposals=True, preserve_valid_blocks=True)
        self.assertNotIn("p < 0.05", result)
        self.assertNotIn("Latency below 1 s", result)
        self.assertIn(OMITTED_PASSAGE, result)

    def test_parenthesized_slash_citations_resolve_without_exposing_internal_ids(self):
        docs = sources()[:2]
        result = ground_answer("The studies evaluate retrieval (E1/E2).", format_evidence(docs)[1], docs)
        self.assertNotIn("E1/E2", result)
        self.assertIn("https://example.org/paper-1", result)
        self.assertIn("https://example.org/paper-2", result)
        invalid = ground_answer("A finding (E1/E999).", format_evidence(docs)[1], docs)
        self.assertIn("not supplied", invalid)


if __name__ == "__main__":
    unittest.main()
