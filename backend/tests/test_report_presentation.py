"""Section guidance and readable citations without extra API calls."""

import unittest

from langchain_core.documents import Document

from app.services.evidence import OMITTED_PASSAGE, format_evidence, ground_answer
from app.services.report_presentation import (
    GENERAL_GUIDANCE,
    compact_report_citations,
    complete_report_sections,
    concise_guidance,
    covered_papers,
    section_bodies,
    thin_paper_analysis,
    reject_speculative_methods,
)


class ReportPresentationTests(unittest.TestCase):
    def test_guidance_is_brief_and_legacy_label_is_removed(self):
        guidance = "Compare the selected multilingual retrieval and FAQ baselines under the same curriculum. " + "This additional sentence repeats broad general advice. " * 20
        result = concise_guidance("## 3. Common Methods\nCited paper analysis remains.\n\n**General guidance (not findings from the selected papers)**\n\n" + guidance)
        self.assertNotIn("not findings", result)
        self.assertIn("Cited paper analysis remains", result)
        self.assertLessEqual(len(result.split("**General guidance**")[1].split()), 60)
        bold_colon = concise_guidance("**General guidance:** " + guidance)
        self.assertLessEqual(len(bold_colon.split("**General guidance**")[1].split()), 60)

    def test_source_appendix_is_not_counted_as_section_coverage(self):
        report = "## 7. Future Directions\nOnly source A [A](https://example.org/a).\n\n## Selected sources\n[B](https://example.org/b)"
        docs = [Document(page_content="A", metadata={"paper_id":"a", "source":"https://example.org/a"}), Document(page_content="B", metadata={"paper_id":"b", "source":"https://example.org/b"})]
        self.assertEqual(covered_papers(section_bodies(report)[7], docs), {"a"})

    def test_short_source_mentions_do_not_replace_analysis(self):
        docs = [Document(page_content="Selected study abstract", metadata={"source":"https://example.org/a", "evidence_scope":"abstract_only"})]
        self.assertTrue(thin_paper_analysis("Uses RAG [A](https://example.org/a).", docs))
        docs[0].metadata["evidence_scope"] = "metadata_only"
        self.assertFalse(thin_paper_analysis("Metadata only [A](https://example.org/a).", docs))

    def test_speculative_author_methods_are_not_presented_as_findings(self):
        report = "## 3. Common Methods\nThe study likely employs dense embeddings [E1].\n\nThe abstract describes retrieval with prompt engineering [E2].\n\n## 7. Future Directions\nProposed research: multilingual retrieval may improve coverage [E2]."
        result = reject_speculative_methods(report)
        self.assertNotIn("likely employs", result)
        self.assertIn("speculative attribution", result)
        self.assertIn("retrieval with prompt engineering", result)
        self.assertIn("Proposed research", result)

    def test_metadata_title_does_not_establish_a_method(self):
        doc = Document(page_content="A RAG chatbot for engineering", metadata={"source": "https://example.org/metadata", "evidence_scope": "metadata_only"})
        guessed = "## 3. Common Methods\nThe application retrieves engineering standards from a vector store [Study](https://example.org/metadata)."
        self.assertIn("speculative attribution", reject_speculative_methods(guessed, [doc]))
        honest = "## 3. Common Methods\nThe supplied record does not disclose the retrieval method [Study](https://example.org/metadata)."
        self.assertNotIn("speculative attribution", reject_speculative_methods(honest, [doc]))
        for statement in ("No methodological details are available.",
                          "The record does not contain any description of the methods.",
                          "No explicit methods can be extracted.",
                          "The record lacks an abstract or methodological details.",
                          "The excerpt does not detail the experimental setup or methods.",
                          "The retrieval methods are not mentioned.",
                          "Methodological details are absent.",
                          "The record doesn't describe the method.",
                          "No abstract is supplied, preventing assessment of the retrieval method."):
            with self.subTest(statement=statement):
                honest = f"## 3. Common Methods\n{statement} [Study](https://example.org/metadata)."
                self.assertNotIn("speculative attribution", reject_speculative_methods(honest, [doc]))
        guessed = "## 3. Common Methods\nThe system uses not only retrieval but also a vector store [Study](https://example.org/metadata)."
        self.assertIn("speculative attribution", reject_speculative_methods(guessed, [doc]))
        doc.metadata["evidence_scope"] = "full_text"
        self.assertNotIn("speculative attribution", reject_speculative_methods(guessed, [doc]))

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

    def test_source_appendices_merge_without_losing_uncited_selections(self):
        raw = ("## 1. Literature Summary\nFinding [First paper](https://example.org/a).\n\n"
               "## Selected sources\n- [First paper](https://example.org/a)\n- [Second paper](https://example.org/b)\n\n"
               "## Sources\n- **Source 1:** [First paper](https://example.org/a)")
        result = compact_report_citations(raw)
        self.assertEqual(result.count("## Sources"), 1)
        self.assertNotIn("## Selected sources", result)
        self.assertIn("**Source 2:** [Second paper](https://example.org/b)", result)
        self.assertIn("Finding [Source 1](https://example.org/a)", result)
        self.assertEqual(compact_report_citations(result), result)

    def test_uploaded_sources_without_urls_remain_in_single_appendix(self):
        raw = "## 1. Literature Summary\nFinding [upload.pdf].\n\n## Sources\n- [upload.pdf]\n- [second-upload.pdf]"
        result = compact_report_citations(raw)
        self.assertEqual(result.count("## Sources"), 1)
        self.assertIn("- [upload.pdf]", result)
        self.assertIn("- [second-upload.pdf]", result)
        self.assertEqual(compact_report_citations(result), result)


if __name__ == "__main__":
    unittest.main()
