from pathlib import Path

from docsearch.models import Chunk

FENCE = "```"
HEADING_MARK = "#"

Block = tuple[int, list[str]]


def split_blocks(text: str) -> list[Block]:
    """Split on blank lines, never inside a fenced code block."""
    blocks: list[Block] = []
    current: list[str] = []
    start = 1
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith(FENCE):
            in_fence = not in_fence
        if line.strip() == "" and not in_fence:
            if current:
                blocks.append((start, current))
                current = []
            continue
        if not current:
            start = number
        current.append(line)
    if current:
        blocks.append((start, current))
    return blocks


def is_heading_only(lines: list[str]) -> bool:
    return len(lines) == 1 and lines[0].startswith(HEADING_MARK)


def chunk_markdown(text: str, path: str) -> list[Chunk]:
    """One chunk per paragraph, with its heading attached when it has one."""
    chunks: list[Chunk] = []
    heading: Block | None = None
    for start, lines in split_blocks(text):
        if is_heading_only(lines):
            if heading:
                chunks.append(_to_chunk(path, heading[0], heading[1]))
            heading = (start, lines)
            continue
        if heading:
            start, lines = heading[0], heading[1] + [""] + lines
            heading = None
        chunks.append(_to_chunk(path, start, lines))
    if heading:
        chunks.append(_to_chunk(path, heading[0], heading[1]))
    return chunks


def _to_chunk(path: str, line: int, lines: list[str]) -> Chunk:
    return Chunk(path=path, line=line, text="\n".join(lines))


def load_corpus(docs_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for file in sorted(docs_dir.rglob("*.md")):
        relative = file.relative_to(docs_dir).as_posix()
        chunks.extend(chunk_markdown(file.read_text(encoding="utf-8"), relative))
    return chunks
