from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from docsearch.constants import (
    DEFAULT_DOCS_DIR,
    DEFAULT_INDEX_DIR,
    DEFAULT_TOP_K,
)
from docsearch.encoder import Encoder, silence_libraries
from docsearch.engine import Mode, SearchEngine, build_index
from docsearch.render import render_response

app = typer.Typer(add_completion=False, help="Local BM25 + vector document search.")
console = Console()


def resolve_mode(bm25: bool, vector: bool, hybrid: bool) -> Mode:
    chosen = [m for m, on in ((Mode.BM25, bm25), (Mode.VECTOR, vector), (Mode.HYBRID, hybrid)) if on]
    if len(chosen) > 1:
        raise typer.BadParameter("Pick only one of --bm25, --vector, --hybrid.")
    return chosen[0] if chosen else Mode.HYBRID


@app.command()
def index(
    docs: Annotated[Path, typer.Option(help="Folder with markdown files.")] = DEFAULT_DOCS_DIR,
    index_dir: Annotated[Path, typer.Option(help="Where to store the index.")] = DEFAULT_INDEX_DIR,
) -> None:
    """Chunk the documents and precompute the BM25 and vector indexes."""
    silence_libraries()
    with console.status("Embedding chunks..."):
        count = build_index(docs, index_dir, Encoder())
    console.print(f"Indexed {count} chunks into {index_dir}/")


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="What to look for.")],
    bm25: Annotated[bool, typer.Option("--bm25", help="Keyword search only.")] = False,
    vector: Annotated[bool, typer.Option("--vector", help="Semantic search only.")] = False,
    hybrid: Annotated[bool, typer.Option("--hybrid", help="BM25 + vectors with RRF (default).")] = False,
    k: Annotated[int, typer.Option("-k", help="Number of results.")] = DEFAULT_TOP_K,
    index_dir: Annotated[Path, typer.Option(help="Index location.")] = DEFAULT_INDEX_DIR,
) -> None:
    """Search the indexed documents."""
    mode = resolve_mode(bm25, vector, hybrid)
    silence_libraries()
    engine = SearchEngine(index_dir, encoder_factory=Encoder)
    engine.warm_up(mode)
    response = engine.search(query, mode, k)
    render_response(console, response, query, mode)


def run_search() -> None:
    """Entry point for the bare `search "query"` command."""
    typer.run(search)


if __name__ == "__main__":
    app()
