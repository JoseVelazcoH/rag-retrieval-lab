from dataclasses import dataclass

from docsearch.constants import RRF_K


@dataclass(frozen=True)
class FusedHit:
    chunk_id: int
    score: float
    sources: tuple[str, ...]


def fuse_rankings(rankings: dict[str, list[int]]) -> list[FusedHit]:
    """Reciprocal Rank Fusion: score = sum over methods of 1 / (k + rank)."""
    scores: dict[int, float] = {}
    sources: dict[int, list[str]] = {}
    for method, ranked_ids in rankings.items():
        for rank, chunk_id in enumerate(ranked_ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (RRF_K + rank)
            sources.setdefault(chunk_id, []).append(method)
    ordered = sorted(scores, key=scores.__getitem__, reverse=True)
    return [FusedHit(i, scores[i], tuple(sources[i])) for i in ordered]
