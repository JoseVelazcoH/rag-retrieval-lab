"""Build retrieval chunks from one clean markdown document in five variants.

All variants share one word budget: a "word" is a whitespace-separated token that
contains at least one letter or digit. Markdown syntax tokens (#, -, |, ---) weigh
zero, so the same content produces comparable chunk counts whichever variant is used.

Variants:
  plain           markdown syntax stripped, then fixed-size windows
  markdown_fixed  markdown kept as is, then fixed-size windows
  sections        one chunk per heading section (long ones split, tiny ones merged)
  sections_path   the same chunks with a "Doc title > H2 > H3" breadcrumb line on top
  markdown_fixed_120  control: markdown_fixed with windows sized like the average
                      section chunk, to separate "split at headings" from "smaller chunks"
"""
import re
from dataclasses import dataclass

from docsearch.md_clean import FENCE_PATTERN, split_fences

TARGET_WORDS = 200
OVERLAP_WORDS = 40
MIN_WORDS = 30
BREADCRUMB_SEPARATOR = " > "
# Control window: about the mean size of a "sections" chunk, overlap scaled by the same ratio.
CONTROL_TARGET_WORDS = 120
CONTROL_OVERLAP_WORDS = 24
VARIANTS = ("plain", "markdown_fixed", "markdown_fixed_120", "sections", "sections_path")

TOKEN_PATTERN = re.compile(r"\S+")
WORD_CHARACTER = re.compile(r"\w")
HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.*\S)[ \t]*$")
LIST_MARKER_PATTERN = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])[ \t]+")
QUOTE_MARKER_PATTERN = re.compile(r"^\s*>+[ \t]?")
HEADING_MARKER_PATTERN = re.compile(r"^\s{0,3}#{1,6}[ \t]+")
TABLE_RULE_PATTERN = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*(?::?-+:?\s*)?$")
RULE_PATTERN = re.compile(r"^\s*([-*_])\1{2,}\s*$")
CODE_SPAN_PATTERN =re.compile(r"(`+[^`]+`+)")
EMPHASIS_PATTERN = re.compile(r"\*+|(?<!\w)_+|_+(?!\w)")


@dataclass(frozen=True)
class Section:
    path: tuple[str, ...]
    text: str


def count_words(text: str) -> int:
    return sum(1 for token in text.split() if WORD_CHARACTER.search(token))


def fixed_chunks(text: str, target: int = TARGET_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    """Windows of `target` words overlapping by `overlap`, keeping original whitespace."""
    spans = [m.span() for m in TOKEN_PATTERN.finditer(text)]
    weights = [1 if WORD_CHARACTER.search(text[s:e]) else 0 for s, e in spans]
    chunks: list[str] = []
    start = 0
    while start < len(spans):
        end, used = start, 0
        while end < len(spans) and used < target:
            used += weights[end]
            end += 1
        if used:
            chunks.append(text[spans[start][0] : spans[end - 1][1]])
        if not any(weights[end:]):
            break
        start = _overlap_start(weights, start, end, overlap)
    return chunks


def _overlap_start(weights: list[int], start: int, end: int, overlap: int) -> int:
    back, kept = end, 0
    while back > start + 1 and kept < overlap:
        back -= 1
        kept += weights[back]
    return back


def strip_inline(line: str) -> str:
    """Remove inline markdown from one line, keeping the text of code spans."""
    parts = CODE_SPAN_PATTERN.split(line)
    cleaned = [
        part.strip("`") if index % 2 else EMPHASIS_PATTERN.sub("", part).replace("|", " ")
        for index, part in enumerate(parts)
    ]
    return "".join(cleaned)


def strip_markdown(text: str) -> str:
    """Plain text: no heading marks, emphasis, list markers, quotes, table pipes or fences."""
    lines: list[str] = []
    for is_code, block in split_fences(text):
        if is_code:
            lines.extend(_code_lines(block))
        else:
            lines.extend(_strip_prose_line(line) for line in block.splitlines())
    return "\n".join(lines) + "\n"


def _code_lines(block: str) -> list[str]:
    """Code text without its opening and closing fence lines."""
    body = block.splitlines()[1:]
    if body and FENCE_PATTERN.match(body[-1]) and not body[-1].strip().strip("`~"):
        body.pop()
    return body


def _strip_prose_line(line: str) -> str:
    if TABLE_RULE_PATTERN.match(line) or RULE_PATTERN.match(line):
        return ""
    for pattern in (HEADING_MARKER_PATTERN, QUOTE_MARKER_PATTERN):
        line = pattern.sub("", line)
    line = LIST_MARKER_PATTERN.sub(r"\1", line)
    return strip_inline(line).strip()


def parse_sections(text: str) -> list[Section]:
    """Heading-delimited sections: heading line plus body, with the heading path."""
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    path: tuple[str, ...] = ()
    current: list[str] = []

    def flush() -> None:
        body = "".join(current).strip()
        if body:
            sections.append(Section(path, body))

    for is_code, block in split_fences(text):
        if is_code:
            current.append(block)
            continue
        for line in block.splitlines(keepends=True):
            match = HEADING_PATTERN.match(line.rstrip("\n"))
            if not match:
                current.append(line)
                continue
            flush()
            current = [line]
            level = len(match.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, strip_inline(match.group(2)).strip()))
            path = tuple(title for _, title in stack)
    flush()
    return sections


def merge_small(sections: list[Section]) -> list[Section]:
    """Merge sections under MIN_WORDS into the following one (a short tail joins the previous)."""
    merged: list[Section] = []
    pending: Section | None = None
    for section in sections:
        if pending is not None:
            section = Section(pending.path, f"{pending.text}\n\n{section.text}")
            pending = None
        if count_words(section.text) < MIN_WORDS:
            pending = section
        else:
            merged.append(section)
    if pending is not None:
        if merged:
            last = merged.pop()
            merged.append(Section(last.path, f"{last.text}\n\n{pending.text}"))
        else:
            merged.append(pending)
    return merged


def split_long(section: Section) -> list[Section]:
    """Split a section over TARGET_WORDS into pieces that each repeat the heading line."""
    if count_words(section.text) <= TARGET_WORDS:
        return [section]
    heading, _, body = section.text.partition("\n")
    budget = max(TARGET_WORDS - count_words(heading), OVERLAP_WORDS * 2)
    return [
        Section(section.path, f"{heading}\n{piece}")
        for piece in fixed_chunks(body, budget, OVERLAP_WORDS)
    ]


def section_chunks(text: str) -> list[Section]:
    return [piece for section in merge_small(parse_sections(text)) for piece in split_long(section)]


def build_chunks(variant: str, doc: str, text: str) -> list[dict]:
    """Chunks for one clean markdown document as {"doc": relpath, "text": ...} dicts."""
    return [{"doc": doc, "text": chunk} for chunk in _variant_texts(variant, text)]


def _variant_texts(variant: str, text: str) -> list[str]:
    if variant == "plain":
        return fixed_chunks(strip_markdown(text))
    if variant == "markdown_fixed":
        return fixed_chunks(text)
    if variant == "markdown_fixed_120":
        return fixed_chunks(text, CONTROL_TARGET_WORDS, CONTROL_OVERLAP_WORDS)
    if variant == "sections":
        return [s.text for s in section_chunks(text)]
    if variant == "sections_path":
        return [_with_breadcrumb(s) for s in section_chunks(text)]
    raise ValueError(f"Unknown variant {variant!r}. Choose from {', '.join(VARIANTS)}.")


def _with_breadcrumb(section: Section) -> str:
    if not section.path:
        return section.text
    return f"{BREADCRUMB_SEPARATOR.join(section.path)}\n{section.text}"


def build_all(variant: str, documents: dict[str, str]) -> list[dict]:
    return [chunk for doc, text in documents.items() for chunk in build_chunks(variant, doc, text)]
