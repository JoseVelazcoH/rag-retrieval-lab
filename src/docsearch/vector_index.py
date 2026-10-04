from pathlib import Path

import numpy as np

from docsearch.constants import VECTORS_FILE
from docsearch.models import Hit


class VectorIndex:
    """Cosine search over L2-normalized embeddings (a dot product)."""

    def __init__(self, matrix: np.ndarray):
        self._matrix = matrix

    def search(self, query_vector: np.ndarray, k: int) -> list[Hit]:
        scores = self._matrix @ query_vector
        best = np.argsort(-scores)[:k]
        return [Hit(int(i), float(scores[i])) for i in best]

    def save(self, directory: Path) -> None:
        np.save(directory / VECTORS_FILE, self._matrix)

    @classmethod
    def load(cls, directory: Path) -> "VectorIndex":
        return cls(np.load(directory / VECTORS_FILE))
