"""Independent BM25 + dense retrieval with reciprocal rank fusion, without API calls."""

import math
import re
from collections import Counter
from typing import Any

from langchain_core.documents import Document


def words(text: str) -> list[str]:
    return re.findall(r"[\w-]{2,}", text.casefold())


class HybridIndex:
    def __init__(self, documents: list[Document]):
        self.documents = documents
        self.counts = [Counter(words(doc.page_content)) for doc in documents]
        self.lengths = [sum(count.values()) for count in self.counts]
        self.average = sum(self.lengths) / max(1, len(documents)) or 1
        self.frequency: Counter[str] = Counter()
        for count in self.counts:
            self.frequency.update(count.keys())

    def lexical(self, query: str, k: int = 30) -> list[int]:
        scores = []
        for i, count in enumerate(self.counts):
            score = 0.0
            for word in set(words(query)):
                tf = count[word]
                if tf:
                    df = self.frequency[word]
                    idf = math.log(1 + (len(self.documents) - df + 0.5) / (df + 0.5))
                    score += (
                        idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * self.lengths[i] / self.average))
                    )
            if score > 0:
                scores.append((score, i))
        return [i for _, i in sorted(scores, key=lambda pair: (-pair[0], pair[1]))[:k]]

    def search(self, store: Any, query: str, k: int = 30) -> list[Document]:
        # One query embedding per facet, irrespective of the number of selected papers.
        dense = store.similarity_search(query, k=min(k, len(self.documents)))
        positions = {self.key(doc): i for i, doc in enumerate(self.documents)}
        dense_ids = [positions[self.key(doc)] for doc in dense if self.key(doc) in positions]
        scores: dict[int, float] = {}
        for ranking in (dense_ids, self.lexical(query, k)):
            for rank, index in enumerate(ranking, 1):
                scores[index] = scores.get(index, 0) + 1 / (60 + rank)
        ordered = sorted(scores, key=lambda index: (-scores[index], index))
        return [self.documents[i] for i in ordered[:k]]

    @staticmethod
    def key(doc: Document) -> tuple[str, str, str]:
        return (
            str(doc.metadata.get("paper_id") or doc.metadata.get("source_file", "")),
            str(doc.metadata.get("page", "")),
            doc.page_content,
        )
