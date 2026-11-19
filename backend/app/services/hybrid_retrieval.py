"""Independent BM25 + dense retrieval with reciprocal rank fusion, without API calls."""

import math
import re
from collections import Counter
from typing import Any

from langchain_core.documents import Document

_WORD_PATTERN = re.compile(r"[\w-]{2,}")
_RRF_SCORES = tuple(1.0 / (60 + r) for r in range(1, 2001))


def words(text: str) -> list[str]:
    return _WORD_PATTERN.findall(text.casefold())


class HybridIndex:
    def __init__(self, documents: list[Document]):
        self.documents = documents
        self.counts = [Counter(words(doc.page_content)) for doc in documents]
        self.lengths = [sum(count.values()) for count in self.counts]
        self.average = sum(self.lengths) / max(1, len(documents)) or 1
        self.frequency: Counter[str] = Counter()
        for count in self.counts:
            self.frequency.update(count.keys())

        self._doc_length_denominators = [
            1.5 * (0.25 + 0.75 * length / self.average) for length in self.lengths
        ]

        self._inverted_index: dict[str, list[tuple[int, float]]] = {}
        for doc_idx, count in enumerate(self.counts):
            denom = self._doc_length_denominators[doc_idx]
            for word, tf in count.items():
                self._inverted_index.setdefault(word, []).append(
                    (doc_idx, tf / (tf + denom))
                )

        num_docs = len(documents)
        self._idfs: dict[str, float] = {
            word: math.log(1 + (num_docs - df + 0.5) / (df + 0.5)) * 2.5
            for word, df in self.frequency.items()
        }

        self._positions = {self.key(doc): i for i, doc in enumerate(documents)}

    def lexical(self, query: str, k: int = 30) -> list[int]:
        num_docs = len(self.documents)
        if num_docs == 0:
            return []

        query_terms = set(words(query))
        if not query_terms:
            return []

        scores: dict[int, float] = {}
        for word in query_terms:
            idf_scaled = self._idfs.get(word)
            if idf_scaled is None:
                continue
            postings = self._inverted_index.get(word)
            if postings:
                for doc_idx, tf_norm in postings:
                    scores[doc_idx] = scores.get(doc_idx, 0.0) + (idf_scaled * tf_norm)

        if not scores:
            return []

        candidate_scores = [(score, idx) for idx, score in scores.items() if score > 0]
        return [idx for _, idx in sorted(candidate_scores, key=lambda pair: (-pair[0], pair[1]))[:k]]

    def search(self, store: Any, query: str, k: int = 30) -> list[Document]:
        dense = store.similarity_search(query, k=min(k, len(self.documents)))
        positions = self._positions
        dense_ids = [positions[key] for doc in dense if (key := self.key(doc)) in positions]
        scores: dict[int, float] = {}
        rrf_len = len(_RRF_SCORES)
        for ranking in (dense_ids, self.lexical(query, k)):
            for rank, index in enumerate(ranking, 1):
                scores[index] = scores.get(index, 0.0) + (
                    _RRF_SCORES[rank - 1] if rank <= rrf_len else 1.0 / (60 + rank)
                )
        ordered = sorted(scores, key=lambda index: (-scores[index], index))
        return [self.documents[i] for i in ordered[:k]]

    @staticmethod
    def key(doc: Document) -> tuple[str, str, str]:
        return (
            str(doc.metadata.get("paper_id") or doc.metadata.get("source_file", "")),
            str(doc.metadata.get("page", "")),
            doc.page_content,
        )
