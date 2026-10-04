from pathlib import Path

from docsearch.corpus import chunk_markdown, load_corpus

SAMPLE = """# Title

Intro paragraph
second line.

## Section

Body of the section.

```nginx
location / {

    proxy_read_timeout 60s;
}
```

Last paragraph.
"""


def test_chunk_markdown_records_starting_line_of_each_chunk():
    chunks = chunk_markdown(SAMPLE, "a.md")
    assert [(c.path, c.line) for c in chunks] == [
        ("a.md", 1),
        ("a.md", 6),
        ("a.md", 10),
        ("a.md", 17),
    ]


def test_chunk_markdown_attaches_heading_to_following_paragraph():
    chunks = chunk_markdown(SAMPLE, "a.md")
    assert chunks[0].text == "# Title\n\nIntro paragraph\nsecond line."
    assert chunks[1].text == "## Section\n\nBody of the section."


def test_chunk_markdown_keeps_fenced_code_block_together():
    chunks = chunk_markdown(SAMPLE, "a.md")
    assert "proxy_read_timeout 60s;" in chunks[2].text
    assert chunks[2].text.startswith("```nginx")
    assert chunks[2].text.endswith("```")


def test_chunk_markdown_empty_text_yields_no_chunks():
    assert chunk_markdown("\n\n", "a.md") == []


def test_load_corpus_uses_paths_relative_to_docs_dir(tmp_path: Path):
    (tmp_path / "runbooks").mkdir()
    (tmp_path / "runbooks" / "nginx.md").write_text("hello\n", encoding="utf-8")
    (tmp_path / "top.md").write_text("bye\n", encoding="utf-8")

    chunks = load_corpus(tmp_path)

    assert [c.path for c in chunks] == ["runbooks/nginx.md", "top.md"]
