"""Catalog consistency, free-only failover, and current SDK wire compatibility."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import AI_PROVIDERS, MODEL_CATALOG, Settings, provider_is_allowed
from app.services.gap_analyzer_engine import GapAnalyzerEngine
from app.services.llm_service import LLMService


class CatalogTests(unittest.TestCase):
    def test_frontend_catalog_matches_server_and_has_unambiguous_ids(self):
        root = Path(__file__).resolve().parents[2]
        frontend = json.loads((root / "frontend/src/lib/model-catalog.json").read_text())
        self.assertEqual(frontend, MODEL_CATALOG)
        ids = [model for provider in AI_PROVIDERS.values() for model in provider.models]
        self.assertEqual(len(ids), len(set(ids)))
        settings = Settings(_env_file=None)
        self.assertIn(settings.default_model, AI_PROVIDERS[settings.default_provider].models)
        self.assertFalse(any("safeguard" in model or "mixtral" in model for model in ids))
        self.assertTrue(all(model.endswith(":free") or model == "openrouter/free"
                            for model in AI_PROVIDERS["openrouter"].models))

    def test_existing_retired_default_is_migrated_without_editing_environment(self):
        settings = Settings(_env_file=None, default_provider="gemini", default_model="gemini-3.6-flash")
        self.assertEqual(settings.default_model, "gemini-3.8-flash")

    def test_all_catalog_providers_are_free_tier(self):
        settings = Settings(_env_file=None)
        service = LLMService()
        with patch("app.config.get_settings", return_value=settings), patch(
            "app.services.llm_service.get_all_provider_api_keys", return_value=["test-key"]
        ):
            sequence = service._llm_attempt_sequence(settings.default_model)
            self.assertEqual({p.name for p, _ in sequence}, {"gemini", "groq", "sambanova", "openrouter"})
        for p in AI_PROVIDERS.values():
            self.assertEqual(p.access_tier, "free")
            self.assertTrue(provider_is_allowed(p))

    def test_latest_sdk_serializes_grounded_chat_without_real_network(self):
        captured = []
        def respond(request):
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "test", "object": "chat.completion", "created": 1,
                "model": "gemini-3.8-flash",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "Supported [E1]"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            })
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            def build(**kwargs):
                return ChatOpenAI(**kwargs, http_client=client)
            with patch("app.services.llm_service.ChatOpenAI", side_effect=build):
                llm = LLMService()._build_llm_with_key(AI_PROVIDERS["gemini"], "gemini-3.8-flash", "test-key", 800)
                result = llm.invoke([SystemMessage(content="Use evidence only."), HumanMessage(content="[E1] Evidence")])
        self.assertEqual(result.content, "Supported [E1]")
        self.assertEqual(captured[0]["model"], "gemini-3.8-flash")
        self.assertEqual(captured[0]["messages"][0]["role"], "system")
        self.assertEqual(captured[0]["reasoning_effort"], "low")
        self.assertNotIn("temperature", captured[0])
        self.assertEqual(captured[0].get("max_completion_tokens", captured[0].get("max_tokens")), 800)
