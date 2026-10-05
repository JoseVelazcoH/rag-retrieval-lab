"""Benchmark bm25, vector and hybrid on a BEIR dataset and write results/beir-<dataset>.json.

Usage: beir_eval.py [scifact|cqadupstack-android] [--rerank]   (defaults to scifact)

The "rerank" mode takes the vector top CANDIDATE_POOL_SIZE and reorders it with a
cross-encoder (RERANK_MODEL). Hypothesis fixed before running: rerank beats vector at
k=3 with a significant sign test on both datasets.

The "hybrid73" mode weighs the vector ranking 0.7 and BM25 0.3 inside RRF, the split
suggested by the LangChain EnsembleRetriever example. Hypothesis fixed before running:
hybrid73 beats vector at k=3 with a significant sign test on both datasets.

Queries are also split by docsearch.query_kinds ("identifier" vs "natural"), and the
paired comparisons are repeated inside each group.

Reuses the engine components (tokenizer, BM25, encoder with query prefix, RRF with
the engine's candidate pool) so the numbers measure exactly this search engine.
"""
import json
import sys
import time
import urllib.request
import zipfile
from itertools import combinations
from pathlib import Path

import numpy as np

from _common import DATA_DIR, ROOT, write_json
from docsearch.bm25_index import Bm25Index
from docsearch.constants import CANDIDATE_POOL_SIZE
from docsearch.encoder import Encoder, silence_libraries
from docsearch.evaluation import (
    bootstrap_interval,
    first_rank_any,
    parse_qrels,
    sign_test_p_value,
)
from docsearch.hybrid import fuse_rankings
from docsearch.query_kinds import query_kind
from docsearch.vector_index import VectorIndex

BEIR_DIR = ROOT / "data" / "beir"
HF_ANDROID = "https://huggingface.co/datasets/mteb/cqadupstack-android/resolve/main/"
# Each dataset is either one BEIR zip or individual files (the full CQADupStack zip is 5 GB).
DATASETS = {
    "scifact": {
        "zip": "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip",
    },
    "cqadupstack-android": {
        "files": {
            "corpus.jsonl": HF_ANDROID + "corpus.jsonl",
            "queries.jsonl": HF_ANDROID + "queries.jsonl",
            "qrels/test.tsv": HF_ANDROID + "qrels/test.tsv",
        },
    },
}
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
DATASET = ARGS[0] if ARGS else "scifact"
if DATASET not in DATASETS:
    sys.exit(f"Unknown dataset {DATASET!r}. Choose from {', '.join(DATASETS)}.")
DATASET_DIR = BEIR_DIR / DATASET
EMBEDDINGS_FILE = BEIR_DIR / f"{DATASET}-embeddings.npy"
OUTPUT_FILE = DATA_DIR / f"beir-{DATASET}.json"
QUERY_KINDS = ("identifier", "natural")

TOP_K = 10
CUTOFFS = (1, 3, 10)
CI_CUTOFFS = (3, 10)
MODES = ("bm25", "vector", "hybrid", "hybrid73") + (("rerank",) if "--rerank" in sys.argv else ())
HYBRID73_WEIGHTS = {"vector": 0.7, "bm25": 0.3}
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_MAX_LENGTH = 512
ENCODE_CHUNK = 256
WARM_UP_QUERY = "warm up"
METRIC_DEFINITION = (
    "A query is a hit at k when ANY of its relevant documents is in the top k. "
    "recall@k is the share of hit queries. MRR uses the first relevant document."
)


def ensure_dataset() -> None:
    source = DATASETS[DATASET]
    if "zip" in source:
        if (DATASET_DIR / "corpus.jsonl").exists():
            return
        BEIR_DIR.mkdir(parents=True, exist_ok=True)
        archive = BEIR_DIR / f"{DATASET}.zip"
        print(f"Downloading {source['zip']}")
        urllib.request.urlretrieve(source["zip"], archive)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(BEIR_DIR)
        return
    for name, url in source["files"].items():
        target = DATASET_DIR / name
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, target)


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def passage_text(doc: dict) -> str:
    return f"{doc['title']}. {doc['text']}"


def load_test_queries(
    queries: list[dict], relevant: dict[str, set[str]]
) -> list[dict]:
    return [q for q in queries if q["_id"] in relevant]


def encode_corpus(encoder: Encoder, texts: list[str]) -> tuple[np.ndarray, float | None]:
    """Return passage embeddings and encoding seconds (None when read from cache)."""
    if EMBEDDINGS_FILE.exists():
        cached = np.load(EMBEDDINGS_FILE)
        if cached.shape[0] == len(texts):
            print(f"Loaded cached embeddings from {EMBEDDINGS_FILE.name}")
            return cached, None
    started = time.perf_counter()
    chunks = []
    for start in range(0, len(texts), ENCODE_CHUNK):
        chunks.append(encoder.encode_passages(texts[start : start + ENCODE_CHUNK]))
        done = min(start + ENCODE_CHUNK, len(texts))
        print(f"\rEncoding passages {done}/{len(texts)}", end="", flush=True)
    print()
    matrix = np.vstack(chunks)
    np.save(EMBEDDINGS_FILE, matrix)
    return matrix, time.perf_counter() - started


class Searcher:
    """The engine's three retrieval modes over an in-memory corpus."""

    def __init__(self, bm25: Bm25Index, vectors: VectorIndex, encoder: Encoder, texts: list[str], reranker):
        self._bm25 = bm25
        self._vectors = vectors
        self._encoder = encoder
        self._texts = texts
        self._reranker = reranker

    def bm25(self, query: str, k: int) -> list[int]:
        return [h.chunk_id for h in self._bm25.search(query, k)]

    def vector(self, query: str, k: int) -> list[int]:
        return [h.chunk_id for h in self._vector_hits(query, k)]

    def hybrid(self, query: str, k: int) -> list[int]:
        rankings = {
            "bm25": self.bm25(query, CANDIDATE_POOL_SIZE),
            "vector": self.vector(query, CANDIDATE_POOL_SIZE),
        }
        return [f.chunk_id for f in fuse_rankings(rankings)[:k]]

    def hybrid73(self, query: str, k: int) -> list[int]:
        rankings = {
            "bm25": self.bm25(query, CANDIDATE_POOL_SIZE),
            "vector": self.vector(query, CANDIDATE_POOL_SIZE),
        }
        return [f.chunk_id for f in fuse_rankings(rankings, HYBRID73_WEIGHTS)[:k]]

    def rerank(self, query: str, k: int) -> list[int]:
        candidates = self.vector(query, CANDIDATE_POOL_SIZE)
        scores = self._reranker.predict([(query, self._texts[i]) for i in candidates])
        order = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)
        return [candidates[i] for i in order[:k]]

    def search(self, mode: str, query: str, k: int) -> list[int]:
        return getattr(self, mode)(query, k)

    def _vector_hits(self, query: str, k: int):
        return self._vectors.search(self._encoder.encode_queries([query])[0], k)


def run_mode(
    searcher: Searcher, mode: str, queries: list[dict], doc_ids: list[str]
) -> tuple[list[list[str]], list[float]]:
    rankings, timings = [], []
    for done, query in enumerate(queries, start=1):
        started = time.perf_counter()
        ranked = searcher.search(mode, query["text"], TOP_K)
        timings.append((time.perf_counter() - started) * 1000)
        rankings.append([doc_ids[i] for i in ranked])
        print(f"\rSearching {mode:6} {done}/{len(queries)}", end="", flush=True)
    print()
    return rankings, timings


def mode_metrics(
    rankings: list[list[str]], relevant: list[set[str]], timings: list[float]
) -> dict:
    firsts = [first_rank_any(r, rel) for r, rel in zip(rankings, relevant)]
    total = len(firsts)
    metrics: dict = {}
    for k in CUTOFFS:
        hits = [float(f is not None and f <= k) for f in firsts]
        metrics[f"hits@{k}"] = int(sum(hits))
        metrics[f"recall@{k}"] = sum(hits) / total
        if k in CI_CUTOFFS:
            metrics[f"recall@{k}_ci95"] = bootstrap_interval(hits)
    metrics["mrr"] = sum(0.0 if f is None else 1 / f for f in firsts) / total
    metrics["search_ms_mean"] = sum(timings) / total
    metrics["search_ms_median"] = float(np.median(timings))
    return metrics


def paired_comparison(
    firsts_a: list[int | None], firsts_b: list[int | None], k: int
) -> dict:
    hit_a = [f is not None and f <= k for f in firsts_a]
    hit_b = [f is not None and f <= k for f in firsts_b]
    only_a = sum(a and not b for a, b in zip(hit_a, hit_b))
    only_b = sum(b and not a for a, b in zip(hit_a, hit_b))
    return {
        "k": k,
        "only_a": only_a,
        "only_b": only_b,
        "both": sum(a and b for a, b in zip(hit_a, hit_b)),
        "neither": sum(not a and not b for a, b in zip(hit_a, hit_b)),
        "p_value": sign_test_p_value(only_a, only_b),
    }


def pair_names() -> list[tuple[str, str]]:
    # (A, B) ordered so the stronger expected mode comes first.
    order = [m for m in ("rerank", "hybrid73", "hybrid", "vector", "bm25") if m in MODES]
    return list(combinations(order, 2))


def print_summary(report: dict) -> None:
    n = report["query_count"]
    print(f"\n{report['dataset']}: {report['doc_count']} docs, {n} queries")
    print(report["metric_definition"])
    for name, stats in report["modes"].items():
        cells = " ".join(
            f"hits@{k}={stats[f'hits@{k}']}/{n} r@{k}={stats[f'recall@{k}']:.3f}"
            for k in CUTOFFS
        )
        low3, high3 = stats["recall@3_ci95"]
        low10, high10 = stats["recall@10_ci95"]
        print(
            f"{name:7} {cells} mrr={stats['mrr']:.3f}"
            f" | CI95 r@3 {low3:.3f}-{high3:.3f} r@10 {low10:.3f}-{high10:.3f}"
            f" | {stats['search_ms_mean']:.1f} ms/query"
        )
    print("\nPaired comparisons (only A / only B / sign test p):")
    for item in report["paired"]:
        print(
            f"k={item['k']:<2} {item['a']} vs {item['b']}: "
            f"{item['only_a']} / {item['only_b']} p={item['p_value']:.4g}"
        )
    for kind, group in report["by_query_kind"].items():
        print(f"\n[{kind}] {group['query_count']} queries, paired (only A / only B / p):")
        for item in group["paired"]:
            print(
                f"k={item['k']:<2} {item['a']} vs {item['b']}: "
                f"{item['only_a']} / {item['only_b']} p={item['p_value']:.4g}"
            )
    timing = report["timing"]
    encode = timing["encode_passages_s"]
    encode_text = "cached" if encode is None else f"{encode:.1f}s"
    print(
        f"\nIndexing: bm25 {timing['bm25_index_s']:.2f}s, "
        f"passage embeddings {encode_text}"
    )


def main() -> None:
    silence_libraries()
    ensure_dataset()
    docs = read_jsonl(DATASET_DIR / "corpus.jsonl")
    doc_ids = [d["_id"] for d in docs]
    texts = [passage_text(d) for d in docs]
    qrels = parse_qrels(
        (DATASET_DIR / "qrels" / "test.tsv").read_text(encoding="utf-8").splitlines()
    )
    queries = load_test_queries(read_jsonl(DATASET_DIR / "queries.jsonl"), qrels)
    relevant = [qrels[q["_id"]] for q in queries]

    started = time.perf_counter()
    bm25 = Bm25Index.build(texts)
    bm25_seconds = time.perf_counter() - started

    encoder = Encoder()
    matrix, encode_seconds = encode_corpus(encoder, texts)
    reranker = None
    if "rerank" in MODES:
        from sentence_transformers import CrossEncoder

        reranker = CrossEncoder(RERANK_MODEL, max_length=RERANK_MAX_LENGTH)
    searcher = Searcher(bm25, VectorIndex(matrix), encoder, texts, reranker)
    searcher.vector(WARM_UP_QUERY, 1)

    rankings, modes = {}, {}
    for mode in MODES:
        rankings[mode], timings = run_mode(searcher, mode, queries, doc_ids)
        modes[mode] = mode_metrics(rankings[mode], relevant, timings)

    firsts = {
        m: [first_rank_any(r, rel) for r, rel in zip(rankings[m], relevant)]
        for m in MODES
    }
    paired = [
        {"a": a, "b": b, **paired_comparison(firsts[a], firsts[b], k)}
        for a, b in pair_names()
        for k in CI_CUTOFFS
    ]
    kinds = [query_kind(q["text"]) for q in queries]
    by_query_kind = {}
    for kind in QUERY_KINDS:
        idx = [i for i, k in enumerate(kinds) if k == kind]
        by_query_kind[kind] = {
            "query_count": len(idx),
            "paired": [
                {
                    "a": a,
                    "b": b,
                    **paired_comparison([firsts[a][i] for i in idx], [firsts[b][i] for i in idx], k),
                }
                for a, b in pair_names()
                for k in CI_CUTOFFS
            ],
        }
    report = {
        "dataset": f"BEIR {DATASET} (test split)",
        "doc_count": len(docs),
        "query_count": len(queries),
        "metric_definition": METRIC_DEFINITION,
        "top_k": TOP_K,
        "hybrid_pool_size": CANDIDATE_POOL_SIZE,
        "rerank_model": RERANK_MODEL if "rerank" in MODES else None,
        "hybrid73_weights": HYBRID73_WEIGHTS,
        "modes": modes,
        "paired": paired,
        "by_query_kind": by_query_kind,
        "timing": {
            "bm25_index_s": bm25_seconds,
            "encode_passages_s": encode_seconds,
        },
        "queries": [
            {
                "id": q["_id"],
                "text": q["text"],
                "kind": kinds[i],
                "relevant_ids": sorted(rel),
                "first_relevant_rank": {m: firsts[m][i] for m in MODES},
            }
            for i, (q, rel) in enumerate(zip(queries, relevant))
        ],
    }
    write_json(OUTPUT_FILE, report)
    print_summary(report)


if __name__ == "__main__":
    main()
