import numpy as np
import pytest

from docsearch.engine import Mode, SearchEngine, build_index

CONCEPTS = ["slow", "vacation"]


class FakeEncoder:
    """Maps texts to one-hot concept vectors so ranking is predictable."""

    def _embed(self, texts):
        rows = [[float(c in t.lower()) for c in CONCEPTS] or [1.0] for t in texts]
        matrix = np.array(rows, dtype=np.float32) + 1e-3
        return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)

    encode_queries = _embed
    encode_passages = _embed


@pytest.fixture
def engine(tmp_path):
    docs = tmp_path / "docs"
    (docs / "runbooks").mkdir(parents=True)
    (docs / "runbooks" / "nginx.md").write_text(
        "# Nginx\n\nThe site is slow and returns a 504 timeout.\n", encoding="utf-8"
    )
    (docs / "hr.md").write_text(
        "# Vacation\n\nVacation requests need two weeks of notice.\n", encoding="utf-8"
    )
    index_dir = tmp_path / ".index"
    build_index(docs, index_dir, FakeEncoder())
    return SearchEngine(index_dir, encoder_factory=FakeEncoder)


def test_bm25_mode_cites_path_and_line(engine):
    result = engine.search("timeout 504", Mode.BM25, k=1)
    top = result.hits[0]
    assert (top.chunk.path, top.chunk.line) == ("runbooks/nginx.md", 1)
    assert top.sources == ("bm25",)


def test_vector_mode_finds_paraphrase_without_shared_keywords(engine):
    result = engine.search("dragging along", Mode.VECTOR, k=2)
    assert result.hits[0].chunk.path in {"runbooks/nginx.md", "hr.md"}
    assert result.hits[0].sources == ("vector",)


def test_hybrid_mode_reports_contributing_methods(engine):
    result = engine.search("slow timeout", Mode.HYBRID, k=1)
    assert result.hits[0].chunk.path == "runbooks/nginx.md"
    assert result.hits[0].sources == ("bm25", "vector")


def test_bm25_mode_never_loads_the_encoder(tmp_path, engine):
    def exploding_factory():
        raise AssertionError("encoder must stay lazy")

    lazy = SearchEngine(engine.index_dir, encoder_factory=exploding_factory)
    assert lazy.search("timeout", Mode.BM25, k=1).hits


def test_search_reports_elapsed_milliseconds(engine):
    assert engine.search("timeout", Mode.BM25, k=1).elapsed_ms >= 0
