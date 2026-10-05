"""Decide whether a retrieved chunk contains the answer to a question.

A chunk is a hit when the normalized answer quote is a substring of the normalized
chunk text. Chunking can cut a quote in two, so a fallback also counts a chunk that
holds, as a contiguous run of words, the first or the last PARTIAL_SHARE of the
quote's words. The fallback needs at least MIN_PARTIAL_WORDS words so a short
fragment cannot match by accident. Hits are judged on text only, not on the document
path, so identical text in two documents counts for both.
"""
import math
import re

SYNTAX_PATTERN = re.compile(r"[#*_`|>]")
PARTIAL_SHARE = 0.6
MIN_PARTIAL_WORDS = 4


def normalize(text: str) -> str:
    """Lowercase, drop markdown syntax characters (#*_`|>) and collapse whitespace."""
    return " ".join(SYNTAX_PATTERN.sub("", text.lower()).split())


def quote_in_chunk(quote: str, chunk_text: str) -> bool:
    """The whole quote sits inside the chunk."""
    return normalize(quote) in normalize(chunk_text)


def _contains_run(words: list[str], run: list[str]) -> bool:
    size = len(run)
    return any(words[i : i + size] == run for i in range(len(words) - size + 1))


def partial_quote_in_chunk(quote: str, chunk_text: str) -> bool:
    """The chunk holds the first or the last 60% of the quote's words, contiguously."""
    quote_words = normalize(quote).split()
    share = math.ceil(PARTIAL_SHARE * len(quote_words))
    if share < MIN_PARTIAL_WORDS:
        return False
    chunk_words = normalize(chunk_text).split()
    return _contains_run(chunk_words, quote_words[:share]) or _contains_run(
        chunk_words, quote_words[-share:]
    )


def is_hit(quote: str, chunk_text: str) -> bool:
    return quote_in_chunk(quote, chunk_text) or partial_quote_in_chunk(quote, chunk_text)


def first_hit_rank(quote: str, chunk_texts: list[str]) -> int | None:
    """1-based rank of the first hit chunk, or None when no chunk is a hit."""
    for rank, text in enumerate(chunk_texts, start=1):
        if is_hit(quote, text):
            return rank
    return None
