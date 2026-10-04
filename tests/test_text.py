import pytest

from docsearch.text import find_term_spans, normalize, tokenize


def test_normalize_lowercases_and_strips_accents():
    assert normalize("Café RÉSUMÉ") == "cafe resume"


def test_tokenize_drops_stopwords_and_punctuation():
    assert tokenize("The page takes forever, and then it crashes!") == [
        "page",
        "takes",
        "forever",
        "crashes",
    ]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("timeout 504", ["timeout", "504"]),
        ("proxy_read_timeout 60s", ["proxy", "read", "timeout", "60s"]),
        ("", []),
        ("the of a", []),
        ("I can't log in", ["log"]),
    ],
)
def test_tokenize_handles_identifiers_contractions_and_empty_input(text, expected):
    assert tokenize(text) == expected


def test_find_term_spans_matches_accent_insensitively():
    text = "Check the café menu"
    spans = find_term_spans(text, {"cafe"})
    assert [text[start:end] for start, end in spans] == ["café"]


def test_find_term_spans_returns_nothing_without_match():
    assert find_term_spans("hello world", {"nginx"}) == []
