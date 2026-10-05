"""Offline regression tests for isolation, grounding contracts and API abuse controls."""
import asyncio
import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage, AIMessageChunk
from starlette.requests import Request

from app.agents.pipeline import AgentPipeline
from app.config import AI_PROVIDERS, get_settings
from app.models.schemas import QuestionRequest
from app.routes import gap_analyzer as routes
from app.services.evidence import fit_evidence, format_evidence, resolve_citations, token_count, ground_answer
from app.services.gap_analyzer_engine import GapAnalyzerEngine
from app.services.ip_rate_limit import client_ip
from app.services.llm_service import LLMService, UsageLogger, _cooldowns
from app.services.research_sessions import ResearchSessionRegistry
from app.services.safe_download import download_pdf, public_addresses
from app.services.vector_store import VectorStoreService


class FixedEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[float(len(text)), 1.0] for text in texts]

    def embed_query(self, text):
        return [float(len(text)), 1.0]


class GroundingTests(unittest.TestCase):
    def test_modes_default_to_strict_and_cannot_conflict(self):
        self.assertFalse(QuestionRequest(question="test").hybrid_mode)
        self.assertTrue(QuestionRequest(question="test", knowledge_mode="hybrid").hybrid_mode)
        with self.assertRaises(ValueError):
            QuestionRequest(question="test", knowledge_mode="strict", hybrid_mode=True)
        with self.assertRaises(ValueError):
            QuestionRequest(question="   ")

    def test_pipeline_propagates_mode_and_four_value_result(self):
        vector = MagicMock()
        vector.similarity_search.return_value = [Document(page_content="The measured accuracy was 91 percent on the held-out evaluation dataset.", metadata={"source_file": "A.pdf", "page": 0})]
        llm = MagicMock()
        llm.generate_answer.return_value = ("Accuracy was 91 percent [A.pdf - Page 1]", "fake", 0.2, ["test warning"])
        result = AgentPipeline(vector, llm).run("What accuracy was measured?", include_sources=True, hybrid_mode=False)
        self.assertTrue(result.success, result.error)
        self.assertFalse(llm.generate_answer.call_args.kwargs["hybrid_mode"])
        self.assertEqual(result.context["warnings"], ["test warning"])
        self.assertEqual(result.sources, ["[A.pdf - Page 1]"])

    def test_budget_skips_oversized_passage_without_truncating_evidence(self):
        large = Document(page_content="large " * 3000)
        small = Document(page_content="The final result is 42 percent.")
        self.assertEqual(fit_evidence([large, small], 100), [small])
        self.assertEqual(small.page_content, "The final result is 42 percent.")

    def test_invalid_and_missing_citations_fail_closed(self):
        self.assertIn("cannot verify", ground_answer("A fabricated result [E999]", {"E1": "[Paper]"}))
        self.assertIn("did not cite", ground_answer("The model achieved 99%", {"E1": "[Paper]"}))
        self.assertEqual(ground_answer("Insufficient evidence", {}), "Insufficient evidence")

    def test_formatted_evidence_fits_actual_local_token_budget(self):
        docs = [Document(page_content="Evidence " * 50, metadata={"paper_title": "A scientific paper", "page": i}) for i in range(10)]
        kept = fit_evidence(docs, 200)
        self.assertLessEqual(token_count(format_evidence(kept)[0]), 200)

    def test_same_prefix_different_facts_are_not_deduplicated(self):
        prefix = "Shared scientific introduction. " * 5
        docs = [Document(page_content=prefix + ending) for ending in ("Result 42.", "Result 93.")]
        self.assertEqual(len(fit_evidence(docs, 1000)), 2)

    def test_citations_resolve_only_supplied_ids_and_keep_provenance(self):
        doc = Document(page_content="Accuracy 91%.", metadata={"paper_title": "Study A", "paper_id": "a", "year": "2026", "page": 2, "source": "https://example.org/paper", "evidence_scope": "abstract_only"})
        text, citations = format_evidence([doc])
        self.assertIn("Study A", text)
        self.assertIn("abstract_only", text)
        self.assertNotIn("https://", text)
        answer = resolve_citations("Result [E1], other [E999].", citations)
        self.assertIn("[Study A - Page 3](https://example.org/paper)", answer)
        self.assertIn("[unverified source]", answer)

    def test_no_evidence_makes_no_api_call(self):
        service = LLMService()
        with patch.object(service, "generate_text") as generate:
            answer, used, _, _ = service.generate_answer("Invent a result", [])
        generate.assert_not_called()
        self.assertEqual(used, "none")
        self.assertIn("sufficient evidence", answer)

    def test_gap_cache_is_per_engine_and_keeps_full_passages(self):
        doc = Document(page_content="important evidence " * 45, metadata={"paper_title": "Paper", "paper_id": "p"})
        first, other = GapAnalyzerEngine(), GapAnalyzerEngine()
        for engine in (first, other):
            engine.llm = MagicMock()
            engine.llm.generate_text.return_value = ("Result [E1]", "fake", [])
        for _ in range(2):
            first._cached_generate("system", "question", [doc], "model", "test", 100)
        first.llm.generate_text.assert_called_once()
        self.assertIn(doc.page_content, first.llm.generate_text.call_args.args[2])
        other._cached_generate("system", "question", [doc], "model", "test", 100)
        other.llm.generate_text.assert_called_once()

    def test_report_uses_one_generation_and_does_not_retry_formatting(self):
        engine = GapAnalyzerEngine()
        engine.vector_store = object()
        engine._report_documents = MagicMock(return_value=[Document(page_content="An abstract", metadata={"evidence_scope": "abstract_only"})])
        engine.llm = MagicMock()
        engine.llm.generate_text.return_value = ("Insufficient evidence [E1]", "fake", [])
        report = engine.generate_gap_report("topic")
        engine.llm.generate_text.assert_called_once()
        self.assertIn("abstracts only", report)


class ProviderTests(unittest.TestCase):
    def setUp(self):
        _cooldowns.clear()
        self.service = LLMService()
        self.service.settings = get_settings().model_copy(update={"llm_max_attempts": 2})
        self.provider = AI_PROVIDERS["gemini"]

    def test_attempts_include_keys_in_the_same_total_budget(self):
        with patch.object(self.service, "_llm_attempt_sequence", return_value=[(self.provider, "m1"), (self.provider, "m2")]), patch.object(self.service, "_resolve_llm_api_keys", return_value=["key1", "key2", "key3"]):
            attempts = list(self.service._attempts("m1"))
        self.assertEqual(len(attempts), 2)
        self.assertEqual([a[-1] for a in attempts], [1, 2])

    def test_strict_system_role_and_output_cap(self):
        response = AIMessage(content="Measured result [E1]", response_metadata={})
        llm = MagicMock()
        llm.invoke.return_value = response
        attempt = (self.provider, "fake", "test-key", 1.0, "signature", 1)
        with patch.object(self.service, "_attempts", return_value=iter([attempt])), patch.object(self.service, "_build_llm_with_key", return_value=llm) as build:
            answer, _, _, _ = self.service.generate_answer("q", [Document(page_content="Measured result")], hybrid_mode=False)
        messages = llm.invoke.call_args.args[0]
        self.assertEqual(messages[0].type, "system")
        self.assertIn("only supplied evidence", messages[0].content)
        self.assertEqual(build.call_args.args[3], self.service.settings.followup_max_tokens)
        self.assertIn("Document", answer)

    def test_partial_stream_does_not_append_another_model_answer(self):
        class BrokenLLM:
            async def astream(self, *args, **kwargs):
                yield AIMessageChunk(content="partial")
                raise RuntimeError("network failure")
        async def run():
            events = []
            attempts = [(self.provider, "one", "key", 1.0, "sig", 1), (self.provider, "two", "key", 1.0, "sig", 2)]
            with patch.object(self.service, "_attempts", return_value=iter(attempts)), patch.object(self.service, "_build_llm_with_key", return_value=BrokenLLM()) as build:
                with self.assertRaisesRegex(RuntimeError, "interrupted"):
                    async for event in self.service.stream_answer_with_failover("q", [Document(page_content="Evidence")]):
                        events.append(event)
                self.assertEqual(build.call_count, 1)
            return events
        events = asyncio.run(run())
        self.assertEqual([e["content"] for e in events if e["type"] == "token"], ["partial"])

    def test_usage_logging_contains_real_usage_without_prompt_text(self):
        callback = UsageLogger("test", "provider", "model", 1)
        message = AIMessage(content="private paper text", usage_metadata={"input_tokens": 23, "output_tokens": 7, "total_tokens": 30})
        response = SimpleNamespace(generations=[[SimpleNamespace(message=message)]], llm_output={})
        with self.assertLogs("app.services.llm_service", level="INFO") as logs:
            callback.on_llm_end(response)
        self.assertIn('"input_tokens": 23', logs.output[0])
        self.assertNotIn("private paper text", logs.output[0])


class DownloadTests(unittest.TestCase):
    def test_public_resolution_rejects_private_and_mixed_results(self):
        for addresses in (["127.0.0.1"], ["169.254.169.254"], ["::1"], ["93.184.216.34", "10.0.0.1"]):
            rows = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443)) for address in addresses]
            with patch("app.services.safe_download.socket.getaddrinfo", return_value=rows), self.assertRaises(ValueError):
                public_addresses("host", 443)

    def test_url_rejects_credentials_and_nonstandard_ports(self):
        for url in ("file:///etc/passwd", "http://user:password@example.org/file", "https://example.org:8443/file"):
            with self.assertRaises(ValueError):
                download_pdf(url)

    def test_missing_length_cannot_bypass_byte_limit_and_connection_closes(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 200
        response.getheader.return_value = None
        response.read.return_value = b"%PDF-" + b"x" * 30
        with patch("app.services.safe_download.public_addresses", return_value=["93.184.216.34"]), patch("app.services.safe_download.http.client.HTTPSConnection", return_value=connection):
            with self.assertRaisesRegex(ValueError, "size limit"):
                download_pdf("https://example.org/paper", max_bytes=20)
        connection.close.assert_called_once()

    def test_redirect_destination_is_revalidated(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 302
        response.getheader.return_value = "http://127.0.0.1/private"
        with patch("app.services.safe_download.public_addresses", side_effect=[["93.184.216.34"], ValueError("private")]) as validate, patch("app.services.safe_download.http.client.HTTPSConnection", return_value=connection):
            with self.assertRaises(ValueError):
                download_pdf("https://example.org/paper")
        self.assertEqual(validate.call_args.args[0], "127.0.0.1")

    def test_validated_address_is_used_for_connection(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 200
        response.getheader.return_value = None
        response.read.side_effect = [b"%PDF-data", b""]
        with patch("app.services.safe_download.public_addresses", return_value=["93.184.216.34"]), patch("app.services.safe_download.http.client.HTTPSConnection", return_value=connection), patch("app.services.safe_download.socket.create_connection") as connect:
            self.assertEqual(download_pdf("https://example.org/paper"), b"%PDF-data")
            connection._create_connection(("attacker", 443))
            self.assertEqual(connect.call_args.args[0], ("93.184.216.34", 443))

    def test_untrusted_proxy_headers_do_not_override_client_address(self):
        request = Request({"type": "http", "headers": [(b"x-real-ip", b"1.2.3.4")], "client": ("10.0.0.5", 123)})
        with patch("app.services.ip_rate_limit.get_settings", return_value=SimpleNamespace(trusted_proxy_ips="")):
            self.assertEqual(client_ip(request), "10.0.0.5")
        with patch("app.services.ip_rate_limit.get_settings", return_value=SimpleNamespace(trusted_proxy_ips="10.0.0.0/24")):
            self.assertEqual(client_ip(request), "1.2.3.4")


class SessionRouteTests(unittest.TestCase):
    def setUp(self):
        self.registry_patch = patch.object(routes, "sessions", ResearchSessionRegistry())
        self.registry_patch.start()
        self.addCleanup(self.registry_patch.stop)
        app = FastAPI()
        app.include_router(routes.router)
        self.client = TestClient(app)
        self.a = {"X-Chat-Session-Id": str(uuid4())}
        self.b = {"X-Chat-Session-Id": str(uuid4())}

    def test_session_required_and_another_session_cannot_use_engine(self):
        self.assertEqual(self.client.post("/api/papers/search", json={"query": "test"}).status_code, 400)
        engine = MagicMock()
        engine.generate_gap_report.return_value = "private A result"
        routes.sessions.get(self.a["X-Chat-Session-Id"]).engine = engine
        self.assertEqual(self.client.post("/api/analyze/gaps", headers=self.a, json={"topic": "test"}).status_code, 200)
        self.assertEqual(self.client.post("/api/analyze/gaps", headers=self.b, json={"topic": "test"}).status_code, 400)
        self.assertEqual(engine.generate_gap_report.call_count, 1)

    def test_ingestion_ignores_client_metadata_and_rejects_unknown_ids(self):
        trusted = {"id": "server-paper", "title": "Trusted title", "pdf_url": "https://example.org/paper.pdf"}
        session = routes.sessions.get(self.a["X-Chat-Session-Id"])
        session.papers[trusted["id"]] = trusted
        engine = MagicMock()
        engine.process_and_index_papers.return_value = 2
        with patch.object(routes.fetcher, "download_and_extract_text", return_value="Trusted text") as download, patch.object(routes, "GapAnalyzerEngine", return_value=engine):
            response = self.client.post("/api/papers/ingest", headers=self.a, json={"fetched_papers": [{"id": "server-paper", "pdf_url": "http://127.0.0.1/private", "abstract": "poisoned"}]})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(download.call_args.args[0], trusted)
            self.assertEqual(self.client.post("/api/papers/ingest", headers=self.b, json={"fetched_papers": [{"id": "server-paper"}]}).status_code, 400)
            self.assertEqual(download.call_count, 1)

    def test_failed_ingest_keeps_previous_engine(self):
        session = routes.sessions.get(self.a["X-Chat-Session-Id"])
        old = session.engine = MagicMock()
        session.papers["paper"] = {"id": "paper"}
        with patch.object(routes.fetcher, "download_and_extract_text", side_effect=RuntimeError("private diagnostic")):
            response = self.client.post("/api/papers/ingest", headers=self.a, json={"fetched_papers": [{"id": "paper"}]})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private diagnostic", response.text)
        self.assertIs(session.engine, old)

    def test_inputs_are_bounded_and_caller_keys_are_rejected(self):
        for payload in ({"query": "x", "limit_per_source": 100000}, {"query": " "}):
            self.assertEqual(self.client.post("/api/papers/search", headers=self.a, json=payload).status_code, 422)
        self.assertEqual(self.client.post("/api/analyze/gaps", headers=self.a, json={"topic": "q", "api_key": "caller-secret"}).status_code, 422)

    def test_all_research_routes_have_rate_limits(self):
        for route in routes.router.routes:
            dependencies = [dependency.call.__name__ for dependency in route.dependant.dependencies]
            self.assertTrue(any(name in dependencies for name in ("check_ask_rate_limit", "check_upload_rate_limit")))


class RequestLimitTests(unittest.TestCase):
    def test_body_limit_including_requests_without_content_length(self):
        from fastapi import Request
        from app.services.body_limits import BodyLimitMiddleware
        app = FastAPI()
        app.add_middleware(BodyLimitMiddleware)
        @app.post("/body")
        async def body(request: Request):
            return {"bytes": len(await request.body())}
        client = TestClient(app)
        self.assertEqual(client.post("/body", content=b"x" * 140000).status_code, 413)
        self.assertEqual(client.post("/body", content=iter([b"x" * 70000, b"x" * 70000])).status_code, 413)
        self.assertEqual(client.post("/body", content=b"ok").status_code, 200)

    def test_capacity_is_held_by_asgi_until_response_finishes(self):
        from threading import BoundedSemaphore
        from app.services.body_limits import BodyLimitMiddleware
        app = FastAPI()
        app.add_middleware(BodyLimitMiddleware)
        @app.post("/ask")
        async def answer():
            return {"answer": "ok"}
        client = TestClient(app)
        slots = BoundedSemaphore(1)
        with patch("app.services.request_limits._slots", return_value=slots):
            slots.acquire()
            self.assertEqual(client.post("/ask").status_code, 429)
            slots.release()
            self.assertEqual(client.post("/ask").status_code, 200)
            self.assertTrue(slots.acquire(blocking=False))
            slots.release()

    def test_telemetry_write_failure_does_not_discard_successful_work(self):
        from app.services.usage_counters import increment_chat_completions
        with patch("app.services.usage_counters._counter_path", side_effect=PermissionError("readonly")):
            increment_chat_completions()


class PersistenceTests(unittest.TestCase):
    def test_unknown_read_sessions_cannot_evict_uploaded_documents(self):
        from app.services.session_vector_registry import SessionVectorRegistry
        registry = SessionVectorRegistry(4)
        existing = MagicMock()
        existing.session_id = str(uuid4())
        registry.activate(existing)
        with patch("app.services.session_vector_registry.VectorStoreService") as cls:
            cls.return_value.is_ready = False
            for _ in range(10):
                registry.get_or_create(str(uuid4()))
        self.assertEqual(len(registry._stores), 1)
        existing.discard_persisted_index_if_idle.assert_not_called()

    def test_json_docstore_roundtrip_without_pickle(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(VectorStoreService, "disk_path_for_session", return_value=directory), patch.object(VectorStoreService, "_make_local_cpu_embeddings", return_value=FixedEmbeddings()):
            first = VectorStoreService(str(uuid4()))
            first.settings = get_settings().model_copy(update={"embedding_use_remote": False})
            first.create_from_documents([Document(page_content="Paper evidence", metadata={"page": 0, "source_file": "paper.pdf"})])
            self.assertFalse((Path(directory) / "index.pkl").exists())
            loaded = VectorStoreService(str(uuid4()))
            self.assertTrue(loaded.is_ready)
            self.assertEqual(loaded.similarity_search("question")[0].page_content, "Paper evidence")
            manifest = json.loads((Path(directory) / "metadata.json").read_text())
            self.assertEqual(manifest["embedding"]["provider"], "local")
            manifest["index_sha256"] = "tampered"
            (Path(directory) / "metadata.json").write_text(json.dumps(manifest))
            self.assertFalse(VectorStoreService(str(uuid4())).is_ready)


if __name__ == "__main__":
    unittest.main()
