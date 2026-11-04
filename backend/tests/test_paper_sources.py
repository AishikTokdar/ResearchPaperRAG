"""Exercise the actual optional SDK adapter without network access."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from app.services.paper_fetcher import PaperFetcher


class PaperSourceTests(unittest.TestCase):
    def test_arxiv_sdk_search_is_installed_and_maps_results(self):
        import arxiv

        paper = SimpleNamespace(
            published=datetime(2026, 1, 1, tzinfo=timezone.utc),
            authors=[SimpleNamespace(name="Test Author")],
            entry_id="https://arxiv.org/abs/2601.00001v1",
            title="Retrieval study",
            summary="Evidence retrieval evaluation.",
            pdf_url="https://arxiv.org/pdf/2601.00001v1",
        )
        with (
            patch.object(arxiv.Client, "results", return_value=iter([paper])),
            patch(
                "app.services.paper_fetcher.requests.get",
                side_effect=AssertionError("Unexpected HTTP fallback"),
            ),
        ):
            results = PaperFetcher().search_arxiv("evidence retrieval", limit=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "arxiv_2601.00001v1")
        self.assertEqual(results[0]["source_api"], "arXiv")
