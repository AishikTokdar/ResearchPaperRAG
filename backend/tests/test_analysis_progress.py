"""Offline progress-stream regressions; no external model or paper APIs are called."""
import asyncio
import json
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from app.routes import gap_analyzer as routes
from app.services.analysis_progress import prepare_analysis
from app.services.gap_analyzer_engine import GapAnalyzerEngine, REPORT_SECTIONS
from app.services.research_sessions import ResearchSession, ResearchSessionRegistry


def parse_events(text):
    result = []
    for block in text.strip().split("\n\n"):
        event = next(line[7:] for line in block.splitlines() if line.startswith("event: "))
        data = next(line[6:] for line in block.splitlines() if line.startswith("data: "))
        result.append((event, json.loads(data)))
    return result


class ReportProgressTests(unittest.TestCase):
    def test_progress_tracks_observed_sections_and_only_final_report_is_grounded(self):
        engine = GapAnalyzerEngine()
        engine._report_documents = MagicMock(return_value=[Document(page_content="Supported result", metadata={"source_file": "Paper.pdf", "page": 0})])
        async def tokens(*args):
            for index, title in enumerate(REPORT_SECTIONS, 1):
                yield {"type": "token", "content": f"## {index}. "}
                yield {"type": "token", "content": f"{title}\nSupported result [E1].\n\n"}
            yield {"type": "complete", "answer": "\n".join(f"## {i}. {title}\nSupported [E1]." for i, title in enumerate(REPORT_SECTIONS, 1)), "warnings": []}
        engine.llm.stream_text = tokens
        async def collect():
            return [event async for event in engine.stream_gap_report("topic", "gemini", "gemini-3.8-flash")]
        events = asyncio.run(collect())
        generating = [event for event in events if event["stage"] == "generate" and event.get("current_section")]
        first = next(event for event in generating if event["current_section"] == 1)
        second = next(event for event in generating if event["current_section"] == 2)
        self.assertEqual(first["sections_completed"], [])
        self.assertEqual(second["sections_completed"], [1])
        self.assertTrue(all(event["percent"] < 100 for event in events))
        self.assertIn("[Paper.pdf - Page 1]", events[-1]["report"])
        self.assertEqual(events[-1]["sections_completed"], list(range(1, 9)))
        self.assertFalse(events[-1]["limited"])

    def test_insufficient_evidence_uses_no_generation_call(self):
        engine = GapAnalyzerEngine()
        engine._report_documents = MagicMock(return_value=[])
        engine.llm = MagicMock()
        async def collect():
            return [event async for event in engine.stream_gap_report("topic", "gemini", "gemini-3.8-flash")]
        events = asyncio.run(collect())
        engine.llm.stream_text.assert_not_called()
        self.assertIn("Insufficient evidence", events[-1]["report"])

    def test_uploaded_passages_are_indexed_in_same_research_engine(self):
        engine = GapAnalyzerEngine()
        paper = {"id": "uploaded", "title": "Uploaded.pdf"}
        chunks = [Document(page_content="Uploaded evidence", metadata={"paper_id": "uploaded", "page": 0})]
        progress = []
        with patch("app.services.gap_analyzer_engine.get_local_embeddings", return_value=object()), patch("app.services.gap_analyzer_engine.FAISS.from_documents", return_value=object()) as index:
            count = engine.process_and_index_papers([], uploaded_papers=[(paper, chunks)], on_progress=progress.append)
        self.assertEqual(count, 1)
        self.assertEqual(index.call_args.args[0], chunks)
        self.assertEqual(engine.paper_metadata_list, [paper])
        self.assertEqual(progress[0]["stage"], "index")

    def test_cancelled_preparation_keeps_previous_session_engine(self):
        session = ResearchSession()
        old = session.engine = object()
        cancelled = threading.Event()
        cancelled.set()
        with patch("app.services.analysis_progress.PaperFetcher.download_and_extract_text") as download:
            with self.assertRaises(InterruptedError):
                prepare_analysis(session, [{"id": "p"}], [], lambda event: None, cancelled)
        download.assert_not_called()
        self.assertIs(session.engine, old)
        self.assertTrue(session.lock.acquire(blocking=False))
        session.lock.release()


class StreamEndpointTests(unittest.TestCase):
    def setUp(self):
        self.patch = patch.object(routes, "sessions", ResearchSessionRegistry())
        self.patch.start()
        self.addCleanup(self.patch.stop)
        for store in ("_ask_hits", "_upload_hits"):
            cleanup = patch.dict(f"app.services.ip_rate_limit.{store}", {}, clear=True)
            cleanup.start()
            self.addCleanup(cleanup.stop)
        app = FastAPI()
        app.include_router(routes.router)
        self.client = TestClient(app)
        self.headers = {"X-Chat-Session-Id": str(uuid4())}
        self.session = routes.sessions.get(self.headers["X-Chat-Session-Id"])
        self.session.papers["known"] = {"id": "known", "title": "Trusted paper"}
        self.form = {"topic": "research", "paper_ids": '["known"]', "provider": "gemini", "model_name": "gemini-3.8-flash"}

    def test_stream_prepares_sources_and_emits_done_with_final_report(self):
        class Engine:
            async def stream_gap_report(self, *args):
                yield {"stage": "generate", "percent": 60, "message": "Writing Literature Summary"}
                yield {"stage": "verify", "percent": 99, "report": "Grounded final report", "sections_completed": [1]}
        with patch.object(routes, "prepare_analysis", return_value=Engine()) as prepare:
            response = self.client.post("/api/analyze/stream", headers=self.headers, data=self.form,
                files=[("files", ("uploaded.pdf", b"%PDF-test", "application/pdf"))])
        self.assertEqual(response.status_code, 200, response.text)
        events = parse_events(response.text)
        self.assertEqual(events[-1][0], "done")
        self.assertEqual(events[-1][1]["percent"], 100)
        self.assertEqual(events[-1][1]["report"], "Grounded final report")
        self.assertEqual(prepare.call_args.args[1], [{"id": "known", "title": "Trusted paper"}])
        self.assertEqual(prepare.call_args.args[2][0], ("uploaded.pdf", b"%PDF-test"))
        self.assertTrue(all(data["percent"] < 100 for event, data in events if event == "progress"))

    def test_unknown_ids_and_invalid_files_are_rejected_before_work(self):
        with patch.object(routes, "prepare_analysis") as prepare:
            response = self.client.post("/api/analyze/stream", headers=self.headers, data={**self.form, "paper_ids": '["unknown"]'})
            self.assertEqual(response.status_code, 400)
            response = self.client.post("/api/analyze/stream", headers=self.headers, data=self.form,
                files=[("files", ("fake.pdf", b"not a PDF", "application/pdf"))])
            self.assertEqual(response.status_code, 400)
            prepare.assert_not_called()

    def test_failure_emits_error_not_false_completion_or_private_diagnostics(self):
        with patch.object(routes, "prepare_analysis", side_effect=RuntimeError("private diagnostic")), patch.object(routes.logger, "exception"):
            response = self.client.post("/api/analyze/stream", headers=self.headers, data=self.form)
        events = parse_events(response.text)
        self.assertEqual(events[-1][0], "error")
        self.assertNotIn("private diagnostic", response.text)
        self.assertFalse(any(event == "done" for event, _ in events))


if __name__ == "__main__":
    unittest.main()
