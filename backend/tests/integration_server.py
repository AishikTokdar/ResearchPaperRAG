"""Local-only integration fixture: real app/parser/FAISS, deterministic external boundaries.

Never use this entrypoint for deployment. No external provider is contacted.
"""

import asyncio
import io
import json
import tempfile
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi import Response
from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage, AIMessageChunk
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def fixture_pdf() -> bytes:
    writer = PdfWriter()
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page = writer.add_blank_page(width=600, height=800)
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    contents = DecodedStreamObject()
    contents.set_data(b"BT /F1 12 Tf 30 700 Td (The evaluated retrieval method measured accuracy of 91% on held-out data.) Tj ET")
    page[NameObject("/Contents")] = contents
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class FixtureEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[float(len(text) % 23), float(len(text.split()) % 19), 1.0] for text in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


class FixtureLLM:
    def answer(self, messages):
        from app.services.gap_analyzer_engine import REPORT_SECTIONS

        evidence = json.loads(messages[-1].content)["untrusted_evidence"]
        assert "91%" in evidence, "Integration fixture lost source evidence"
        if "Literature Summary" in messages[0].content:
            return "\n\n".join(f"## {i}. {title}\nThe evaluated retrieval method measured accuracy of 91% [E1]." for i, title in enumerate(REPORT_SECTIONS, 1))
        return "The evaluated retrieval method measured accuracy of 91% [E1]."

    def invoke(self, messages, **kwargs):
        return AIMessage(content=self.answer(messages))

    async def astream(self, messages, **kwargs):
        for part in self.answer(messages).splitlines(keepends=True):
            await asyncio.sleep(0.02)
            yield AIMessageChunk(content=part)


def fixture_app(stack: ExitStack, directory: Path):
    from app.config import get_settings
    from app.main import create_app
    from app.routes import gap_analyzer
    from app.services.research_sessions import ResearchSessionRegistry

    settings = get_settings()
    for key, value in {"faiss_persist_dir": str(directory), "allowed_hosts": "localhost,127.0.0.1,testserver",
                       "embedding_use_remote": False, "rate_limit_ask_per_minute": 0,
                       "rate_limit_upload_per_minute": 0, "telemetry_tunnel_dsn": None}.items():
        stack.enter_context(patch.object(settings, key, value))
    keys = lambda provider, *args: ["integration-fixture-key"] if provider == "gemini" else []
    for module in ("app.config", "app.services.llm_service", "app.main"):
        stack.enter_context(patch(f"{module}.get_all_provider_api_keys", side_effect=keys))
    stack.enter_context(patch("app.services.llm_service.LLMService._build_llm_with_key", return_value=FixtureLLM()))
    for module in ("app.services.vector_store", "app.services.gap_analyzer_engine"):
        stack.enter_context(patch(f"{module}.get_local_embeddings", return_value=FixtureEmbeddings()))
    stack.enter_context(patch.object(gap_analyzer, "sessions", ResearchSessionRegistry()))
    pdf = fixture_pdf()
    papers = [{"id": f"fixture-{i}", "title": f"Retrieval evaluation study {i}", "authors": "Fixture author",
               "year": str(datetime.now(UTC).year), "source_api": "arXiv", "abstract": "The retrieval method measured accuracy of 91%.",
               "url": f"https://example.org/study/{i}", "pdf_url": f"https://example.org/study/{i}.pdf",
               "is_open_access": True} for i in range(1, 6)]

    def search(query, limit_per_source=3, source_status=None):
        if source_status is not None:
            source_status.append({"source": "arXiv", "status": "ok", "count": len(papers)})
        return [dict(paper) for paper in papers]

    stack.enter_context(patch("app.services.paper_fetcher.PaperFetcher.search_all", side_effect=search))
    stack.enter_context(patch("app.services.paper_fetcher.download_pdf", return_value=pdf))
    app = create_app()

    @app.get("/__test__/pdf", include_in_schema=False)
    def pdf_fixture():
        return Response(content=pdf, media_type="application/pdf")

    return app


if __name__ == "__main__":
    import uvicorn

    with tempfile.TemporaryDirectory(prefix="research-rag-integration-") as temporary, ExitStack() as stack:
        app = fixture_app(stack, Path(temporary))
        uvicorn.run(app, host="127.0.0.1", port=8999, proxy_headers=False)
