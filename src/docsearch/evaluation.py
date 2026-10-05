"""Retrieval metrics computed from ranked document lists."""
import math
import random


def dedupe_ranking(paths: list[str]) -> list[str]:
    """Collapse chunk-level results into a document ranking, keeping first hits."""
    return list(dict.fromkeys(paths))


def first_rank(ranked: list[str], expected: str) -> int | None:
    """1-based position of the expected document, or None when it is missing."""
    for position, path in enumerate(ranked, start=1):
        if path == expected:
            return position
    return None


def reciprocal_rank(ranked: list[str], expected: str) -> float:
    rank = first_rank(ranked, expected)
    return 0.0 if rank is None else 1 / rank


def hit_at_k(ranked: list[str], expected: str, k: int) -> bool:
    rank = first_rank(ranked, expected)
    return rank is not None and rank <= k


def recall_at_k(rankings: list[list[str]], expected: list[str], k: int) -> float:
    """Share of queries whose expected document appears in the top k."""
    if not rankings:
        return 0.0
    hits = sum(hit_at_k(r, e, k) for r, e in zip(rankings, expected, strict=True))
    return hits / len(rankings)


def mrr(rankings: list[list[str]], expected: list[str]) -> float:
    """Mean reciprocal rank of the expected document over all queries."""
    if not rankings:
        return 0.0
    total = sum(reciprocal_rank(r, e) for r, e in zip(rankings, expected, strict=True))
    return total / len(rankings)


def first_rank_any(ranked: list[str], relevant: set[str]) -> int | None:
    """1-based position of the first relevant document, or None when none appear."""
    for position, doc_id in enumerate(ranked, start=1):
        if doc_id in relevant:
            return position
    return None


def parse_qrels(lines: list[str]) -> dict[str, set[str]]:
    """Map query id to relevant doc ids from BEIR qrels rows (score > 0 is relevant)."""
    relevant: dict[str, set[str]] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        query_id, doc_id, score = line.rstrip("\n").split("\t")
        if int(score) > 0:
            relevant.setdefault(query_id, set()).add(doc_id)
    return relevant


def sign_test_p_value(only_a: int, only_b: int) -> float:
    """Exact two-sided sign test over discordant pairs (binomial, p=0.5)."""
    discordant = only_a + only_b
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, i) for i in range(min(only_a, only_b) + 1))
    return min(1.0, 2 * tail / 2**discordant)


def bootstrap_interval(
    values: list[float], resamples: int = 2000, confidence: float = 0.95, seed: int = 0
) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean of per-query values."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(resamples))
    tail = (1 - confidence) / 2
    low = means[int(tail * (resamples - 1))]
    high = means[int((1 - tail) * (resamples - 1))]
    return (low, high)


def paired_comparison(
    firsts_a: list[int | None], firsts_b: list[int | None], k: int
) -> dict:
    """Discordant-pair counts and sign test for two systems' first-hit ranks at cutoff k."""
    hit_a = [f is not None and f <= k for f in firsts_a]
    hit_b = [f is not None and f <= k for f in firsts_b]
    only_a = sum(a and not b for a, b in zip(hit_a, hit_b, strict=True))
    only_b = sum(b and not a for a, b in zip(hit_a, hit_b, strict=True))
    return {
        "k": k,
        "only_a": only_a,
        "only_b": only_b,
        "both": sum(a and b for a, b in zip(hit_a, hit_b, strict=True)),
        "neither": sum(not a and not b for a, b in zip(hit_a, hit_b, strict=True)),
        "p_value": sign_test_p_value(only_a, only_b),
    }
