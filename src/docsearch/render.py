import textwrap

from rich.console import Console
from rich.text import Text

from docsearch.constants import (
    SNIPPET_MAX_LINES,
    SNIPPET_MAX_ROWS,
    SNIPPET_MAX_WIDTH,
)
from docsearch.engine import Mode, Result, SearchResponse
from docsearch.text import find_term_spans, tokenize

FENCE = "```"
HIGHLIGHT_STYLE = "bold black on bright_yellow"
MODE_COLORS = {Mode.BM25: "cyan", Mode.VECTOR: "magenta", Mode.HYBRID: "green"}
SCORE_FORMATS = {Mode.BM25: "{:.1f}", Mode.VECTOR: "{:.2f}", Mode.HYBRID: "{:.4f}"}


def truncate(line: str, width: int) -> str:
    return line if len(line) <= width else line[: width - 1] + "…"


def wrap_rows(lines: list[str], width: int, max_rows: int) -> list[str]:
    rows = textwrap.wrap(" ".join(lines), width)
    if len(rows) <= max_rows:
        return rows
    kept = rows[:max_rows]
    kept[-1] = truncate(kept[-1] + "…", width) if len(kept[-1]) < width else truncate(kept[-1], width)
    return kept


def pick_snippet(
    text: str, terms: set[str], max_lines: int = SNIPPET_MAX_LINES
) -> list[str]:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(FENCE)
    ]
    start = min(_best_line_index(lines, terms), max(0, len(lines) - max_lines))
    return lines[start : start + max_lines]


def _best_line_index(lines: list[str], terms: set[str]) -> int:
    if not terms:
        return 0
    matches = [len(set(tokenize(line)) & terms) for line in lines]
    return matches.index(max(matches)) if max(matches) > 0 else 0


def render_response(
    console: Console, response: SearchResponse, query: str, mode: Mode
) -> None:
    color = MODE_COLORS[mode]
    console.print(f"[bold {color}]\\[{mode.value}][/] {response.elapsed_ms:.0f} ms")
    if not response.hits:
        console.print("[dim]no results[/]")
    terms = set(tokenize(query))
    for rank, result in enumerate(response.hits, start=1):
        console.print()
        console.print(_header(rank, result, mode))
        console.print(_snippet(result, terms))


def _header(rank: int, result: Result, mode: Mode) -> Text:
    chunk = result.chunk
    header = Text()
    header.append(f"{rank}. ", style="bold")
    header.append(f"{chunk.path}:{chunk.line}", style="bold underline")
    header.append(f"  score {SCORE_FORMATS[mode].format(result.score)}", style="dim")
    if mode is Mode.HYBRID:
        header.append("  " + "+".join(result.sources), style="green")
    return header


def _snippet(result: Result, terms: set[str]) -> Text:
    highlight = terms if "bm25" in result.sources else set()
    snippet = Text()
    lines = pick_snippet(result.chunk.text, highlight)
    for shown in wrap_rows(lines, SNIPPET_MAX_WIDTH, SNIPPET_MAX_ROWS):
        row = Text("   " + shown + "\n", style="white")
        for start, end in find_term_spans(shown, highlight):
            row.stylize(HIGHLIGHT_STYLE, start + 3, end + 3)
        snippet.append_text(row)
    snippet.rstrip()
    return snippet
