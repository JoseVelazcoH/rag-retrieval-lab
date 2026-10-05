"""Run every eval query in each mode and write results/eval.json.

Usage: run_eval.py [queries.json]  (defaults to eval/queries.json)
"""
import json
import sys
from pathlib import Path

from _common import DATA_DIR, MODES, ROOT, open_engine, write_json
from docsearch.engine import Mode, SearchEngine
from docsearch.evaluation import (
    bootstrap_interval,
    dedupe_ranking,
    first_rank,
    hit_at_k,
    mrr,
    recall_at_k,
)

QUERIES_FILE = ROOT / "eval" / "queries.json"
POOL_SIZE = 10


def ranked_files(engine: SearchEngine, query: str, mode: Mode) -> list[str]:
    response = engine.search(query, mode, POOL_SIZE)
    return dedupe_ranking([hit.chunk.path for hit in response.hits])


def evaluate_mode(engine: SearchEngine, queries: list[dict], mode: Mode) -> dict:
    rankings = [ranked_files(engine, q["query"], mode) for q in queries]
    expected = [q["expected_file"] for q in queries]
    hits_at_3 = [float(hit_at_k(r, e, 3)) for r, e in zip(rankings, expected)]
    return {
        "recall@1": recall_at_k(rankings, expected, 1),
        "recall@3": recall_at_k(rankings, expected, 3),
        "mrr": mrr(rankings, expected),
        "hits@1": sum(hit_at_k(r, e, 1) for r, e in zip(rankings, expected)),
        "hits@3": int(sum(hits_at_3)),
        "recall@3_ci95": bootstrap_interval(hits_at_3),
        "queries": [
            {
                "id": q["id"],
                "kind": q["kind"],
                "query": q["query"],
                "expected_file": q["expected_file"],
                "top_files": ranking[:3],
                "rank": first_rank(ranking, q["expected_file"]),
                "hit@1": hit_at_k(ranking, q["expected_file"], 1),
                "hit@3": hit_at_k(ranking, q["expected_file"], 3),
            }
            for q, ranking in zip(queries, rankings)
        ],
    }


def main() -> None:
    queries_file = Path(sys.argv[1]) if len(sys.argv) > 1 else QUERIES_FILE
    queries = json.loads(queries_file.read_text(encoding="utf-8"))
    engine = open_engine()
    report = {
        "query_count": len(queries),
        "queries_file": queries_file.name,
        "modes": {mode.value: evaluate_mode(engine, queries, mode) for mode in MODES},
    }
    write_json(DATA_DIR / "eval.json", report)
    for name, stats in report["modes"].items():
        low, high = stats["recall@3_ci95"]
        print(
            f"{name:7} top1={stats['hits@1']}/{len(queries)} top3={stats['hits@3']}/{len(queries)}"
            f" (95% CI {low:.2f}-{high:.2f}) mrr={stats['mrr']:.2f}"
        )
    for kind in sorted({q["kind"] for q in queries}):
        line = "  ".join(
            f"{name} {sum(r['hit@3'] for r in stats['queries'] if r['kind'] == kind)}"
            for name, stats in report["modes"].items()
        )
        print(f"top3 by kind [{kind}] {line} (of {sum(q['kind'] == kind for q in queries)})")


if __name__ == "__main__":
    main()
