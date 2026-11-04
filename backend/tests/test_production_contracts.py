"""Production boundaries and full route integration without paid services."""

import asyncio
import json
import tempfile
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from threading import BoundedSemaphore
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.routes.tunnel import _upstream
from app.services.request_limits import run_bounded_worker
from app.services.research_sessions import ResearchSessionRegistry
from integration_server import fixture_app, fixture_pdf


class ProductionBoundaryTests(unittest.TestCase):
    def test_huggingface_platform_host_is_allowed_without_wildcards(self):
        with patch.dict("os.environ", {"SPACE_HOST": "audit-space.hf.space"}):
            client = TestClient(create_app())
            self.assertEqual(
                client.get("/health", headers={"Host": "audit-space.hf.space"}).status_code, 200
            )
            self.assertEqual(
                client.get("/health", headers={"Host": "other-space.hf.space"}).status_code, 400
            )

    def test_cancelled_cpu_work_retains_capacity_until_thread_finishes(self):
        started, finish = threading.Event(), threading.Event()
        slots = BoundedSemaphore(1)

        def work():
            started.set()
            finish.wait(5)

        async def scenario():
            with patch("app.services.request_limits._worker_slots", return_value=slots):
                task = asyncio.create_task(run_bounded_worker(work))
                await asyncio.to_thread(started.wait, 2)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                with self.assertRaises(HTTPException) as error:
                    await run_bounded_worker(lambda: None)
                self.assertEqual(error.exception.status_code, 429)
                finish.set()

        try:
            asyncio.run(scenario())
            self.assertTrue(slots.acquire(blocking=False))
            slots.release()
        finally:
            finish.set()

    def test_invalid_research_probes_do_not_evict_valid_sessions(self):
        registry = ResearchSessionRegistry()
        original = registry.get(str(uuid4()))
        for _ in range(100):
            registry.get(str(uuid4()), remember=False)
        self.assertEqual(list(registry.sessions.values()), [original])

    def test_telemetry_cannot_relay_to_arbitrary_tenants_or_hosts(self):
        for dsn in (
            "http://key@o1.ingest.sentry.io/12",
            "https://key@evil.test/12",
            "https://key@o1.ingest.sentry.io/private/path",
            "https://key@o1.ingest.sentry.io:444/12",
        ):
            self.assertIsNone(_upstream(dsn))
        settings = get_settings()
        with patch.object(settings, "telemetry_tunnel_dsn", None):
            self.assertEqual(
                TestClient(create_app()).post("/api/oversight", content=b"{}").status_code, 404
            )
        with patch.object(settings, "telemetry_tunnel_dsn", "https://key@o1.ingest.sentry.io/12"):
            body = json.dumps({"dsn": "https://key@o2.ingest.sentry.io/34"})
            self.assertEqual(
                TestClient(create_app()).post("/api/oversight", content=body).status_code, 403
            )

    def test_cors_headers_survive_body_rejection_and_hosts_are_checked(self):
        with (
            patch.object(get_settings(), "allowed_hosts", "testserver"),
            patch.object(get_settings(), "cors_origins_csv", "http://localhost:5173"),
        ):
            client = TestClient(create_app())
        response = client.post(
            "/ask", content=b"x" * 140000, headers={"Origin": "http://localhost:5173"}
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")
        self.assertEqual(client.get("/health", headers={"Host": "evil.test"}).status_code, 400)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(len(response.headers["x-request-id"]), 32)

    def test_runtime_counter_read_failure_is_nonfatal(self):
        from app.services.usage_counters import read_counters

        with patch(
            "app.services.usage_counters._counter_path", side_effect=PermissionError("private path")
        ):
            self.assertEqual(read_counters(), (0, 0))

    def test_arxiv_transport_has_a_real_network_timeout(self):
        from app.services.paper_fetcher import _TimeoutAdapter

        with patch("requests.adapters.HTTPAdapter.send") as send:
            _TimeoutAdapter(5).send(object(), timeout=None)
        self.assertEqual(send.call_args.kwargs["timeout"], 5)


class CompleteAPIIntegrationTests(unittest.TestCase):
    def test_real_upload_json_stream_search_report_followup_and_session_isolation(self):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            app = fixture_app(stack, Path(temporary))
            headers = {"X-Chat-Session-Id": str(uuid4())}
            other = {"X-Chat-Session-Id": str(uuid4())}
            with TestClient(app) as client:
                for path in (
                    "/health",
                    "/models",
                    "/runtime-summary",
                    "/pipeline-info",
                    "/openapi.json",
                    "/docs",
                    "/redoc",
                ):
                    self.assertEqual(client.get(path).status_code, 200, path)
                runtime = client.get("/runtime-summary").json()
                self.assertEqual(runtime["embedding_chunk_tokens"], 224)
                self.assertEqual(runtime["embedding_chain_steps"], 0)
                uploaded = client.post(
                    "/upload",
                    headers=headers,
                    files=[("files", ("real.pdf", fixture_pdf(), "application/pdf"))],
                )
                self.assertEqual(uploaded.status_code, 200, uploaded.text)
                self.assertTrue(client.get("/status", headers=headers).json()["pdf_loaded"])
                self.assertFalse(client.get("/status", headers=other).json()["pdf_loaded"])
                answer = client.post(
                    "/ask", headers=headers, json={"question": "What accuracy was measured?"}
                )
                self.assertEqual(answer.status_code, 200, answer.text)
                self.assertIn("91%", answer.json()["answer"])
                stream = client.post(
                    "/ask/stream", headers=headers, json={"question": "What accuracy was measured?"}
                )
                self.assertIn("event: done", stream.text)
                self.assertNotIn("event: error", stream.text)
                found = client.post(
                    "/api/papers/search", headers=headers, json={"query": "retrieval evaluation"}
                ).json()
                ids = [paper["id"] for paper in found["papers"][:2]]
                data = {"topic": "retrieval evaluation", "paper_ids": json.dumps(ids)}
                report = client.post(
                    "/api/analyze/stream",
                    headers=headers,
                    data=data,
                    files=[("files", ("mixed.pdf", fixture_pdf(), "application/pdf"))],
                )
                self.assertIn("event: done", report.text, report.text)
                self.assertNotIn("event: error", report.text)
                self.assertIn("Literature Summary", report.text)
                followup = client.post(
                    "/api/chat/followup",
                    headers=headers,
                    json={"question": "What accuracy did they measure?"},
                )
                self.assertEqual(followup.status_code, 200, followup.text)
                self.assertIn("91%", followup.json()["answer"])
                from app.routes.gap_analyzer import sessions

                engine = sessions.get(headers["X-Chat-Session-Id"]).engine
                self.assertTrue(engine._history)
                regenerated = client.post(
                    "/api/analyze/gaps", headers=headers, json={"topic": "retrieval evaluation"}
                )
                self.assertEqual(regenerated.status_code, 200, regenerated.text)
                self.assertEqual(engine._history, [])
                client.post(
                    "/api/chat/followup",
                    headers=headers,
                    json={"question": "What accuracy did they measure?"},
                )
                self.assertTrue(engine._history)
                self.assertEqual(
                    client.delete("/api/chat/followup", headers=headers).status_code, 200
                )
                self.assertEqual(engine._history, [])
                self.assertEqual(
                    client.post(
                        "/api/chat/followup", headers=other, json={"question": "What accuracy?"}
                    ).status_code,
                    400,
                )
                ingested = client.post(
                    "/api/papers/ingest",
                    headers=headers,
                    json={"fetched_papers": [{"id": paper_id} for paper_id in ids]},
                )
                self.assertEqual(ingested.status_code, 200, ingested.text)
                report_json = client.post(
                    "/api/analyze/gaps", headers=headers, json={"topic": "retrieval evaluation"}
                )
                self.assertEqual(report_json.status_code, 200, report_json.text)
                self.assertIn("Novel Paper Suggestions", report_json.json()["report"])
