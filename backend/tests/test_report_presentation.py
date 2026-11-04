"""Section guidance and readable citations without extra API calls."""

import unittest

from langchain_core.documents import Document

from app.services.evidence import OMITTED_PASSAGE, format_evidence, ground_answer
from app.services.report_presentation import (
    GENERAL_GUIDANCE,
    compact_report_citations,
    complete_report_sections,
)


class ReportPresentationTests(unittest.TestCase):
    def test_missing_middle_sections_receive_labeled_guidance(self):
        raw = f"{OMITTED_PASSAGE} (uncited introduction).\n\n## 1. Literature Summary\nSupported summary.\n\n## 5. Contradictions\n{OMITTED_PASSAGE} (a factual passage did not cite the supplied evidence).\n\n## 7. Future Directions\n{OMITTED_PASSAGE}.\n{OMITTED_PASSAGE}."
        result = complete_report_sections(raw)
        self.assertEqual(result.count("## "), 8)
        self.assertNotIn(OMITTED_PASSAGE, result)
        self.assertIn("Supported summary", result)
        self.assertIn("same population, task, dataset", result)
        self.assertIn("independent validation", result)
        self.assertEqual(result.count(GENERAL_GUIDANCE), 7)

    def test_primary_model_general_guidance_is_retained_only_for_reports(self):
        docs = [Document(page_content="An EEG classification method was evaluated.")]
        citations = format_evidence(docs)[1]
        draft = "## 5. Contradictions\nGeneral guidance: Compare study populations and outcomes before interpreting differences as contradictions."
        result = ground_answer(draft, citations, docs, allow_general_guidance=True)
        self.assertIn("Compare study populations", result)
        self.assertNotIn("cannot", result)
        self.assertIn("did not cite", ground_answer(draft, citations, docs))
        self.assertIn(
            "did not cite",
            ground_answer(
                draft.replace("Compare study populations", "Expect 99% accuracy"),
                citations,
                docs,
                allow_general_guidance=True,
            ),
        )
        self.assertIn(GENERAL_GUIDANCE, complete_report_sections(result))

    def test_rejected_passage_does_not_remove_valid_neighbor(self):
        raw = f"## 4. Limitations\nSupported limitation [Study](https://example.org/study).\n\n{OMITTED_PASSAGE} (unsupported number)."
        result = complete_report_sections(raw)
        self.assertIn("Supported limitation", result)
        self.assertNotIn("unsupported number", result)
        self.assertIn(GENERAL_GUIDANCE, result)

    def test_citation_clusters_are_short_deduplicated_and_keep_pages(self):
        raw = "Finding [A very long paper title - Page 19](https://example.org/p)[A very long paper title - Page 15](https://example.org/p)[Other study](https://example.org/q)[Other study](https://example.org/q)."
        result = compact_report_citations(raw)
        body, sources = result.split("## Sources")
        self.assertIn("[Source 1, p. 19]", body)
        self.assertIn("[Source 1, p. 15]", body)
        self.assertIn(") [Source 2]", body)
        self.assertEqual(body.count("[Source 2]"), 1)
        self.assertEqual(sources.count("A very long paper title"), 1)
        self.assertNotIn("very long paper title", body)


if __name__ == "__main__":
    unittest.main()
