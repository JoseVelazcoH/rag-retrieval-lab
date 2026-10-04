import re
import unicodedata

from docsearch.constants import STOPWORDS

WORD_PATTERN = re.compile(r"[^\W_]+")


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    words = WORD_PATTERN.findall(normalize(text))
    return [word for word in words if word not in STOPWORDS]


def find_term_spans(text: str, terms: set[str]) -> list[tuple[int, int]]:
    return [
        match.span()
        for match in WORD_PATTERN.finditer(text)
        if normalize(match.group()) in terms
    ]
