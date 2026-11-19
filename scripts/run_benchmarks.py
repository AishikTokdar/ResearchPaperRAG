#!/usr/bin/env python3
"""
Production-Grade High-Impact Benchmark Suite for ResearchPaperRAG.

Evaluates 8 core architectural pillars of the system under authentic scientific
RAG workloads:
1. Document Ingestion & Tokenizer-Aware Semantic Chunking Pipeline
2. Lexical BM25 Retrieval Engine & Reciprocal Rank Fusion
3. Evidence Token Budgeting, Fitting & Packing Algorithm
4. Deterministic Evidence Grounding & Numerical Verification
5. Multi-Agent RAG Orchestration Pipeline (Zero-Network Agent Loop)
6. Literature Search Federation, Deduplication & Relevance Ranking
7. Report Presentation & Speculative Methodology Filter Engine
8. High-Concurrency Sliding-Window Rate Limiting Under Load

Tracks statistical rigor: Min, Mean, Median (p50), p95, p99, Max,
Throughput (ops/sec, tokens/sec, req/sec), Speedup Multipliers, and Latency Reductions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
import time
import unicodedata
from collections import Counter, deque
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

# Ensure backend directory is in path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
from langchain_core.documents import Document

# Domain imports
from app.agents.pipeline import AgentPipeline
from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.analyzer import AnalyzerAgent
from app.agents.preprocessor import PreprocessorAgent
from app.agents.optimizer import OptimizerAgent
from app.agents.validator import ValidatorAgent
from app.agents.assembler import AssemblerAgent
from app.config import get_settings
from app.services import chunking, evidence, hybrid_retrieval, ip_rate_limit, paper_fetcher, report_presentation


@dataclass
class BenchmarkStats:
    pillar_id: str
    name: str
    sample_count: int
    unit: str
    baseline_mean: float
    baseline_p50: float
    baseline_p95: float
    baseline_p99: float
    baseline_min: float
    baseline_max: float
    baseline_throughput: float
    optimized_mean: float
    optimized_p50: float
    optimized_p95: float
    optimized_p99: float
    optimized_min: float
    optimized_max: float
    optimized_throughput: float
    speedup_factor: float
    latency_reduction_pct: float
    throughput_metric: str


# ---------------------------------------------------------------------------
# Synthetic Domain Datasets (Authentic Scientific Workloads)
# ---------------------------------------------------------------------------

SAMPLE_PAPER_TEXT = """
# Scaling Laws for Retrieval-Augmented Language Models in Scientific Synthesis

## Abstract
Retrieval-Augmented Generation (RAG) combines parametric memory with external non-parametric document indices. In this work, we systematically investigate the scaling properties of hybrid lexical and dense retrieval across 15 scientific benchmark datasets. We demonstrate that dense embeddings alone fail on rare chemical nomenclature, resulting in a 24.5% decrease in exact-match recall compared to hybrid retrieval. By integrating Reciprocal Rank Fusion (RRF) with dynamic token-budget packing, our architecture achieves 94.2% grounded accuracy and improves citation precision by 3.8x.

## Introduction
Modern scientific discovery requires processing vast corpora of academic literature. Standard Large Language Models (LLMs) suffer from hallucination when queried about cutting-edge findings or granular experimental metrics. Retrieval-augmented architectures address this by grounding generation in verifiable literature excerpts. However, naively packing retrieved passages into prompt contexts encounters token budget ceilings and quadratic formatting overhead.

## Methods and Materials
Our pipeline utilizes a federated discovery module across arXiv, Crossref, and Semantic Scholar. Harvested documents are segmented using tokenizer-aware recursive splitting with a 224-token window and 32-token overlap. Dense representations are generated using sentence-transformers/all-MiniLM-L6-v2 mapped into an in-memory FAISS index. Lexical scoring computes BM25 relevance across normalized document frequencies with k1=2.5 and b=0.75. Reciprocal rank fusion merges dense and sparse rankings with smoothing constant k=60.

## Results
Across 1,200 evaluation queries, our hybrid pipeline achieved a mean reciprocal rank (MRR) of 0.887, compared to 0.612 for dense-only retrieval and 0.541 for BM25-only baselines. Under strict latency constraints, the incremental token fitting algorithm reduced context packaging latency from 45.2 ms to 3.1 ms, representing a 14.5x acceleration. Numerical claim verification flagged 98.7% of fabricated performance metrics without degrading valid citations.

## Discussion
The empirical findings confirm that hybrid fusion is essential for domain-specific technical literature. Exact keyword matching recovers numerical tolerances, enzyme identifiers, and dataset versions, while dense representations capture semantic intent. Furthermore, deterministic grounding guarantees that every synthesized claim possesses a verifiable evidence identifier.

## Limitations
This study is bounded by local CPU vector indexing constraints. At corpora exceeding 100,000 documents, approximate nearest neighbor quantization (IVF-PQ) is required to sustain sub-10ms retrieval latency. Additionally, parsing heavily formatted mathematical expressions from legacy PDF scans introduces optical character recognition artifacts.

## References
1. Lewis, P., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS 2020.
2. Robertson, S., & Zaragoza, H. (2009). The Probabilistic Relevance Framework: BM25 and Beyond. Information Retrieval, 11(4), 333-389.
3. Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search with GPUs. IEEE Transactions on Big Data, 7(3), 535-547.
"""

SYNTHETIC_PAPERS_CATALOG = [
    {
        "id": f"paper_{i:03d}",
        "title": f"Advancements in Deep Learning for Biomedical RAG Systems Part {i}: Empirical Analysis of Attention Heads",
        "authors": f"Author A. Smith, Researcher B. {i}, Scientist C. {i % 10}",
        "year": str(2022 + (i % 4)),
        "abstract": (
            f"Study {i} investigates transformer architectures applied to scientific synthesis. "
            f"The model demonstrates an improvement of {(12.5 + (i % 20)):.1f}% over classical baselines. "
            f"Using {1000 + i * 50} benchmark samples, precision reached {(85.0 + (i % 15)):.2f}%."
        ),
        "url": f"https://doi.org/10.1000/182_{i}",
        "doi": f"10.1000/182_{i}" if i % 3 != 0 else "",
        "pdf_url": f"https://arxiv.org/pdf/2401.{10000+i}.pdf",
        "evidence_scope": "full_text" if i % 2 == 0 else "abstract_only",
        "source_api": ["arXiv", "Crossref", "Semantic Scholar", "PubMed", "DOAJ", "OpenAlex"][i % 6],
    }
    for i in range(120)
]


def generate_synthetic_documents(count: int = 200) -> list[Document]:
    """Generate realistic academic Document chunks with metadata."""
    docs = []
    topics = [
        "quantum computing error mitigation in superconducting qubits",
        "contrastive learning for multimodal biomedical image segmentation",
        "zero-shot cross-lingual transfer in low-resource speech recognition",
        "graph neural networks for molecular property prediction and drug discovery",
        "retrieval augmented generation with reciprocal rank fusion on scientific corpora",
        "efficient kv cache compression via selective token pruning in long contexts",
        "differential privacy in federated genomic data sharing protocols",
        "reinforcement learning from human feedback with constrained reward models",
    ]
    for i in range(count):
        topic = topics[i % len(topics)]
        content = (
            f"Section {i % 8 + 1}. In this study on {topic}, we evaluate system parameters. "
            f"The experimental pipeline achieves an accuracy of {(78.2 + (i % 20)):.1f}% on test split {i % 5}. "
            f"Prior methods achieved only {(62.1 + (i % 15)):.1f}% under identical evaluation conditions. "
            f"We observe that convergence rate scales logarithmically with parameter count N={1000 * (i + 1)}. "
            f"Hyperparameters include learning rate 0.00{i % 9 + 1}, batch size 64, and weight decay 1e-4."
        )
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "paper_id": f"paper_{i % 30:03d}",
                    "paper_title": f"Scientific Investigation of {topic.title()}",
                    "source": f"https://arxiv.org/abs/2401.{10000 + (i % 30)}",
                    "year": str(2023 + (i % 3)),
                    "page": i % 12,
                    "evidence_scope": "full_text" if i % 2 == 0 else "abstract_only",
                },
            )
        )
    return docs


# ---------------------------------------------------------------------------
# Benchmark Runner Utility
# ---------------------------------------------------------------------------

def calculate_distribution(timings: list[float]) -> dict[str, float]:
    """Calculate statistical distribution metrics from timing array (ms)."""
    arr = np.array(timings)
    return {
        "mean": float(np.mean(arr)),
        "p50": float(np.median(arr)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def run_workload(
    fn: Callable[[], Any],
    iterations: int,
    warmup: int = 10,
) -> list[float]:
    """Execute workload with warmup and return per-iteration latency in ms."""
    for _ in range(warmup):
        fn()
    timings = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        timings.append((t1 - t0) * 1000.0)
    return timings


# ---------------------------------------------------------------------------
# Pillar 1: Document Chunking & Tokenizer Splitting
# ---------------------------------------------------------------------------

def benchmark_pillar_1_chunking(iterations: int = 100) -> tuple[dict[str, float], dict[str, float], float, float]:
    """Benchmark tokenizer-aware semantic document splitting."""
    docs = [Document(page_content=SAMPLE_PAPER_TEXT * 2, metadata={"paper_title": "Scaling Laws"})]

    # Baseline: Uncached splitter instantiation and dynamic regex recompilation per call
    def baseline_fn():
        tokenizer = chunking.embedding_tokenizer()
        splitter = chunking.RecursiveCharacterTextSplitter(
            chunk_size=224,
            chunk_overlap=32,
            length_function=lambda text: len(tokenizer.encode(text, add_special_tokens=False, verbose=False)),
            separators=["\n\n", "\n", ". ", "; ", " ", ""],
        )
        heading_re = re.compile(
            r"(?m)^(?:#{1,3}\s+.+|(?:\d+(?:\.\d+)*\.?\s+)?(?:Abstract|Introduction|Methods?|Materials and Methods|Results|Discussion|Conclusions?|Limitations|References))\s*$",
            re.I,
        )
        sections = []
        for doc in docs:
            matches = list(heading_re.finditer(doc.page_content))
            boundaries = sorted({0, *(m.start() for m in matches), len(doc.page_content)})
            for start, end in zip(boundaries, boundaries[1:], strict=False):
                text = doc.page_content[start:end].strip()
                if text:
                    lines = text.splitlines()
                    meta = dict(doc.metadata)
                    if lines and heading_re.match(lines[0]):
                        meta["section"] = lines[0]
                    sections.append(Document(page_content=text, metadata=meta))
        return splitter.split_documents(sections)

    # Optimized: Using production optimized split_documents
    def optimized_fn():
        return chunking.split_documents(docs, chunk_size=224, overlap=32)

    base_times = run_workload(baseline_fn, iterations, warmup=5)
    opt_times = run_workload(optimized_fn, iterations, warmup=5)

    base_stats = calculate_distribution(base_times)
    opt_stats = calculate_distribution(opt_times)

    tokens_per_op = 1800
    base_tp = (1000.0 / base_stats["mean"]) * tokens_per_op
    opt_tp = (1000.0 / opt_stats["mean"]) * tokens_per_op

    return base_stats, opt_stats, base_tp, opt_tp


# ---------------------------------------------------------------------------
# Pillar 2: Lexical BM25 Retrieval & Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def benchmark_pillar_2_retrieval(iterations: int = 150) -> tuple[dict[str, float], dict[str, float], float, float]:
    """Benchmark BM25 lexical ranking and reciprocal rank fusion."""
    corpus = generate_synthetic_documents(count=200)
    index = hybrid_retrieval.HybridIndex(corpus)
    queries = [
        "quantum computing error mitigation superconducting qubits",
        "multimodal biomedical image segmentation contrastive learning",
        "reciprocal rank fusion hybrid retrieval scientific corpora",
        "kv cache compression selective token pruning long context",
        "reinforcement learning human feedback constrained reward models",
    ]

    # Baseline: Classic O(D * |Q|) document scan with inner-loop log(IDF) recalculation
    counts = [Counter(hybrid_retrieval.words(doc.page_content)) for doc in corpus]
    lengths = [sum(c.values()) for c in counts]
    avg_len = sum(lengths) / max(1, len(corpus))
    freq = Counter()
    for c in counts:
        freq.update(c.keys())

    def baseline_lexical(q: str, k: int = 30) -> list[int]:
        scores = []
        for i, count in enumerate(counts):
            score = 0.0
            for word in set(hybrid_retrieval.words(q)):
                tf = count[word]
                if tf:
                    df = freq[word]
                    idf = math.log(1 + (len(corpus) - df + 0.5) / (df + 0.5))
                    score += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * lengths[i] / avg_len))
            if score > 0:
                scores.append((score, i))
        return [idx for _, idx in sorted(scores, key=lambda pair: (-pair[0], pair[1]))[:k]]

    def baseline_fn():
        q = queries[random.randint(0, len(queries) - 1)]
        return baseline_lexical(q, k=30)

    def optimized_fn():
        q = queries[random.randint(0, len(queries) - 1)]
        return index.lexical(q, k=30)

    base_times = run_workload(baseline_fn, iterations, warmup=10)
    opt_times = run_workload(optimized_fn, iterations, warmup=10)

    base_stats = calculate_distribution(base_times)
    opt_stats = calculate_distribution(opt_times)

    base_tp = 1000.0 / base_stats["mean"]
    opt_tp = 1000.0 / opt_stats["mean"]

    return base_stats, opt_stats, base_tp, opt_tp


# ---------------------------------------------------------------------------
# Pillar 3: Evidence Token Budgeting & Incremental Packing
# ---------------------------------------------------------------------------

def benchmark_pillar_3_evidence_fitting(iterations: int = 100) -> tuple[dict[str, float], dict[str, float], float, float]:
    """Benchmark token budgeting and passage fitting (O(N^2) naive vs O(N) optimized)."""
    docs = generate_synthetic_documents(count=50)
    budget = 4000

    # Baseline: O(N^2) naive cumulative formatting & full-text re-tokenization
    def baseline_fit_evidence(documents: list[Document], b: int) -> list[Document]:
        kept: list[Document] = []
        seen: set[tuple[str, str]] = set()
        for doc in documents:
            source = str(doc.metadata.get("paper_id") or doc.metadata.get("source_file") or doc.metadata.get("source", ""))
            digest = hashlib.sha256(" ".join(doc.page_content.split()).encode()).hexdigest()
            key = (source, digest)
            if key in seen:
                continue
            cost = evidence.token_count(evidence.format_evidence(kept + [doc])[0])
            if cost > b:
                continue
            kept.append(doc)
            seen.add(key)
        return kept

    def baseline_fn():
        return baseline_fit_evidence(docs, budget)

    def optimized_fn():
        return evidence.fit_evidence(docs, budget)

    base_times = run_workload(baseline_fn, iterations, warmup=5)
    opt_times = run_workload(optimized_fn, iterations, warmup=5)

    base_stats = calculate_distribution(base_times)
    opt_stats = calculate_distribution(opt_times)

    passages_per_op = len(docs)
    base_tp = (1000.0 / base_stats["mean"]) * passages_per_op
    opt_tp = (1000.0 / opt_stats["mean"]) * passages_per_op

    return base_stats, opt_stats, base_tp, opt_tp


# ---------------------------------------------------------------------------
# Pillar 4: Deterministic Grounding & Numerical Verification
# ---------------------------------------------------------------------------

def benchmark_pillar_4_grounding(iterations: int = 200) -> tuple[dict[str, float], dict[str, float], float, float]:
    """Benchmark factual verification and numerical claim extraction."""
    docs = generate_synthetic_documents(count=10)
    citations = {f"E{i}": f"[Paper {i}]" for i in range(1, 11)}

    report_text = """
## 1. Literature Summary
In this research synthesis, we examine recent breakthroughs in transformer scaling [E1]. The initial baseline achieved 78.2% accuracy [E1], while hybrid retrieval improved performance to 94.2% [E2]. Furthermore, convergence accelerated by 3.8x when using 64 batch samples [E3].

## 2. Trend Detection
Empirical evaluation demonstrates consistent gains across all test splits [E4]. Specifically, parameter scaling from 1000 to 5000 parameters yielded an 18.5% gain in precision [E5]. No contradictions were observed across identical benchmarks [E6].

## 3. Common Methods
All evaluated architectures utilized AdamW optimizer with learning rate 0.001 and weight decay 1e-4 [E7].
"""

    # Baseline: Uncompiled regexes and no digit fast-path
    def baseline_numbers(text: str) -> set[str]:
        text = re.sub(r"https?://\S+", "", text).replace("−", "-")
        result = set()
        pattern = r"(?<![\w.])([+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)(\s*%|\s+percent\b)?(?!\w|\.\d)"
        for match in re.finditer(pattern, text, re.I):
            try:
                num = Decimal(match[1].replace(",", ""))
                exp = num.as_tuple().exponent
                if not isinstance(exp, int) or abs(exp) > 308:
                    val = str(num)
                else:
                    val = format(num, "f")
                    if "." in val:
                        val = val.rstrip("0").rstrip(".")
            except InvalidOperation:
                val = match[1]
            result.add(val + ("%" if match[2] else ""))
        return result

    def baseline_resolve(ans: str, cits: dict[str, str]) -> str:
        ans = ans.replace("【", "[").replace("】", "]")
        ans = re.sub(
            r"\[(E\d+(?:\s*[,;/]\s*E\d+)*)\]|\((E\d+(?:\s*[,;/]\s*E\d+)*)\)",
            lambda m: " ".join(f"[{ref.upper()}]" for ref in re.findall(r"E\d+", m[0], re.I)),
            ans,
            flags=re.I,
        )
        ans = re.sub(r"(?<=[\w)*`])(?=\[E\d+\])", " ", ans)
        ans = re.sub(
            r"(?m)^(\s*[-*•]\s*)(?:Source\s+)?P\d+(?:\s*[/,-]\s*(?:P\d+|E\d+))*\s*\(([^)\n]+)\)",
            lambda m: f"{m[1]}**{m[2].strip().strip('*')}**",
            ans,
        )
        resolved = re.sub(r"\[(E\d+)\]", lambda m: cits.get(m[1], "[unverified source]"), ans)
        resolved = re.sub(r"(\[[^\]]+\]\([^)]+\))(?:\s+\1)+", r"\1", resolved)
        return re.sub(r"(\[[^\]]+\](?:\([^)]+\))?)\s+([.,;:!?])", r"\1\2", resolved)

    def baseline_ground(answer: str, cits: dict[str, str], d_list: list[Document]) -> str:
        answer = answer.replace("【", "[").replace("】", "]")
        answer = re.sub(r"\[(E\d+(?:\s*[,;/]\s*E\d+)*)\]|\((E\d+(?:\s*[,;/]\s*E\d+)*)\)",
                        lambda m: " ".join(f"[{ref.upper()}]" for ref in re.findall(r"E\d+", m[0], re.I)),
                        answer, flags=re.I)
        answer = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"[\1]", answer)
        answer = re.sub(r"https?://[^\s<>]+", "[unverified URL removed]", answer)

        evidence_dict = {}
        for idx, doc in enumerate(d_list, 1):
            t = doc.metadata.get("paper_title") or doc.metadata.get("source_file") or ""
            evidence_dict[f"E{idx}"] = f"{doc.page_content} {t} {doc.metadata.get('year', '')}"

        lines = answer.splitlines()
        table_headers = {
            line.strip()
            for i, line in enumerate(lines[:-1])
            if line.strip().startswith("|") and re.fullmatch(r"[\s|:-]+", lines[i + 1])
        }
        blocks = re.split(r"(\n\s*\n|\n(?=\s*(?:#{1,6} |[-*•] |\d+[.)] |\|)))", answer)
        kept = []
        for idx, block in enumerate(blocks):
            if idx % 2:
                kept.append(block)
                continue
            prose = "\n".join(
                l for l in block.splitlines()
                if not l.lstrip().startswith("#")
                and l.strip() not in table_headers
                and not re.fullmatch(r"[\s|:-]+", l)
            ).strip()
            if not prose:
                kept.append(block)
                continue
            refs = re.findall(r"\[(E\d+)\]", prose)
            claim = re.sub(r"\[E\d+\]", "", prose)
            claim = re.sub(r"(?m)^\s*(?:[-*•]\s+)?(?:\d+[.)]\s+|\(\d+\)\s+)", "", claim)
            src = " ".join(evidence_dict.get(ref, "") for ref in refs)
            if baseline_numbers(claim) - baseline_numbers(src):
                pass
            kept.append(block)
        return baseline_resolve("".join(kept), cits)

    def baseline_fn():
        return baseline_ground(report_text, citations, docs)

    def optimized_fn():
        return evidence.ground_answer(
            report_text,
            citations=citations,
            documents=docs,
            preserve_valid_blocks=True,
        )

    base_times = run_workload(baseline_fn, iterations, warmup=10)
    opt_times = run_workload(optimized_fn, iterations, warmup=10)

    base_stats = calculate_distribution(base_times)
    opt_stats = calculate_distribution(opt_times)

    base_tp = 1000.0 / base_stats["mean"]
    opt_tp = 1000.0 / opt_stats["mean"]

    return base_stats, opt_stats, base_tp, opt_tp


# ---------------------------------------------------------------------------
# Pillar 5: Multi-Agent RAG Orchestration Pipeline (Zero-Network)
# ---------------------------------------------------------------------------

class MockVectorService:
    def __init__(self, docs: list[Document]):
        self.docs = docs
        self.is_ready = True

    def similarity_search(self, query: str, k: int | None = None) -> list[Document]:
        return self.docs[:k or 10]


class MockLLMService:
    def generate(self, prompt: str, **kwargs) -> str:
        return "Based on the provided research papers, the scaling laws demonstrate a 94.2% accuracy [E1]."


class NaivePreprocessorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="naive_preprocessor", description="Naive Preprocessor")

    def process(self, input_data: list[Document], context: dict[str, Any]) -> list[Document]:
        cleaned = []
        for doc in input_data:
            text = unicodedata.normalize("NFC", doc.page_content)
            for old, new in [("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u2013", "-"), ("\u2014", "-"), ("\u2026", "...")]:
                text = text.replace(old, new)
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r"[ \t]+", " ", text).strip()
            cleaned.append(Document(page_content=text, metadata=dict(doc.metadata)))
        return cleaned


def benchmark_pillar_5_pipeline(iterations: int = 100) -> tuple[dict[str, float], dict[str, float], float, float]:
    """Benchmark end-to-end multi-agent orchestration lifecycle."""
    docs = generate_synthetic_documents(count=20)
    mock_vs = MockVectorService(docs)
    mock_llm = MockLLMService()

    # Pre-instantiate production pipeline
    pipeline = AgentPipeline(mock_vs, mock_llm)  # type: ignore
    naive_pre = NaivePreprocessorAgent()

    # Baseline pipeline: Runs the pipeline stages with naive preprocessor & unoptimized fit_evidence
    def baseline_run():
        context = {
            "question": "What are the scaling laws for hybrid retrieval?",
            "model": "mock-model",
            "include_sources": True,
            "hybrid_mode": False,
            "retrieval_k": 10,
        }
        chunks = mock_vs.similarity_search("What are the scaling laws?", k=10)
        filtered = pipeline.analyzer.process(chunks, context)
        cleaned = naive_pre.process(filtered, context)
        # Naive fitting
        ranked = evidence.rank_evidence("scaling laws", cleaned)
        # Naive format_evidence token calculation loop
        kept_docs = []
        for d in ranked:
            c = evidence.token_count(evidence.format_evidence(kept_docs + [d])[0])
            if c <= 2000:
                kept_docs.append(d)
        ans = mock_llm.generate("prompt")
        validated = pipeline.validator.process(ans, context)
        assembled = pipeline.assembler.process(validated, context)
        return assembled

    def optimized_run():
        return pipeline.run(
            question="What are the scaling laws for hybrid retrieval?",
            model="mock-model",
            include_sources=True,
            hybrid_mode=False,
        )

    base_times = run_workload(baseline_run, iterations, warmup=5)
    opt_times = run_workload(optimized_run, iterations, warmup=5)

    base_stats = calculate_distribution(base_times)
    opt_stats = calculate_distribution(opt_times)

    base_tp = 1000.0 / base_stats["mean"]
    opt_tp = 1000.0 / opt_stats["mean"]

    return base_stats, opt_stats, base_tp, opt_tp


# ---------------------------------------------------------------------------
# Pillar 6: Search Federation Ingestion & Deduplication
# ---------------------------------------------------------------------------

def benchmark_pillar_6_search_ranking(iterations: int = 250) -> tuple[dict[str, float], dict[str, float], float, float]:
    """Benchmark paper deduplication, tokenization, and rank scoring."""
    papers_pool = SYNTHETIC_PAPERS_CATALOG
    query = "deep learning biomedical rag empirical attention"

    # Baseline: Redundant words() tokenization on titles and non-memoized DOI normalization
    def baseline_rank_dedup(query_str: str, raw_papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        combined = []
        seen_titles: set[str] = set()
        seen_dois: set[str] = set()
        query_terms = set(hybrid_retrieval.words(query_str))
        for rank, paper in enumerate(raw_papers):
            title = " ".join(hybrid_retrieval.words(paper["title"]))
            raw_doi = paper.get("doi") or (paper.get("url", "").split("doi.org/", 1)[1] if "doi.org/" in paper.get("url", "") else "")
            doi = str(raw_doi).casefold().strip()
            if title in seen_titles or (doi and doi in seen_dois):
                continue
            seen_titles.add(title)
            if doi:
                seen_dois.add(doi)
            p_words = set(hybrid_retrieval.words(paper["title"]))
            relevance = len(query_terms & p_words) / max(1, len(query_terms))
            p_copy = dict(paper)
            p_copy["_rank_score"] = relevance + 1 / (60 + rank + 1)
            combined.append(p_copy)
        combined.sort(key=lambda p: p["_rank_score"], reverse=True)
        return combined

    # Optimized: Single pass tokenization with local caching
    def optimized_rank_dedup(query_str: str, raw_papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        combined = []
        seen_titles: set[str] = set()
        seen_dois: set[str] = set()
        query_terms = set(hybrid_retrieval.words(query_str))
        q_len = max(1, len(query_terms))
        for rank, paper in enumerate(raw_papers):
            raw_title = paper.get("title", "")
            p_words = hybrid_retrieval.words(raw_title)
            title = " ".join(p_words)
            raw_url = paper.get("url", "")
            raw_doi = paper.get("doi") or (raw_url.split("doi.org/", 1)[1] if "doi.org/" in raw_url else "")
            doi = str(raw_doi).casefold().strip() if raw_doi else ""
            if title in seen_titles or (doi and doi in seen_dois):
                continue
            seen_titles.add(title)
            if doi:
                seen_dois.add(doi)
            relevance = len(query_terms & set(p_words)) / q_len
            p_copy = dict(paper)
            p_copy["_rank_score"] = relevance + 1.0 / (61 + rank)
            combined.append(p_copy)
        combined.sort(key=lambda p: p["_rank_score"], reverse=True)
        return combined

    base_times = run_workload(lambda: baseline_rank_dedup(query, papers_pool), iterations, warmup=10)
    opt_times = run_workload(lambda: optimized_rank_dedup(query, papers_pool), iterations, warmup=10)

    base_stats = calculate_distribution(base_times)
    opt_stats = calculate_distribution(opt_times)

    papers_per_op = len(papers_pool)
    base_tp = (1000.0 / base_stats["mean"]) * papers_per_op
    opt_tp = (1000.0 / opt_stats["mean"]) * papers_per_op

    return base_stats, opt_stats, base_tp, opt_tp


# ---------------------------------------------------------------------------
# Pillar 7: Report Presentation & Speculative Methodology Filter
# ---------------------------------------------------------------------------

def benchmark_pillar_7_report_filter(iterations: int = 150) -> tuple[dict[str, float], dict[str, float], float, float]:
    """Benchmark speculative methodology detection and report validation."""
    docs = generate_synthetic_documents(count=6)
    for d in docs:
        d.metadata["evidence_scope"] = "metadata_only"

    report_content = """
## 1. Literature Summary
**Paper 1** - Describes transformer models for chemistry [E1].
**Paper 2** - Outlines attention mechanisms for biology [E2].

## 2. Trend Detection
Increasing parameter counts across all benchmark evaluations [E3].

## 3. Common Methods
The authors likely employ dense vector retrieval pipelines and probably adopt fine-tuning across corpora.
The study may use recursive neural networks to classify graph nodes without empirical baseline validation.
We observe that the framework likely relies on BERT embeddings.

## 4. Limitations
The authors possibly acknowledge lack of external validation across diverse patient demographics.
The framework may omit hyperparameter tuning due to computational constraints.

## 5. Contradictions
Results differ based on dataset domain.

## 6. Research Gaps
Unexplored scaling limits.

## 7. Future Directions
Proposed research: test multimodal models.

## 8. Novel Paper Suggestions
| Title | Idea | Outcome |
|---|---|---|
| Project Alpha | Test hybrid | Improved recall |
"""

    # Baseline: Dynamic re-compilation of regular expressions in nested paragraph loop
    def baseline_norm_title(val: str) -> str:
        return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", val).casefold())

    def baseline_covered_papers(body: str, d_list: list[Document]) -> set[str]:
        cov = set()
        for doc in d_list:
            meta = doc.metadata
            key = str(meta.get("paper_id") or meta.get("source") or meta.get("source_file") or meta.get("paper_title") or "document")
            title = str(meta.get("paper_title") or meta.get("source_file") or "")
            url = str(meta.get("source") or "")
            if (url and url in body) or (title and baseline_norm_title(title) in baseline_norm_title(body)):
                cov.add(key)
        return cov

    def baseline_reject_speculative(report: str, documents: list[Document]) -> str:
        bodies = {
            int(m[1]): m[2].strip()
            for m in re.finditer(r"(?ms)^##\s+([1-8])\.\s+[^\n]*\n(.*?)(?=^##\s+|\Z)", report)
        }
        for num, body in bodies.items():
            if num not in (3, 4):
                continue
            paras = re.split(r"\n\s*\n", body)
            for idx, p in enumerate(paras):
                metadata_method = num == 3 and any(
                    doc.metadata.get("evidence_scope") == "metadata_only" and baseline_covered_papers(p, [doc])
                    for doc in documents or []
                )
                prose = re.sub(r"^\s*(?:[-*]\s+)?\*\*[^*]+\*\*\s*[–—:-]?", "", p)
                prose = re.sub(r"\[[^\]]*\](?:\([^)]*\))?", "", prose)
                method_claim = re.search(r"\b(?:retriev\w*|generat\w*|architect\w*|pipeline|model\w*|method\w*|embed\w*|vector|index\w*|train\w*|corpus|corpora)\b", prose, re.I)
                explicit_boundary = re.search(r"\b(?:no|not(?!\s+only\b)|cannot|without|lack\w*|missing|unavailable|undisclosed|unknown|unspecified|unreported|indeterminate|absent|omitted)\b|\b(?:doesn|isn|aren)['’]t\b", prose, re.I)
                speculative = re.search(r"\b(?:(?:study|paper|authors?|framework)\s+(?:likely|probably|possibly|may|might)\s+(?:use|employ|adopt|acknowledge|note)\w*|(?:title|metadata|validation)\b[^.!?\n]{0,100}\b(?:impli|suggest)\w*)", p, re.I)
                if (metadata_method and method_claim and not explicit_boundary) or speculative:
                    paras[idx] = f"{evidence.OMITTED_PASSAGE} (speculative attribution of methods or limitations)."
            replacement = "\n\n".join(paras)
            report = re.sub(rf"(?ms)(^##\s+{num}\.\s+[^\n]*\n).*?(?=^##\s+|\Z)",
                            lambda match: match[1] + replacement + "\n\n", report, count=1)
        return report

    def optimized_reject():
        return report_presentation.reject_speculative_methods(report_content, docs)

    base_times = run_workload(lambda: baseline_reject_speculative(report_content, docs), iterations, warmup=10)
    opt_times = run_workload(optimized_reject, iterations, warmup=10)

    base_stats = calculate_distribution(base_times)
    opt_stats = calculate_distribution(opt_times)

    base_tp = 1000.0 / base_stats["mean"]
    opt_tp = 1000.0 / opt_stats["mean"]

    return base_stats, opt_stats, base_tp, opt_tp


# ---------------------------------------------------------------------------
# Pillar 8: High-Concurrency Sliding-Window Rate Limiting
# ---------------------------------------------------------------------------

def benchmark_pillar_8_rate_limiting(iterations: int = 100) -> tuple[dict[str, float], dict[str, float], float, float]:
    """Benchmark high-throughput sliding window deque pruning under load."""
    store_base: dict[str, deque[float]] = {}
    store_opt: dict[str, deque[float]] = {}
    ip_pool = [f"192.168.1.{i}" for i in range(1, 200)] + [f"10.0.{i // 256}.{i % 256}" for i in range(300)]
    now = time.monotonic()

    # Pre-populate stores with historical hits
    for ip in ip_pool:
        store_base[ip] = deque([now - random.uniform(0.1, 75.0) for _ in range(random.randint(5, 40))])
        store_opt[ip] = deque(store_base[ip])

    import ipaddress

    trusted_cidrs_str = "10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16"

    def baseline_check_peer(peer: str) -> bool:
        try:
            return any(
                ipaddress.ip_address(peer) in ipaddress.ip_network(c.strip(), strict=False)
                for c in trusted_cidrs_str.split(",")
                if c.strip()
            )
        except ValueError:
            return False

    def optimized_check_peer(peer: str) -> bool:
        networks = ip_rate_limit._parse_trusted_networks(trusted_cidrs_str)
        try:
            addr = ipaddress.ip_address(peer)
            return any(addr in net for net in networks)
        except ValueError:
            return False

    def baseline_burst():
        for _ in range(250):
            ip = ip_pool[random.randint(0, len(ip_pool) - 1)]
            baseline_check_peer(ip)
            ip_rate_limit._prune_and_allow(store_base, ip, max_events=30, window_seconds=60.0)

    def optimized_burst():
        for _ in range(250):
            ip = ip_pool[random.randint(0, len(ip_pool) - 1)]
            optimized_check_peer(ip)
            ip_rate_limit._prune_and_allow(store_opt, ip, max_events=30, window_seconds=60.0)

    base_times = run_workload(baseline_burst, iterations, warmup=5)
    opt_times = run_workload(optimized_burst, iterations, warmup=5)

    base_stats = calculate_distribution(base_times)
    opt_stats = calculate_distribution(opt_times)

    requests_per_burst = 250
    base_tp = (1000.0 / base_stats["mean"]) * requests_per_burst
    opt_tp = (1000.0 / opt_stats["mean"]) * requests_per_burst

    return base_stats, opt_stats, base_tp, opt_tp


# ---------------------------------------------------------------------------
# Main Suite Execution & Reporting
# ---------------------------------------------------------------------------

def run_all_benchmarks(output_json: Path | None = None) -> list[BenchmarkStats]:
    print("=" * 80)
    print(" ResearchPaperRAG: Core Subsystem Performance & Benchmark Suite")
    print("=" * 80)
    print(f" Python Version : {sys.version.split()[0]}")
    print(f" Platform       : {sys.platform}")
    print(f" CPU Workers    : {os.cpu_count() or 1} logical cores")
    print("-" * 80)

    benchmarks_def = [
        ("Pillar 1", "Tokenizer-Aware Semantic Chunking", "ms", benchmark_pillar_1_chunking, "tokens/sec", 100),
        ("Pillar 2", "BM25 Retrieval & Reciprocal Rank Fusion", "ms", benchmark_pillar_2_retrieval, "queries/sec", 150),
        ("Pillar 3", "Evidence Token Budgeting & Incremental Packing", "ms", benchmark_pillar_3_evidence_fitting, "passages/sec", 100),
        ("Pillar 4", "Deterministic Grounding & Numerical Verification", "ms", benchmark_pillar_4_grounding, "evals/sec", 200),
        ("Pillar 5", "Multi-Agent RAG Orchestration Loop", "ms", benchmark_pillar_5_pipeline, "pipelines/sec", 100),
        ("Pillar 6", "Federated Search Ingestion & Deduplication", "ms", benchmark_pillar_6_search_ranking, "papers/sec", 250),
        ("Pillar 7", "Speculative Methodology & Report Filter", "ms", benchmark_pillar_7_report_filter, "reports/sec", 150),
        ("Pillar 8", "Sliding-Window IP Rate Limiter & Trusted CIDR", "ms", benchmark_pillar_8_rate_limiting, "req/sec", 100),
    ]

    results: list[BenchmarkStats] = []

    for pid, name, unit, fn, tp_metric, iters in benchmarks_def:
        print(f"\n[*] Benchmarking {pid}: {name} (N={iters})...")
        base_stats, opt_stats, base_tp, opt_tp = fn(iterations=iters)

        speedup = base_stats["mean"] / max(1e-9, opt_stats["mean"])
        reduction = ((base_stats["mean"] - opt_stats["mean"]) / max(1e-9, base_stats["mean"])) * 100.0

        stat = BenchmarkStats(
            pillar_id=pid,
            name=name,
            sample_count=iters,
            unit=unit,
            baseline_mean=round(base_stats["mean"], 3),
            baseline_p50=round(base_stats["p50"], 3),
            baseline_p95=round(base_stats["p95"], 3),
            baseline_p99=round(base_stats["p99"], 3),
            baseline_min=round(base_stats["min"], 3),
            baseline_max=round(base_stats["max"], 3),
            baseline_throughput=round(base_tp, 1),
            optimized_mean=round(opt_stats["mean"], 3),
            optimized_p50=round(opt_stats["p50"], 3),
            optimized_p95=round(opt_stats["p95"], 3),
            optimized_p99=round(opt_stats["p99"], 3),
            optimized_min=round(opt_stats["min"], 3),
            optimized_max=round(opt_stats["max"], 3),
            optimized_throughput=round(opt_tp, 1),
            speedup_factor=round(speedup, 2),
            latency_reduction_pct=round(reduction, 1),
            throughput_metric=tp_metric,
        )
        results.append(stat)

        print(f"    Baseline Latency  : p50={stat.baseline_p50}ms | p95={stat.baseline_p95}ms | Mean={stat.baseline_mean}ms")
        print(f"    Optimized Latency : p50={stat.optimized_p50}ms | p95={stat.optimized_p95}ms | Mean={stat.optimized_mean}ms")
        print(f"    Throughput Boost  : {stat.baseline_throughput:,.1f} -> {stat.optimized_throughput:,.1f} {tp_metric}")
        print(f"    Measured Impact   : {stat.speedup_factor}x Speedup ({stat.latency_reduction_pct:.1f}% Latency Reduction)")

    # Print summary table
    print("\n" + "=" * 110)
    print(f"{'Pillar':<10} | {'Benchmark Name':<42} | {'Base p50':<9} | {'Opt p50':<9} | {'Base Mean':<9} | {'Opt Mean':<9} | {'Speedup':<8}")
    print("-" * 110)
    for r in results:
        print(f"{r.pillar_id:<10} | {r.name:<42} | {r.baseline_p50:>7.2f}ms | {r.optimized_p50:>7.2f}ms | {r.baseline_mean:>7.2f}ms | {r.optimized_mean:>7.2f}ms | {r.speedup_factor:>6.2f}x")
    print("=" * 110)

    if output_json:
        data = [asdict(r) for r in results]
        output_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"\n[+] Statistical results written to: {output_json}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ResearchPaperRAG benchmarks")
    parser.add_argument("--output", type=str, default="scripts/benchmark_results.json", help="Path to output JSON")
    args = parser.parse_args()

    out_path = Path(args.output) if args.output else None
    run_all_benchmarks(out_path)
