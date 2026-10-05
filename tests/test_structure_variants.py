import pytest

from docsearch.structure_variants import (
    MIN_WORDS,
    OVERLAP_WORDS,
    TARGET_WORDS,
    VARIANTS,
    Section,
    build_all,
    build_chunks,
    count_words,
    fixed_chunks,
    merge_small,
    parse_sections,
    section_chunks,
    split_long,
    strip_markdown,
)


def words(count: int, prefix: str = "w") -> str:
    return " ".join(f"{prefix}{i}" for i in range(count))


def test_constants_match_the_experiment_design():
    assert (TARGET_WORDS, OVERLAP_WORDS, MIN_WORDS) == (200, 40, 30)


def test_markdown_symbols_do_not_count_as_words():
    assert count_words("## Title\n- a | b ---") == 3


def test_empty_text_has_no_chunks():
    assert fixed_chunks("") == []
    assert fixed_chunks("  \n ") == []


def test_short_text_is_one_chunk():
    assert fixed_chunks("one two three") == ["one two three"]


def test_fixed_chunks_overlap_by_forty_words():
    chunks = fixed_chunks(words(450))
    assert [count_words(c) for c in chunks] == [200, 200, 130]
    assert chunks[1].split()[0] == "w160"
    assert chunks[2].split()[-1] == "w449"


def test_fixed_chunks_keep_line_breaks():
    chunk = fixed_chunks("# Title\n\n- a\n- b")[0]
    assert chunk == "# Title\n\n- a\n- b"


def test_symbol_tokens_do_not_consume_the_budget():
    def items(n):
        return "\n".join(f"- w{i}" for i in range(n))

    assert len(fixed_chunks(items(200))) == 1
    assert len(fixed_chunks(items(201))) == 2


def test_trailing_symbols_do_not_create_an_extra_chunk():
    assert len(fixed_chunks(words(200) + "\n---\n")) == 1


def test_strip_markdown_removes_syntax_but_keeps_words():
    text = "## Heading\n\n- item **bold** and `code_span`\n1. _emph_ kube_proxy\n\n> quoted\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    plain = strip_markdown(text)
    for symbol in ("#", "**", "`", "|", "> ", "- ", "1."):
        assert symbol not in plain
    assert plain.split() == ["Heading", "item", "bold", "and", "code_span", "emph", "kube_proxy", "quoted", "a", "b", "1", "2"]


def test_strip_markdown_keeps_code_text_and_drops_fences():
    text = "intro\n```bash\n# keep\nrun it\n```\nafter\n"
    assert strip_markdown(text) == "intro\n# keep\nrun it\nafter\n"


def test_sections_follow_heading_hierarchy():
    doc = "# T\n\nintro\n\n## A\n\nbody a\n\n### B\n\nbody b\n\n## C\n\nbody c\n"
    sections = parse_sections(doc)
    assert [s.path for s in sections] == [("T",), ("T", "A"), ("T", "A", "B"), ("T", "C")]
    assert sections[1].text == "## A\n\nbody a"


def test_headings_inside_code_fences_are_not_sections():
    sections = parse_sections("# T\n\n```bash\n# not a heading\n```\n")
    assert len(sections) == 1


def test_small_section_merges_into_the_following_one():
    doc = f"# T\n\n## A\n\n{words(40)}\n"
    merged = merge_small(parse_sections(doc))
    assert len(merged) == 1
    assert merged[0].path == ("T",)
    assert merged[0].text.startswith("# T\n\n## A")


def test_small_trailing_section_joins_the_previous_one():
    doc = f"# T\n\n{words(40)}\n\n## A\n\nshort\n"
    merged = merge_small(parse_sections(doc))
    assert len(merged) == 1
    assert merged[0].text.endswith("short")


def test_long_section_is_split_with_the_heading_repeated():
    pieces = split_long(Section(("T",), "## Big\n\n" + words(450)))
    assert len(pieces) == 3
    assert all(p.text.startswith("## Big\n") for p in pieces)
    assert max(count_words(p.text) for p in pieces) <= TARGET_WORDS


def test_section_within_budget_is_not_split():
    section = Section(("T",), "## A\n\n" + words(150))
    assert split_long(section) == [section]


def test_sections_variant_has_one_chunk_per_heading_section():
    doc = f"# Title\n\n{words(40)}\n\n## Sub\n\n{words(40, 'x')}\n"
    chunks = build_chunks("sections", "a.md", doc)
    assert [c["doc"] for c in chunks] == ["a.md", "a.md"]
    assert chunks[0]["text"].startswith("# Title")
    assert chunks[1]["text"].startswith("## Sub")


def test_sections_path_prefixes_a_breadcrumb():
    doc = f"# Title\n\n{words(40)}\n\n## Sub\n\n{words(40, 'x')}\n"
    chunks = build_chunks("sections_path", "a.md", doc)
    assert chunks[0]["text"].startswith("Title\n# Title")
    assert chunks[1]["text"].startswith("Title > Sub\n## Sub")


def test_sections_path_uses_the_same_chunks_as_sections():
    doc = f"# T\n\n{words(40)}\n\n## A\n\n{words(300, 'y')}\n"
    plain_sections = [c["text"] for c in build_chunks("sections", "a.md", doc)]
    with_path = [c["text"] for c in build_chunks("sections_path", "a.md", doc)]
    assert len(plain_sections) == len(with_path)
    assert all(p.endswith(s) for p, s in zip(with_path, plain_sections))


def test_plain_and_markdown_fixed_have_comparable_chunk_counts():
    doc = "# T\n\n" + "\n".join(f"- item{i}" for i in range(450)) + "\n"
    plain = build_chunks("plain", "a.md", doc)
    markdown = build_chunks("markdown_fixed", "a.md", doc)
    assert len(plain) == len(markdown) == 3


def test_every_variant_produces_chunks():
    doc = f"# T\n\n{words(60)}\n\n## A\n\n{words(60, 'x')}\n"
    for variant in VARIANTS:
        assert build_chunks(variant, "a.md", doc)


def test_unknown_variant_is_rejected():
    with pytest.raises(ValueError):
        build_chunks("nope", "a.md", "# T\n")


def test_build_all_tags_every_chunk_with_its_document():
    docs = {"a.md": f"# A\n\n{words(40)}\n", "b.md": f"# B\n\n{words(40)}\n"}
    chunks = build_all("markdown_fixed", docs)
    assert [c["doc"] for c in chunks] == ["a.md", "b.md"]


def test_section_chunks_returns_sections():
    assert section_chunks(f"# T\n\n{words(40)}\n")[0].path == ("T",)


def test_control_variant_uses_smaller_fixed_windows():
    text = " ".join(f"w{i}" for i in range(400))
    small = build_chunks("markdown_fixed_120", "d.md", text)
    large = build_chunks("markdown_fixed", "d.md", text)
    assert len(small) > len(large)
    assert all(count_words(c["text"]) <= 120 for c in small)
