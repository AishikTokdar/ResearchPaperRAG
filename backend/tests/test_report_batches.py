"""Selection-sized generation must preserve citations, depth, and partial results."""

import asyncio
import re
import unittest
from unittest.mock import MagicMock

from langchain_core.documents import Document

from app.config import DEFAULT_MODEL
from app.services.gap_analyzer_engine import REPORT_SECTIONS, GapAnalyzerEngine
from app.services.report_plan import batch_token_budget, section_batches
from app.services.report_presentation import section_bodies

PROSE = ("The selected study evaluates curriculum-grounded retrieval and explains how retrieved "
         "teaching materials support answer generation. Its evaluation compares evidence quality, "
         "relevance, and source attribution. These observations support a focused comparison of "
         "retrieval and generation behavior within the supplied task, while broader deployment "
         "claims require independent investigation using appropriate baselines and assessment criteria.")


def engine_for(count):
    engine = GapAnalyzerEngine()
    docs = [Document(page_content=PROSE, metadata={"paper_id": f"paper-{i}", "paper_title": f"Selected study {i}",
                     "source": f"https://example.org/study-{i}", "evidence_scope": "full_text"}) for i in range(count)]
    engine.documents = docs
    engine.paper_metadata_list = [{"id": doc.metadata["paper_id"]} for doc in docs]
    engine.vector_store = object()
    engine._report_documents = MagicMock(return_value=docs)
    return engine


def response_for(prompt, docs):
    requested = [int(n) for n in re.findall(r"(?m)^## ([1-8])\. ", prompt)]
    return "\n\n".join(
        f"## {n}. {REPORT_SECTIONS[n - 1]}\n\n" + "\n\n".join(
            f"**{doc.metadata['paper_title']}** – {PROSE} [E{i}]." for i, doc in enumerate(docs, 1)
        ) for n in requested
    )


class ReportBatchTests(unittest.TestCase):
    def test_plan_scales_with_selection_and_lower_output_caps(self):
        for count, expected in [(2, 1), (3, 2), (4, 3), (5, 3)]:
            with self.subTest(count=count):
                plan = section_batches(count, 6000)
                self.assertEqual(len(plan), expected)
                self.assertEqual([n for group in plan for n in group], list(range(1, 9)))
                small = section_batches(count, 1024)
                self.assertGreaterEqual(len(small), expected)
                self.assertEqual([n for group in small for n in group], list(range(1, 9)))
                self.assertTrue(all(batch_token_budget(group, 1024) <= 1024 for group in small))

    def test_sync_and_stream_merge_every_selection_once_in_every_section(self):
        for count in range(2, 6):
            with self.subTest(count=count):
                sync = engine_for(count)
                sync.llm.generate_text = MagicMock(side_effect=lambda prompt, *args: (
                    response_for(prompt, sync.documents), DEFAULT_MODEL, []))
                sync_report = sync.generate_gap_report("Any discovery question", "gemini", DEFAULT_MODEL)
                streamed = engine_for(count)
                calls = []

                async def stream(messages, model, feature, budget):
                    calls.append((messages[0].content, budget))
                    answer = response_for(messages[0].content, streamed.documents)
                    yield {"type": "token", "content": answer}
                    yield {"type": "complete", "answer": answer, "model_used": DEFAULT_MODEL, "warnings": []}

                streamed.llm.stream_text = stream

                async def collect():
                    return [event async for event in streamed.stream_gap_report("Any discovery question", "gemini", DEFAULT_MODEL)]

                events = asyncio.run(collect())
                result = events[-1]
                self.assertEqual(sync_report, result["report"])
                self.assertEqual(result["sections_completed"], list(range(1, 9)))
                self.assertFalse(result["limited"])
                self.assertEqual(len(calls), len(section_batches(count, 6000)))
                self.assertEqual(sync.llm.generate_text.call_count, len(calls))
                for _, body in section_bodies(result["report"]).items():
                    for doc in streamed.documents:
                        self.assertEqual(body.count(doc.metadata["source"]), 1)
                for prompt, budget in calls:
                    self.assertIn(f"{count} selected papers", prompt)
                    self.assertLessEqual(budget, 6000)
                self.assertEqual(asyncio.run(collect())[-1]["report"], result["report"])
                self.assertEqual(len(calls), len(section_batches(count, 6000)))
                percentages = [e["percent"] for e in events]
                self.assertEqual(percentages, sorted(percentages))

    def test_later_batch_failure_keeps_prior_completed_sections(self):
        engine = engine_for(5)
        calls = []

        async def stream(messages, *args):
            calls.append(messages)
            if len(calls) > 1:
                raise RuntimeError("private upstream failure")
            yield {"type": "complete", "answer": response_for(messages[0].content, engine.documents), "warnings": []}

        engine.llm.stream_text = stream
        engine.llm.generate_text = MagicMock(side_effect=AssertionError("Do not repair an interrupted report"))

        async def collect():
            return [event async for event in engine.stream_gap_report("A different topic", "gemini", DEFAULT_MODEL)]

        result = asyncio.run(collect())[-1]
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["sections_completed"], [1, 2])
        self.assertTrue(result["limited"])
        self.assertIn("Generation was interrupted", result["report"])
        self.assertNotIn("private upstream", result["report"])
        self.assertFalse(engine._cache)
        engine.llm.generate_text.assert_not_called()

    def test_unrequested_sections_do_not_leak_into_a_generation_part(self):
        engine = engine_for(5)
        entire = response_for(engine._report_prompt(engine.documents), engine.documents)
        result = engine._validated_batch(entire, engine.documents, (3, 4, 5))
        self.assertEqual(list(section_bodies(result)), [3, 4, 5])


if __name__ == "__main__":
    unittest.main()
