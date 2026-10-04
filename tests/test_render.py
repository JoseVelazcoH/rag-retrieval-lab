from docsearch.render import pick_snippet, truncate, wrap_rows

TEXT = """## Title

first line
```nginx
proxy_read_timeout 60s;
other line
last line
```"""


def test_pick_snippet_without_terms_starts_at_first_content_line():
    assert pick_snippet(TEXT, set(), max_lines=2) == ["## Title", "first line"]


def test_pick_snippet_skips_fence_markers_and_blank_lines():
    lines = pick_snippet(TEXT, set(), max_lines=10)
    assert "```nginx" not in lines
    assert "" not in lines


def test_pick_snippet_starts_at_line_with_most_matching_terms():
    snippet = pick_snippet(TEXT, {"proxy_read_timeout", "60s"}, max_lines=2)
    assert snippet == ["proxy_read_timeout 60s;", "other line"]


def test_truncate_adds_ellipsis_only_when_too_long():
    assert truncate("short", 10) == "short"
    assert truncate("abcdefghij", 6) == "abcde…"


def test_pick_snippet_fills_the_window_when_best_line_is_last():
    snippet = pick_snippet(TEXT, {"last"}, max_lines=3)
    assert snippet == ["proxy_read_timeout 60s;", "other line", "last line"]


def test_wrap_rows_wraps_long_lines_on_word_boundaries():
    rows = wrap_rows(["uno dos tres cuatro cinco"], width=12, max_rows=5)
    assert rows == ["uno dos tres", "cuatro cinco"]


def test_wrap_rows_caps_total_rows_with_ellipsis():
    rows = wrap_rows(["uno dos tres cuatro cinco seis"], width=8, max_rows=2)
    assert rows == ["uno dos", "tres…"]


def test_wrap_rows_reflows_consecutive_lines_as_one_paragraph():
    assert wrap_rows(["a b", "c d"], width=10, max_rows=5) == ["a b c d"]
