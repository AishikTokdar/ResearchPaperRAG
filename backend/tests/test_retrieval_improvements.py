"""Offline behavior regressions, not a substitute for a labeled research corpus."""

import asyncio
import io
import subprocess
import threading
import unittest
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.config import DEFAULT_MODEL
from app.services.analysis_progress import prepare_analysis
from app.services.chunking import LOCAL_EMBEDDING_MODEL, embedding_tokenizer, split_documents
from app.services.evidence import format_evidence, ground_answer
from app.services.gap_analyzer_engine import GapAnalyzerEngine, REPORT_SECTIONS
from app.services.hybrid_retrieval import HybridIndex
from app.services.paper_fetcher import PaperFetcher
from app.services.pdf_extraction import extract_pdf, extract_pdf_bytes
from app.services.research_sessions import ResearchSession


class RetrievalTests(unittest.TestCase):
    def test_keyword_only_hit_is_recovered_outside_dense_candidates(self):
        docs = [Document(page_content=f"General evidence passage {i}") for i in range(40)]
        target = Document(page_content="The ZXQ-17 ablation evaluates instrument drift.")
        docs.append(target)
        store = MagicMock()
        store.similarity_search.return_value = docs[:30]
        results = HybridIndex(docs).search(store, "ZXQ-17", 30)
        self.assertIn(target, results[:3])
        store.similarity_search.assert_called_once()

    def test_empty_lexical_query_has_no_arbitrary_keyword_ranking(self):
        index = HybridIndex([Document(page_content="nothing relevant")])
        self.assertEqual(index.lexical("ZXQ-17"), [])

    def test_balancing_embeds_query_once_and_recovers_small_source(self):
        engine = GapAnalyzerEngine()
        engine.documents = [
            Document(page_content=f"Methods evidence {i}", metadata={"paper_id": "a"})
            for i in range(40)
        ]
        rare = Document(
            page_content="Methods evidence from small source", metadata={"paper_id": "b"}
        )
        engine.documents.append(rare)
        engine.paper_metadata_list = [{"id": "a"}, {"id": "b"}]
        engine.vector_store = MagicMock()
        engine.vector_store.similarity_search.return_value = engine.documents
        result = engine._get_balanced_documents("methods", top_k_per_paper=2)
        self.assertIn(rare, result[:2])
        engine.vector_store.similarity_search.assert_called_once()

    def test_real_minilm_tokenizer_bounds_chunks_and_keeps_page_sections(self):
        tokenizer = embedding_tokenizer()
        text = (
            "Methods\n"
            + "Electroencephalographic characterization of microarchitectural interdependencies. "
            * 90
        )
        docs = split_documents([Document(page_content=text, metadata={"page": 7, "paper_id": "p"})])
        self.assertGreater(len(docs), 2)
        self.assertTrue(
            all(
                len(tokenizer.encode(doc.page_content, add_special_tokens=True)) <= 256
                for doc in docs
            )
        )
        self.assertTrue(
            all(doc.metadata["page"] == 7 and doc.metadata["section"] == "Methods" for doc in docs)
        )
        self.assertEqual(LOCAL_EMBEDDING_MODEL, "sentence-transformers/all-MiniLM-L6-v2")


class GroundingChecks(unittest.TestCase):
    def setUp(self):
        self.docs = [Document(page_content="The measured accuracy was 91% on held-out data.")]
        self.citations = format_evidence(self.docs)[1]

    def test_supported_number_passes(self):
        result = ground_answer("Accuracy was 91% [E1].", self.citations, self.docs)
        self.assertIn("91%", result)
        self.assertNotIn("cannot", result)

    def test_valid_id_does_not_excuse_invented_number(self):
        self.assertIn(
            "numerical claim", ground_answer("Accuracy was 99% [E1].", self.citations, self.docs)
        )

    def test_disclaimer_cannot_excuse_uncited_claim_elsewhere(self):
        for text in (
            "Insufficient evidence.\n\nAccuracy was 99%.",
            "Supported [E1].\n\nUncited finding.",
            "Supported [E1].\n- Uncited finding.",
        ):
            self.assertIn("did not cite", ground_answer(text, self.citations, self.docs))

    def test_uncited_table_data_is_rejected(self):
        text = "Supported [E1].\n\n| Method | Result |\n| --- | --- |\n| Unmeasured method | Best |"
        self.assertIn("did not cite", ground_answer(text, self.citations, self.docs))

    def test_table_headers_and_numbered_headings_are_not_claims(self):
        text = "## 1. Results\n\n| Method | Accuracy |\n| --- | --- |\n| Test [E1] | 91% |"
        self.assertNotIn("cannot", ground_answer(text, self.citations, self.docs))

    def test_opted_in_background_mode_still_checks_document_claims(self):
        answer = "Accuracy was 91% [E1].\n\n## Background knowledge\n\nGeneral background beyond the source."
        self.assertIn("did not cite", ground_answer(answer, self.citations, self.docs))
        self.assertIn(
            "General background",
            ground_answer(answer, self.citations, self.docs, allow_background=True),
        )
        self.assertIn(
            "numerical claim",
            ground_answer(
                answer.replace("91%", "99%"), self.citations, self.docs, allow_background=True
            ),
        )


class CachingAndConversationTests(unittest.TestCase):
    def test_streaming_report_reuses_verified_generation(self):
        engine = GapAnalyzerEngine()
        engine._report_documents = MagicMock(
            return_value=[Document(page_content="Supported evidence")]
        )
        report = "\n\n".join(
            f"## {i}. {title}\nSupported evidence [E1]."
            for i, title in enumerate(REPORT_SECTIONS, 1)
        )
        calls = []

        async def stream(*args):
            calls.append(args)
            yield {"type": "complete", "answer": report, "warnings": []}

        engine.llm.stream_text = stream

        async def collect():
            return [
                event async for event in engine.stream_gap_report("topic", "gemini", DEFAULT_MODEL)
            ]

        first, second = asyncio.run(collect()), asyncio.run(collect())
        self.assertEqual(first[-1]["report"], second[-1]["report"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(second[-1]["sections_completed"], list(range(1, 9)))

    def test_warning_and_unverified_reports_are_not_cached(self):
        engine = GapAnalyzerEngine()
        doc = Document(page_content="Supported evidence")
        engine.llm.generate_text = MagicMock(return_value=("Unsupported 99% [E1]", "fake", []))
        for _ in range(2):
            engine._cached_generate("system", "question", [doc], "model", "test", 100)
        self.assertEqual(engine.llm.generate_text.call_count, 2)

    def test_incomplete_and_warning_bearing_reports_do_not_poison_cache(self):
        engine = GapAnalyzerEngine()
        docs = [Document(page_content="Supported evidence")]
        for warnings in ([], ["Output was interrupted"]):
            engine.llm.generate_text = MagicMock(
                return_value=("## 1. Literature Summary\nSupported [E1].", "fake", warnings)
            )
            for _ in range(2):
                engine._cached_generate("system", "question", docs, "model", "gap_report", 100)
            self.assertEqual(engine.llm.generate_text.call_count, 6 if not warnings else 2)

    def test_changed_evidence_or_generation_settings_invalidate_answers(self):
        engine = GapAnalyzerEngine()
        engine.llm.generate_text = MagicMock(return_value=("Supported [E1].", "fake", []))
        for text, model, budget in (
            ("first evidence", "model", 100),
            ("changed evidence", "model", 100),
            ("changed evidence", "other", 100),
            ("changed evidence", "other", 200),
        ):
            engine._cached_generate(
                "system", "question", [Document(page_content=text)], model, "test", budget
            )
        self.assertEqual(engine.llm.generate_text.call_count, 4)

    def test_identical_preparation_reuses_index_but_changed_source_invalidates(self):
        session = ResearchSession()
        paper = {"id": "p", "title": "Paper", "abstract": "Abstract evidence"}
        with (
            patch(
                "app.services.analysis_progress.PaperFetcher.download_and_extract_text",
                return_value="Evidence",
            ) as fetch,
            patch(
                "app.services.analysis_progress.GapAnalyzerEngine.process_and_index_papers"
            ) as index,
        ):
            first = prepare_analysis(session, [paper], [], lambda event: None, threading.Event())
            second = prepare_analysis(session, [paper], [], lambda event: None, threading.Event())
            self.assertIs(first, second)
            self.assertEqual(index.call_count, 1)
            prepare_analysis(
                session,
                [{**paper, "abstract": "Updated evidence"}],
                [],
                lambda event: None,
                threading.Event(),
            )
            self.assertEqual(index.call_count, 2)
            self.assertEqual(fetch.call_count, 2)

    def test_followup_references_use_bounded_server_history(self):
        engine = GapAnalyzerEngine()
        engine._topic = "Graph retrieval"
        engine._history = [("How does the graph model work?", "Supported context")]
        engine.documents = [Document(page_content="Graph model methods and limitations")]
        engine.vector_store = MagicMock()
        engine.vector_store.similarity_search.return_value = engine.documents
        engine._cached_generate = MagicMock(return_value="Supported answer")
        for _ in range(4):
            engine.ask_followup("What are its limitations?".replace("its", "their"))
        self.assertEqual(len(engine._history), 2)
        self.assertIn("untrusted context", engine._cached_generate.call_args.args[1])
        self.assertIn("Graph retrieval", engine.vector_store.similarity_search.call_args.args[0])

    def test_partial_pdf_coverage_is_visible(self):
        result = GapAnalyzerEngine._coverage_note(
            "Report",
            [Document(page_content="Evidence", metadata={"evidence_scope": "partial_full_text"})],
        )
        self.assertIn("coverage is incomplete", result)


class ParsingAndDiscoveryTests(unittest.TestCase):
    def test_actual_layout_worker_extracts_text_with_page_provenance(self):
        writer = PdfWriter()
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        for number in range(2):
            page = writer.add_blank_page(width=600, height=800)
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
            )
            contents = DecodedStreamObject()
            contents.set_data(
                f"BT /F1 12 Tf 30 700 Td (Supported result on page {number + 1}.) Tj ET".encode()
            )
            page[NameObject("/Contents")] = contents
        buffer = io.BytesIO()
        writer.write(buffer)
        parsed = extract_pdf_bytes(buffer.getvalue())
        self.assertTrue(parsed["complete"])
        self.assertEqual(parsed["total_pages"], 2)
        self.assertEqual(parsed["pages"][1]["page"], 1)
        self.assertIn("Supported result on page 2", parsed["pages"][1]["text"])

    def test_native_parser_timeout_is_enforced(self):
        with patch(
            "app.services.pdf_extraction.subprocess.run",
            side_effect=subprocess.TimeoutExpired("parser", 30),
        ):
            with self.assertRaisesRegex(ValueError, "processing limit"):
                extract_pdf("unused.pdf")

    def test_actual_isolated_parser_rejects_blank_pdf_with_ocr_guidance(self):
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        buffer = io.BytesIO()
        writer.write(buffer)
        with self.assertRaisesRegex(ValueError, "OCR"):
            extract_pdf_bytes(buffer.getvalue())

    def test_fetched_pdf_does_not_silently_stop_at_page_thirty(self):
        paper = {"pdf_url": "https://example.org/paper.pdf", "abstract": "Available abstract"}
        pages = [{"page": i, "text": f"Page {i} evidence"} for i in range(45)]
        with (
            patch("app.services.paper_fetcher.download_pdf", return_value=b"PDF"),
            patch(
                "app.services.paper_fetcher.extract_pdf_bytes",
                return_value={"pages": pages, "total_pages": 45, "complete": True},
            ),
        ):
            text = PaperFetcher().download_and_extract_text(paper)
        self.assertIn("--- Page 45 ---", text)
        self.assertEqual(paper["evidence_scope"], "full_text")

    def test_discovery_relevance_dedup_and_partial_failure_status(self):
        fetcher = PaperFetcher()
        relevant = {
            "id": "a",
            "title": "Exact graph retrieval",
            "url": "https://doi.org/10.1/test",
            "year": "2025",
        }
        duplicate = {
            "id": "b",
            "title": "Different punctuation and title",
            "doi": "10.1/test",
            "year": "2026",
        }
        irrelevant = {
            "id": "c",
            "title": "Ocean salinity",
            "year": "2026",
            "is_open_access": True,
            "citations": 99999,
        }
        statuses = []
        with (
            patch.object(fetcher, "search_arxiv", return_value=[relevant]),
            patch.object(fetcher, "search_crossref", return_value=[duplicate, irrelevant]),
            patch.object(
                fetcher, "search_semantic_scholar", side_effect=RuntimeError("private error")
            ),
            patch.object(fetcher, "search_openalex", return_value=[]),
            patch.object(fetcher, "search_pubmed", return_value=[]),
            patch.object(fetcher, "search_doaj", return_value=[]),
        ):
            results = fetcher.search_all("graph retrieval", source_status=statuses)
        self.assertEqual([paper["id"] for paper in results], ["a", "c"])
        self.assertIn({"source": "Semantic Scholar", "status": "unavailable"}, statuses)
        self.assertNotIn("private error", str(statuses))

    def test_pubmed_fetches_actual_structured_abstract(self):
        search = MagicMock()
        search.status_code = 200
        search.json.return_value = {"esearchresult": {"idlist": ["123"]}}
        article = MagicMock()
        article.content = b"""<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><ArticleTitle>Evidence study</ArticleTitle><Journal><JournalIssue><PubDate><Year>2026</Year></PubDate></JournalIssue></Journal><Abstract><AbstractText Label="RESULTS">Measured accuracy was 91%.</AbstractText></Abstract></Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1/test</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"""
        with patch("app.services.paper_fetcher.requests.get", side_effect=[search, article]):
            results = PaperFetcher().search_pubmed("evidence")
        self.assertEqual(results[0]["abstract"], "RESULTS: Measured accuracy was 91%.")
        self.assertFalse(results[0]["is_open_access"])
        self.assertEqual(results[0]["doi"], "10.1/test")


if __name__ == "__main__":
    unittest.main()
