"""Regressions for the security audit's cross-user and output-boundary failures."""

import asyncio
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from langchain_core.documents import Document

from app.config import get_settings
from app.main import create_app
from app.services.evidence import format_evidence, ground_answer
from app.services.llm_service import LLMService


class ClaimSupportTests(unittest.TestCase):
    def setUp(self):
        self.docs = [Document(page_content=(
            "The treatment did not improve accuracy. "
            "Accuracy was 40 percent on dataset A and 90 percent on dataset B."
        ))]
        self.citations = format_evidence(self.docs)[1]

    def test_citation_cannot_launder_negation_metric_swaps_or_unrelated_claims(self):
        for claim in (
            "The treatment improved accuracy [E1].",
            "Accuracy was 90 percent on dataset A [E1].",
            "This entirely unrelated claim is proven [E1].",
            "The treatment did not improve accuracy [E1]. It cured all diseases [E1].",
            "# The treatment cured all disease",
            "Insufficient evidence to deny that the treatment cured all disease.",
        ):
            with self.subTest(claim=claim):
                self.assertRegex(ground_answer(claim, self.citations, self.docs),
                                 r"^I cannot (verify|provide a grounded answer)")

    def test_supported_sentences_preserve_negation_conditions_and_numeric_formatting(self):
        answer = ("The treatment did not improve accuracy [E1]. "
                  "Accuracy was 40% on dataset A and 90% on dataset B [E1].")
        self.assertNotIn("cannot", ground_answer(answer, self.citations, self.docs))

    def test_each_sentence_must_use_its_own_supporting_citation(self):
        docs = [Document(page_content="Dataset A measured 40% accuracy."),
                Document(page_content="Dataset B measured 90% accuracy.")]
        citations = format_evidence(docs)[1]
        answer = "Dataset A measured 40% accuracy [E2]. Dataset B measured 90% accuracy [E1]."
        self.assertIn("cannot verify", ground_answer(answer, citations, docs))
        uncited = "Dataset A measured 40% accuracy. Dataset B measured 90% accuracy [E2]."
        self.assertIn("cannot verify", ground_answer(uncited, citations, docs))

    def test_metadata_only_cannot_establish_factual_source_content(self):
        docs = [Document(page_content="A treatment cured all disease.",
                         metadata={"evidence_scope": "metadata_only"})]
        self.assertIn("cannot verify", ground_answer(
            "A treatment cured all disease [E1].", format_evidence(docs)[1], docs))

    def test_unit_case_and_leading_negative_sign_cannot_be_normalized_away(self):
        docs = [Document(page_content="Mass was 1 mg. Another mass was 1 Mg. -40% change was observed. A baseline was 40%.")]
        citations = format_evidence(docs)[1]
        for claim in ("Mass was 1 Mg [E1].", "40% change was observed [E1]."):
            self.assertIn("cannot verify", ground_answer(claim, citations, docs))


class OutputBoundaryTests(unittest.TestCase):
    def test_rejected_raw_tokens_never_leave_chat_service(self):
        service = LLMService()

        async def provider(*args):
            yield {"type": "token", "content": "Untrusted raw claim."}
            yield {"type": "complete", "answer": "Untrusted raw claim.", "model_used": "fixture"}

        async def run():
            with patch.object(service, "stream_text", provider):
                return [event async for event in service.stream_answer_with_failover(
                    "question", [Document(page_content="The source says something else.")])]

        events = asyncio.run(run())
        self.assertNotIn("Untrusted raw claim", str(events))
        self.assertIn("cannot provide a grounded answer", events[-1]["answer"])
        self.assertEqual(events[0]["content"], events[-1]["answer"])

    def test_incomplete_provider_stream_fails_without_releasing_text(self):
        service = LLMService()

        async def provider(*args):
            yield {"type": "token", "content": "Raw partial answer"}

        async def run():
            events = []
            with patch.object(service, "stream_text", provider):
                with self.assertRaisesRegex(RuntimeError, "interrupted"):
                    async for event in service.stream_answer_with_failover(
                        "q", [Document(page_content="Source sentence.")]):
                        events.append(event)
            self.assertEqual(events, [])

        asyncio.run(run())

    def test_provider_failure_logs_do_not_contain_exception_payloads(self):
        from app.config import AI_PROVIDERS

        with self.assertLogs("app.services.llm_service", level="WARNING") as logs:
            LLMService._failure(AI_PROVIDERS["gemini"], "fixture", "signature",
                                RuntimeError("PRIVATE_DOCUMENT API_SECRET"))
        self.assertNotIn("PRIVATE_DOCUMENT", str(logs.output))
        self.assertNotIn("API_SECRET", str(logs.output))


class OriginAndLauncherTests(unittest.TestCase):
    def test_dependency_audit_rejects_inherited_system_packages(self):
        from scripts import audit_core

        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "pyvenv.cfg").write_text("include-system-site-packages = true\n")
            with patch.object(audit_core.sys, "prefix", directory):
                with self.assertRaisesRegex(SystemExit, "isolated virtual environment"):
                    audit_core.installed_profile()

    def test_wildcard_host_pattern_cannot_silently_enable_global_cors(self):
        with patch.object(get_settings(), "cors_origins_csv", "https://*.pages.dev"):
            with self.assertRaisesRegex(ValueError, "exact origins"):
                create_app()

    def test_cors_allows_only_configured_origins(self):
        with patch.object(get_settings(), "cors_origins_csv", "https://trusted.example"):
            client = TestClient(create_app())
        for origin, status in (("https://trusted.example", 200),
                               ("https://untrusted-audit.pages.dev", 400),
                               ("https://untrusted-audit.vercel.app", 400)):
            with self.subTest(origin=origin):
                response = client.options("/api/papers/search", headers={
                    "Origin": origin, "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,x-chat-session-id"})
                self.assertEqual(response.status_code, status)
                self.assertNotIn("access-control-allow-credentials", response.headers)
                if status == 400:
                    self.assertNotIn("access-control-allow-origin", response.headers)

    def test_legacy_launcher_delegates_to_session_isolated_application(self):
        import backend.main as legacy
        from backend.app.main import app as supported

        self.assertIs(legacy.app, supported)
        self.assertFalse(hasattr(legacy, "qa_chain"))
        self.assertFalse(hasattr(legacy, "vectorstore"))


@unittest.skipUnless(importlib.util.find_spec("gradio"), "Optional Gradio profile is not installed")
class GradioSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {"GRADIO_ANALYTICS_ENABLED": "False"}):
            import gradio_app
        cls.ui = gradio_app

    def test_independent_browser_sessions_have_different_index_capabilities(self):
        import gradio as gr
        from gradio.state_holder import SessionState

        states = [block for block in self.ui.demo.blocks.values() if isinstance(block, gr.State)]
        state = states[0]
        first, second = SessionState(self.ui.demo), SessionState(self.ui.demo)
        a, b = first[state._id], second[state._id]
        self.assertNotEqual(a, b)
        self.assertEqual(a, first[state._id])
        from langchain_core.embeddings import Embeddings
        from app.services.session_vector_registry import SessionVectorRegistry
        from app.services.vector_store import VectorStoreService

        class FixedEmbeddings(Embeddings):
            def embed_documents(self, texts):
                return [[1.0, float(len(text))] for text in texts]

            def embed_query(self, text):
                return [1.0, float(len(text))]

        with tempfile.TemporaryDirectory() as directory, \
             patch.object(VectorStoreService, "sessions_directory", return_value=directory), \
             patch.object(get_settings(), "embedding_use_remote", False), \
             patch("app.services.vector_store.get_local_embeddings", return_value=FixedEmbeddings()):
            registry = SessionVectorRegistry(4)
            one = registry.activate(registry.get_or_create(a))
            two = registry.activate(registry.get_or_create(b))
            one.create_from_documents([Document(page_content="Private source A")])
            two.create_from_documents([Document(page_content="Private source B")])
            self.assertEqual(registry.get_or_create(a).similarity_search("source")[0].page_content,
                             "Private source A")
            self.assertEqual(registry.get_or_create(b).similarity_search("source")[0].page_content,
                             "Private source B")

    def test_oversized_file_is_rejected_without_reading_its_content(self):
        reader = MagicMock()
        reader.__enter__.return_value = reader
        with patch("builtins.open", return_value=reader), patch.object(
            self.ui.os, "fstat", return_value=SimpleNamespace(st_size=self.ui.settings.max_file_size + 1)
        ), patch.object(self.ui.pdf_processor, "process_uploaded_file") as process:
            result = self.ui.upload_pdf_files(["large.pdf"], str(uuid4()))
        reader.read.assert_not_called()
        process.assert_not_called()
        self.assertEqual(result[-1]["status"], "error")

    def test_upload_activates_session_registry_and_reads_only_remaining_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "small.pdf"
            source.write_bytes(b"%PDF-fixture")
            processed = SimpleNamespace(chunks=[Document(page_content="Source sentence.")],
                                        total_pages=1, total_chunks=1)
            with patch.object(self.ui.pdf_processor, "process_uploaded_file", return_value=processed), \
                 patch.object(self.ui, "vector_registry") as registry, \
                 patch.object(self.ui, "increment_pdf_uploads"):
                result = self.ui.upload_pdf_files([str(source)], str(uuid4()))
            self.assertEqual(result[-1]["status"], "success")
            registry.activate.assert_called_once_with(registry.get_or_create.return_value)

    def test_gradio_uses_grounded_completion_and_fails_on_missing_completion(self):
        class Pipeline:
            def __init__(self, *args):
                self.retrieval_k = 4
                (self.extractor, self.analyzer, self.preprocessor, self.optimizer,
                 self.validator, self.assembler) = range(6)

            def _step(self, agent, value, context, results):
                if agent == self.optimizer:
                    value = ("q", [])
                elif agent == self.assembler:
                    value = {"answer": value, "sources": []}
                elif agent != self.validator:
                    value = []
                return True, value, 0, None

        async def run(complete):
            async def provider(**kwargs):
                yield {"type": "token", "content": "Old raw answer."}
                if complete:
                    yield {"type": "complete", "answer": "Grounded final answer.", "model_used": "fixture"}
            with patch.object(self.ui, "AgentPipeline", Pipeline), \
                 patch.object(self.ui, "vector_registry") as registry, \
                 patch.object(self.ui.llm_service, "stream_answer_with_failover", provider), \
                 patch.object(self.ui, "increment_chat_completions"):
                registry.get_or_create.return_value.is_ready = True
                return [event async for event in self.ui._stream_chat_response_pairs(
                    "q", self.ui.ALL_MODEL_CHOICES[0], "Strict", False, [], str(uuid4()))]

        self.assertEqual(asyncio.run(run(True))[-1][0][-1][1], "Grounded final answer.")
        self.assertNotIn("Old raw answer", asyncio.run(run(False))[-1][0][-1][1])


if __name__ == "__main__":
    unittest.main()
