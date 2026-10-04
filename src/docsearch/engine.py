import json
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol

import numpy as np

from docsearch.bm25_index import Bm25Index
from docsearch.constants import (
    BM25_SUBDIR,
    CANDIDATE_POOL_SIZE,
    CHUNKS_FILE,
    WARM_UP_QUERY,
    WARM_UP_ROUNDS,
)
from docsearch.corpus import load_corpus
from docsearch.hybrid import fuse_rankings
from docsearch.models import Chunk, Hit
from docsearch.vector_index import VectorIndex


class Mode(str, Enum):
    BM25 = "bm25"
    VECTOR = "vector"
    HYBRID = "hybrid"


class TextEncoder(Protocol):
    def encode_queries(self, texts: list[str]) -> np.ndarray: ...
    def encode_passages(self, texts: list[str]) -> np.ndarray: ...


@dataclass(frozen=True)
class Result:
    chunk: Chunk
    score: float
    sources: tuple[str, ...]


@dataclass(frozen=True)
class SearchResponse:
    hits: list[Result]
    elapsed_ms: float


def build_index(docs_dir: Path, index_dir: Path, encoder: TextEncoder) -> int:
    chunks = load_corpus(docs_dir)
    texts = [chunk.text for chunk in chunks]
    index_dir.mkdir(parents=True, exist_ok=True)
    Bm25Index.build(texts).save(index_dir / BM25_SUBDIR)
    VectorIndex(encoder.encode_passages(texts)).save(index_dir)
    payload = [asdict(chunk) for chunk in chunks]
    (index_dir / CHUNKS_FILE).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    return len(chunks)


class SearchEngine:
    """Loads the precomputed index; the embedding model only loads on demand."""

    def __init__(self, index_dir: Path, encoder_factory: Callable[[], TextEncoder]):
        self.index_dir = index_dir
        self._encoder_factory = encoder_factory
        self._encoder: TextEncoder | None = None
        self._chunks = self._load_chunks()
        self._bm25 = Bm25Index.load(index_dir / BM25_SUBDIR)
        self._vectors: VectorIndex | None = None

    def warm_up(self, mode: Mode) -> None:
        """Pay the one-time model load cost outside the timed search."""
        if mode is not Mode.BM25:
            encoder, _ = self._vector_parts()
            for _ in range(WARM_UP_ROUNDS):
                encoder.encode_queries([WARM_UP_QUERY])

    def search(self, query: str, mode: Mode, k: int) -> SearchResponse:
        started = time.perf_counter()
        if mode is Mode.BM25:
            results = self._bm25_results(query, k)
        elif mode is Mode.VECTOR:
            results = self._vector_results(query, k)
        else:
            results = self._hybrid_results(query, k)
        elapsed_ms = (time.perf_counter() - started) * 1000
        return SearchResponse(results, elapsed_ms)

    def _bm25_results(self, query: str, k: int) -> list[Result]:
        return self._as_results(self._bm25.search(query, k), "bm25")

    def _vector_results(self, query: str, k: int) -> list[Result]:
        return self._as_results(self._vector_hits(query, k), "vector")

    def _hybrid_results(self, query: str, k: int) -> list[Result]:
        rankings = {
            "bm25": [h.chunk_id for h in self._bm25.search(query, CANDIDATE_POOL_SIZE)],
            "vector": [h.chunk_id for h in self._vector_hits(query, CANDIDATE_POOL_SIZE)],
        }
        return [
            Result(self._chunks[f.chunk_id], f.score, f.sources)
            for f in fuse_rankings(rankings)[:k]
        ]

    def _vector_hits(self, query: str, k: int) -> list[Hit]:
        encoder, vectors = self._vector_parts()
        return vectors.search(encoder.encode_queries([query])[0], k)

    def _vector_parts(self) -> tuple[TextEncoder, VectorIndex]:
        if self._encoder is None or self._vectors is None:
            self._encoder = self._encoder_factory()
            self._vectors = VectorIndex.load(self.index_dir)
        return self._encoder, self._vectors

    def _as_results(self, hits: list[Hit], method: str) -> list[Result]:
        return [Result(self._chunks[h.chunk_id], h.score, (method,)) for h in hits]

    def _load_chunks(self) -> list[Chunk]:
        raw = json.loads((self.index_dir / CHUNKS_FILE).read_text(encoding="utf-8"))
        return [Chunk(**item) for item in raw]
