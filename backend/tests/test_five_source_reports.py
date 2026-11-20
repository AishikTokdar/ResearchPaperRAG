"""Five selections must remain visible after budgeting, validation and rendering."""

import asyncio
import json
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
    return [Document(page_content=f"Study {i} evaluates educational chatbot retrieval. Its source-specific objective is curriculum coverage. Original supported finding. Curriculum coverage is the source-specific objective. Additional paper analysis. The studies evaluate retrieval.",
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

    def test_repairs_keep_the_original_selection_word_allocation(self):
        for count, limits in [(2, [450, 650]), (3, [350, 500]), (4, [280, 400]), (5, [220, 350])]:
            with self.subTest(count=count):
                engine = GapAnalyzerEngine()
                engine.llm.generate_text = MagicMock(side_effect=RuntimeError("Offline"))
                engine._complete_report("## 1. Literature Summary\nPartial draft.", "Any discovery query", sources()[:count], DEFAULT_MODEL)
                request = json.loads(engine.llm.generate_text.call_args.args[1])
                self.assertEqual(request["selection_size"], count)
                self.assertEqual(request["per_paper_word_range"], limits)

    def test_no_static_fallback_or_quoted_extracts_in_engine_output(self):
        engine = GapAnalyzerEngine()
        engine.documents = sources()
        engine.llm.generate_text = MagicMock(side_effect=RuntimeError("unavailable"))
        result = engine._complete_report("## 1. Literature Summary\nModel-written summary.", "education", sources(), DEFAULT_MODEL)
        self.assertIn("Model-written summary.", result)
        self.assertNotIn("Retrieved excerpt:", result)
        self.assertNotIn("Bibliographic record retrieved", result)
        self.assertFalse(any(text in result for text in GUIDANCE))

    def test_incomplete_paper_coverage_repairs_with_cited_source_analysis(self):
        engine = GapAnalyzerEngine()
        docs = sources()[:2]
        engine.documents = docs
        engine.paper_metadata_list = [{"id": doc.metadata["paper_id"]} for doc in docs]
        report = "\n\n".join(f"## {i}. {title}\nOriginal supported finding [Study](https://example.org/paper-1)." for i, title in enumerate(REPORT_SECTIONS, 1))
        completion = "\n\n".join(f"## {i}. {REPORT_SECTIONS[i-1]}\nOriginal supported finding [E1]. Curriculum coverage is the source-specific objective [E2]." for i in range(1, 8))
        engine.llm.generate_text = MagicMock(return_value=(completion, "fixture", []))
        result = engine._complete_report(report, "education", docs, DEFAULT_MODEL)
        engine.llm.generate_text.assert_called_once()
        self.assertIn("Original supported finding", result)
        self.assertIn("Curriculum coverage", result)
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

    def test_repair_adds_missing_paper_without_losing_prior_valid_entry(self):
        engine = GapAnalyzerEngine()
        docs = sources()[:2]
        engine.documents = docs
        engine.paper_metadata_list = [{"id": doc.metadata["paper_id"]} for doc in docs]
        report = "\n\n".join(f"## {i}. {title}\nOriginal valid entry [Study](https://example.org/paper-1)." for i, title in enumerate(REPORT_SECTIONS, 1))
        completion = "\n\n".join(f"## {i}. {title}\nAdditional paper analysis [E2]." for i, title in enumerate(REPORT_SECTIONS[:7], 1))
        engine.llm.generate_text = MagicMock(return_value=(completion, "fixture", []))
        result = engine._complete_report(report, "education", docs, DEFAULT_MODEL)
        self.assertEqual(result.count("Original valid entry"), 8)
        self.assertEqual(result.count("Additional paper analysis"), 7)
        self.assertNotIn("> Partial report:", result)

    def test_second_repair_sends_only_the_missing_paper(self):
        engine = GapAnalyzerEngine()
        docs = sources()[:2]
        for doc in docs:
            doc.metadata["evidence_scope"] = "metadata_only"
        engine.documents = docs
        engine.paper_metadata_list = [{"id": doc.metadata["paper_id"]} for doc in docs]
        both = "Source coverage [A](https://example.org/paper-1) [B](https://example.org/paper-2)."
        report = "\n\n".join(f"## {i}. {title}\n{both}" for i, title in enumerate(REPORT_SECTIONS, 1))
        report = report.replace(f"## 6. Research Gaps\n{both}", "## 6. Research Gaps\nInitial source [A](https://example.org/paper-1).")
        engine.llm.generate_text = MagicMock(side_effect=[
            ("## 6. Research Gaps\nProposed research: First source analysis [E1].", "fixture", []),
            ("## 6. Research Gaps\nProposed research: Missing source analysis [E1].", "fixture", []),
        ])
        result = engine._complete_report(report, "education", docs, DEFAULT_MODEL)
        retry = engine.llm.generate_text.call_args_list[1].args
        self.assertEqual(json.loads(retry[1])["selected_titles"], [docs[1].metadata["paper_title"]])
        self.assertEqual(json.loads(retry[1])["selection_size"], 2)
        self.assertEqual(json.loads(retry[1])["per_paper_word_range"], [450, 650])
        self.assertEqual(json.loads(retry[1])["selected_sources"][0]["allowed_citations"], ["[E1]"])
        self.assertEqual(json.loads(retry[1])["requested_section_word_ranges"]["6"], [68, 98])
        self.assertNotIn(docs[0].metadata["paper_title"], retry[2])
        self.assertIn("First source analysis", result)
        self.assertIn("Missing source analysis", result)
        self.assertNotIn("> Partial report:", result)

    def test_invalid_synthesis_does_not_discard_valid_repair_entries(self):
        engine = GapAnalyzerEngine()
        docs = sources()[:2]
        engine.documents = docs
        report = "\n\n".join(f"## {i}. {title}\nSupported content [Study](https://example.org/paper-1)." for i, title in enumerate(REPORT_SECTIONS, 1))
        report = report.replace("## 6. Research Gaps\nSupported content [Study](https://example.org/paper-1).", f"## 6. Research Gaps\n{OMITTED_PASSAGE}.")
        engine.llm.generate_text = MagicMock(return_value=(
            "## 6. Research Gaps\nProposed research: Curriculum coverage can be investigated [E1].\n\nProposed research: A comparative evaluation is proposed [E2].\n\nUncited unsupported synthesis.", "fixture", []))
        result = engine._complete_report(report, "education", docs, DEFAULT_MODEL)
        engine.llm.generate_text.assert_called_once()
        self.assertIn("Curriculum coverage can be investigated", result)
        self.assertIn("comparative evaluation is proposed", result)
        self.assertNotIn("Uncited unsupported synthesis", result)

    def test_retry_receives_specific_numeric_validation_feedback(self):
        engine = GapAnalyzerEngine()
        docs = sources()[:1]
        engine.documents = docs
        report = "\n\n".join(f"## {i}. {title}\nSupported content [Study](https://example.org/paper-1)." for i, title in enumerate(REPORT_SECTIONS, 1))
        report = report.replace("## 6. Research Gaps\nSupported content [Study](https://example.org/paper-1).", f"## 6. Research Gaps\n{OMITTED_PASSAGE}.")
        engine.llm.generate_text = MagicMock(side_effect=[
            ("## 6. Research Gaps\nCurriculum coverage reaches 99% [E1].", "fixture", []),
            ("## 6. Research Gaps\nProposed research: evaluate curriculum coverage using held-out material [E1].", "fixture", []),
        ])
        result = engine._complete_report(report, "education", docs, DEFAULT_MODEL)
        feedback = json.loads(engine.llm.generate_text.call_args_list[1].args[1])["validation_feedback"]
        self.assertIn("99%", feedback[0]["rejected_paragraph"])
        self.assertIn("numerical claim", feedback[0]["reason"])
        self.assertNotIn("99%", result)
        self.assertIn("held-out material", result)

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

    def test_context_shares_budget_across_papers_and_retrieval_purposes(self):
        engine = GapAnalyzerEngine()
        docs = sources()
        engine.documents = docs
        groups = [[Document(page_content=f"{purpose} for the selected study. " * 14,
                            metadata=doc.metadata) for doc in docs]
                  for purpose in ("Methods", "Results", "Limitations")]
        engine._get_balanced_documents = MagicMock(side_effect=groups)
        chosen = engine._report_documents("educational RAG")
        for doc in docs:
            passages = " ".join(item.page_content for item in chosen
                                if item.metadata["paper_id"] == doc.metadata["paper_id"])
            for purpose in ("Methods", "Results", "Limitations"):
                self.assertIn(purpose, passages)
        self.assertLessEqual(token_count(format_evidence(chosen)[0]), 4000)

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

    def test_model_repairs_rejected_sections_using_supplied_evidence(self):
        engine = GapAnalyzerEngine()
        docs = sources()
        engine.documents = docs
        valid = "\n\n".join(f"## {i}. {title}\nSupported content [Study](https://example.org/paper-1)." for i, title in enumerate(REPORT_SECTIONS, 1))
        report = valid.replace("## 6. Research Gaps\nSupported content [Study](https://example.org/paper-1).", f"## 6. Research Gaps\n{OMITTED_PASSAGE}.")
        engine.llm.generate_text = MagicMock(return_value=("## 6. Research Gaps\nProposed research: Evaluate curriculum coverage and multilingual retrieval separately from answer faithfulness, using held-out course materials to identify where educational chatbots fail [E1].", "fixture", []))
        result = engine._complete_report(report, "education", docs, DEFAULT_MODEL)
        engine.llm.generate_text.assert_called_once()
        args = engine.llm.generate_text.call_args.args
        self.assertIn("scope=", args[2])
        self.assertEqual(args[4], "report_section_repair")
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
            ("## 6. Research Gaps\nProposed research: Evaluate curriculum coverage using held-out course material [E1].", "fixture", []),
            ("## 8. Novel Paper Suggestions\nProposed research: Design a curriculum-aware retrieval benchmark with independent evaluation [E1].", "fixture", []),
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
