"""Does markdown structure change retrieval quality when the content is held constant?

Builds five chunkings of the same cleaned documentation corpus (plain, markdown_fixed,
markdown_fixed_120, sections, sections_path; see docsearch.structure_variants), indexes
each one, and asks the questions of the chosen corpus. A retrieved chunk is a hit when it
contains the question's answer quote (docsearch.quote_match). Writes
results/structure-<corpus>-<model>.json.

Pre-registered hypothesis: Replication: for vector search, sections beats markdown_fixed
and sections beats markdown_fixed_120 at k=3 (paired sign test), on both corpora and both
embedding models.

Vector search is the primary mode. BM25 over the same chunks is a secondary mode.
The "answerable" count per variant is a ceiling: questions whose quote sits whole inside
at least one chunk. A variant that cuts quotes in two cannot score above it, except
through the partial-quote fallback.

Corpora: k8s (data/k8s-clean, eval/k8s-questions.json), pg (data/pg-clean,
eval/pg-questions.json). Models: bge (BAAI/bge-small-en-v1.5), e5 (intfloat/e5-small-v2).
Embeddings are cached in data/structure-cache/<corpus>/<model>/<variant>.npy, keyed by a
hash of the model name and chunk texts. For k8s with bge the older data/k8s-cache files
are reused when their key matches.

Prerequisites: k8s_prepare.py or pg_prepare.py, and the questions file of the corpus.
Usage: structure_eval.py --corpus {k8s,pg} --model {bge,e5}
"""
import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np

from _common import DATA_DIR, ROOT, write_json
from docsearch.bm25_index import Bm25Index
from docsearch.constants import E5_MODEL, EMBEDDING_MODEL
from docsearch.encoder import Encoder, silence_libraries
from docsearch.embedding_cache import chunk_key
from docsearch.evaluation import bootstrap_interval, paired_comparison
from docsearch.quote_match import first_hit_rank, is_hit, quote_in_chunk
from docsearch.structure_variants import (
    MIN_WORDS,
    OVERLAP_WORDS,
    TARGET_WORDS,
    VARIANTS,
    build_all,
    count_words,
)
from docsearch.vector_index import VectorIndex

CACHE_ROOT = ROOT / "data" / "structure-cache"
LEGACY_CACHE_DIR = ROOT / "data" / "k8s-cache"
CORPORA = {
    "k8s": {
        "clean_dir": ROOT / "data" / "k8s-clean",
        "questions": ROOT / "eval" / "k8s-questions.json",
        "dataset": "Kubernetes concept docs (kubernetes/website, content/en/docs/concepts)",
        "label": "Kubernetes concepts",
    },
    "pg": {
        "clean_dir": ROOT / "data" / "pg-clean",
        "questions": ROOT / "eval" / "pg-questions.json",
        "dataset": "PostgreSQL manual chapters (doc/src/sgml, DocBook converted with pandoc)",
        "label": "PostgreSQL manual",
    },
}
MODELS = {"bge": EMBEDDING_MODEL, "e5": E5_MODEL}

TOP_K = 10
CUTOFFS = (1, 3, 5, 10)
CI_CUTOFFS = (3, 5)
PAIR_CUTOFFS = (3, 5)
MODES = ("vector", "bm25")
# (A, B): A is expected to beat B.
PAIRS = (
    ("sections_path", "sections"),
    ("sections", "markdown_fixed"),
    ("markdown_fixed", "plain"),
    ("sections_path", "plain"),
    ("sections", "markdown_fixed_120"),
    ("markdown_fixed_120", "markdown_fixed"),
)
ENCODE_CHUNK = 256
WARM_UP_QUERY = "warm up"
HYPOTHESIS = (
    "Replication: for vector search, sections beats markdown_fixed and sections beats "
    "markdown_fixed_120 at k=3 (paired sign test), on both corpora and both embedding models."
)
METRIC_DEFINITION = (
    "A question is a hit at k when ANY of the top k chunks contains its answer quote "
    "(whole, or its first or last 60% of words contiguously). recall@k is the share of "
    "hit questions. MRR uses the first hit chunk."
)


def load_documents(clean_dir: Path) -> dict[str, str]:
    return {
        path.relative_to(clean_dir).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(clean_dir.rglob("*.md"))
    }


def read_cache(directory: Path, variant: str, key: str, count: int) -> np.ndarray | None:
    cache_file = directory / f"{variant}.npy"
    key_file = directory / f"{variant}.key"
    if not (cache_file.exists() and key_file.exists()):
        return None
    if key_file.read_text().strip() != key:
        return None
    cached = np.load(cache_file)
    return cached if cached.shape[0] == count else None


def encode_chunks(
    encoder: Encoder,
    cache_dir: Path,
    legacy_dirs: list[Path],
    model_name: str,
    variant: str,
    texts: list[str],
) -> tuple[np.ndarray, float | None]:
    """Return chunk embeddings and encoding seconds (None when read from cache)."""
    key = chunk_key(model_name, texts)
    for directory in [cache_dir, *legacy_dirs]:
        cached = read_cache(directory, variant, key, len(texts))
        if cached is not None:
            print(f"Loaded cached {variant} embeddings from {directory}")
            return cached, None
    started = time.perf_counter()
    parts = []
    for start in range(0, len(texts), ENCODE_CHUNK):
        parts.append(encoder.encode_passages(texts[start : start + ENCODE_CHUNK]))
        done = min(start + ENCODE_CHUNK, len(texts))
        print(f"\rEncoding {variant:18} {done}/{len(texts)}", end="", flush=True)
    print()
    matrix = np.vstack(parts)
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_dir / f"{variant}.npy", matrix)
    (cache_dir / f"{variant}.key").write_text(key + "\n")
    return matrix, time.perf_counter() - started


def read_questions(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_questions(questions: list[dict], documents: dict[str, str]) -> list[str]:
    """Ids of questions whose doc is missing or whose quote is not in that doc."""
    return [
        q["id"]
        for q in questions
        if q["doc"] not in documents or not quote_in_chunk(q["answer_quote"], documents[q["doc"]])
    ]


def rank_chunks(
    mode: str,
    variant: str,
    questions: list[dict],
    query_vectors: np.ndarray,
    vectors: VectorIndex,
    bm25: Bm25Index,
) -> list[list[int]]:
    rankings = []
    for done, question in enumerate(questions, start=1):
        if mode == "vector":
            hits = vectors.search(query_vectors[done - 1], TOP_K)
        else:
            hits = bm25.search(question["question"], TOP_K)
        rankings.append([h.chunk_id for h in hits])
        print(f"\rSearching {variant:18} {mode:6} {done}/{len(questions)}", end="", flush=True)
    print()
    return rankings


def mode_metrics(firsts: list[int | None]) -> dict:
    total = len(firsts)
    metrics: dict = {}
    for k in CUTOFFS:
        hits = [float(f is not None and f <= k) for f in firsts]
        metrics[f"hits@{k}"] = int(sum(hits))
        metrics[f"recall@{k}"] = sum(hits) / total
        if k in CI_CUTOFFS:
            metrics[f"recall@{k}_ci95"] = bootstrap_interval(hits)
    metrics["mrr"] = sum(0.0 if f is None else 1 / f for f in firsts) / total
    return metrics


def recall_by_kind(firsts: list[int | None], kinds: list[str], k: int) -> dict:
    result = {}
    for kind in sorted(set(kinds)):
        picked = [f for f, q in zip(firsts, kinds, strict=True) if q == kind]
        result[kind] = {
            "question_count": len(picked),
            f"recall@{k}": sum(f is not None and f <= k for f in picked) / len(picked),
        }
    return result


def evaluate_variant(
    variant: str,
    documents: dict[str, str],
    questions: list[dict],
    query_vectors: np.ndarray,
    encoder: Encoder,
    cache_dir: Path,
    legacy_dirs: list[Path],
    model_name: str,
) -> dict:
    chunks = build_all(variant, documents)
    texts = [c["text"] for c in chunks]
    word_counts = [count_words(t) for t in texts]
    quotes = [q["answer_quote"] for q in questions]
    matrix, encode_seconds = encode_chunks(
        encoder, cache_dir, legacy_dirs, model_name, variant, texts
    )
    vectors = VectorIndex(matrix)
    started = time.perf_counter()
    bm25 = Bm25Index.build(texts)
    bm25_seconds = time.perf_counter() - started
    kinds = [q["kind"] for q in questions]

    modes, firsts = {}, {}
    for mode in MODES:
        rankings = rank_chunks(mode, variant, questions, query_vectors, vectors, bm25)
        firsts[mode] = [
            first_hit_rank(quote, [texts[i] for i in ranked])
            for quote, ranked in zip(quotes, rankings, strict=True)
        ]
        modes[mode] = {
            **mode_metrics(firsts[mode]),
            "by_kind": recall_by_kind(firsts[mode], kinds, 3),
        }
    report = {
        "chunk_count": len(chunks),
        "chunk_words_mean": statistics.fmean(word_counts),
        "chunk_words_median": statistics.median(word_counts),
        "chunk_words_max": max(word_counts),
        "answerable_whole": sum(any(quote_in_chunk(q, t) for t in texts) for q in quotes),
        "answerable_any": sum(any(is_hit(q, t) for t in texts) for q in quotes),
        "modes": modes,
        "timing": {"bm25_index_s": bm25_seconds, "encode_chunks_s": encode_seconds},
    }
    return {"report": report, "firsts": firsts}


def paired_report(firsts: dict[str, dict[str, list[int | None]]]) -> list[dict]:
    return [
        {"mode": mode, "a": a, "b": b, **paired_comparison(firsts[a][mode], firsts[b][mode], k)}
        for mode in MODES
        for a, b in PAIRS
        for k in PAIR_CUTOFFS
    ]


def print_summary(report: dict) -> None:
    n = report["question_count"]
    print(f"\n{report['label']} / {report['model']}: {report['doc_count']} docs, {n} questions")
    print(f"Hypothesis: {report['hypothesis']}")
    print(report["metric_definition"])
    if report["unverified_questions"]:
        print(f"WARNING: quote not found in its doc for: {', '.join(report['unverified_questions'])}")
    header = (
        f"{'variant':19} {'mode':6} {'chunks':>6} {'whole':>5} "
        + " ".join(f"{'r@' + str(k):>6}" for k in CUTOFFS)
        + f" {'mrr':>6} {'CI95 r@3':>13} {'CI95 r@5':>13}"
    )
    print("\n" + header)
    for mode in MODES:
        for variant in VARIANTS:
            stats = report["variants"][variant]
            modes = stats["modes"][mode]
            cells = " ".join(f"{modes[f'recall@{k}']:6.3f}" for k in CUTOFFS)
            low3, high3 = modes["recall@3_ci95"]
            low5, high5 = modes["recall@5_ci95"]
            print(
                f"{variant:19} {mode:6} {stats['chunk_count']:6} {stats['answerable_whole']:5} "
                f"{cells} {modes['mrr']:6.3f} {low3:6.3f}-{high3:5.3f} {low5:6.3f}-{high5:5.3f}"
            )
    print("\nChunk words (mean / median / max), answerable whole / partial-or-whole:")
    for variant in VARIANTS:
        stats = report["variants"][variant]
        print(
            f"{variant:19} {stats['chunk_words_mean']:6.1f} / {stats['chunk_words_median']:5.1f}"
            f" / {stats['chunk_words_max']:4}   {stats['answerable_whole']}/{n} / {stats['answerable_any']}/{n}"
        )
    print("\nPaired comparisons (only A / only B / sign test p):")
    for item in report["paired"]:
        print(
            f"{item['mode']:6} k={item['k']} {item['a']} vs {item['b']}: "
            f"{item['only_a']} / {item['only_b']} p={item['p_value']:.4g}"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", choices=sorted(CORPORA), required=True)
    parser.add_argument("--model", choices=sorted(MODELS), required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    corpus = CORPORA[args.corpus]
    model_name = MODELS[args.model]
    clean_dir, questions_file = corpus["clean_dir"], corpus["questions"]
    silence_libraries()
    if not clean_dir.exists():
        raise SystemExit(f"Missing {clean_dir}. Run the corpus preparation script first.")
    if not questions_file.exists():
        raise SystemExit(f"Missing {questions_file}.")
    documents = load_documents(clean_dir)
    questions = read_questions(questions_file)
    unverified = check_questions(questions, documents)
    print(f"{args.corpus}/{args.model}: {len(documents)} documents, {len(questions)} questions")
    print(f"Hypothesis: {HYPOTHESIS}")

    cache_dir = CACHE_ROOT / args.corpus / args.model
    legacy_dirs = [LEGACY_CACHE_DIR] if (args.corpus, args.model) == ("k8s", "bge") else []
    encoder = Encoder(model_name)
    encoder.encode_queries([WARM_UP_QUERY])
    query_vectors = encoder.encode_queries([q["question"] for q in questions])

    variants, firsts = {}, {}
    for number, variant in enumerate(VARIANTS, start=1):
        print(f"[{number}/{len(VARIANTS)}] {variant}")
        result = evaluate_variant(
            variant, documents, questions, query_vectors, encoder, cache_dir, legacy_dirs, model_name
        )
        variants[variant] = result["report"]
        firsts[variant] = result["firsts"]
        print(f"{variant}: {result['report']['chunk_count']} chunks")

    report = {
        "dataset": corpus["dataset"],
        "label": corpus["label"],
        "corpus": args.corpus,
        "model": model_name,
        "hypothesis": HYPOTHESIS,
        "metric_definition": METRIC_DEFINITION,
        "doc_count": len(documents),
        "question_count": len(questions),
        "unverified_questions": unverified,
        "top_k": TOP_K,
        "chunking": {
            "target_words": TARGET_WORDS,
            "overlap_words": OVERLAP_WORDS,
            "min_words": MIN_WORDS,
        },
        "variants": variants,
        "paired": paired_report(firsts),
        "questions": [
            {
                "id": q["id"],
                "kind": q["kind"],
                "question": q["question"],
                "doc": q["doc"],
                "first_hit_rank": {v: {m: firsts[v][m][i] for m in MODES} for v in VARIANTS},
            }
            for i, q in enumerate(questions)
        ],
    }
    output_file = DATA_DIR / f"structure-{args.corpus}-{args.model}.json"
    write_json(output_file, report)
    print_summary(report)
    print(f"\nWrote {output_file}")


if __name__ == "__main__":
    main()
