import numpy as np

from docsearch.vector_index import VectorIndex


def unit(*values: float) -> np.ndarray:
    vector = np.array(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def test_search_ranks_by_cosine_similarity():
    matrix = np.stack([unit(1, 0), unit(0, 1), unit(1, 1)])
    hits = VectorIndex(matrix).search(unit(1, 0.1), k=3)
    assert [h.chunk_id for h in hits] == [0, 2, 1]


def test_search_limits_results_to_k():
    matrix = np.stack([unit(1, 0), unit(0, 1), unit(1, 1)])
    assert len(VectorIndex(matrix).search(unit(1, 0), k=2)) == 2


def test_index_round_trips_through_disk(tmp_path):
    matrix = np.stack([unit(1, 0), unit(0, 1)])
    VectorIndex(matrix).save(tmp_path)
    loaded = VectorIndex.load(tmp_path)
    assert loaded.search(unit(0, 1), k=1)[0].chunk_id == 1
