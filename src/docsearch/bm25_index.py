from pathlib import Path

import bm25s

from docsearch.models import Hit
from docsearch.text import tokenize


class Bm25Index:
    def __init__(self, retriever: bm25s.BM25, size: int):
        self._retriever = retriever
        self._size = size

    @classmethod
    def build(cls, texts: list[str]) -> "Bm25Index":
        retriever = bm25s.BM25()
        retriever.index([tokenize(t) for t in texts], show_progress=False)
        return cls(retriever, len(texts))

    def search(self, query: str, k: int) -> list[Hit]:
        tokens = tokenize(query)
        if not tokens:
            return []
        ids, scores = self._retriever.retrieve(
            [tokens], k=min(k, self._size), show_progress=False
        )
        return [
            Hit(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if s > 0
        ]

    def save(self, directory: Path) -> None:
        self._retriever.save(directory)

    @classmethod
    def load(cls, directory: Path) -> "Bm25Index":
        retriever = bm25s.BM25.load(directory)
        return cls(retriever, retriever.scores["num_docs"])
