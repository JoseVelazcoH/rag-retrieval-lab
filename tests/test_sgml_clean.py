import pytest

from docsearch.sgml_clean import (
    inline_includes,
    is_excluded_name,
    parse_system_entities,
    prepare_markdown,
    remove_empty_spans,
    remove_indexterms,
    replace_entities,
    starts_with_chapter,
)


def test_chapter_is_found_after_leading_comment():
    assert starts_with_chapter('<!-- doc/src/sgml/mvcc.sgml -->\n\n <chapter id="mvcc">\n')


@pytest.mark.parametrize("text", ['<!-- x -->\n<sect1 id="a">', "<refentry>", "", "<!-- only comment -->"])
def test_non_chapter_files_are_rejected(text):
    assert not starts_with_chapter(text)


@pytest.mark.parametrize(
    "name, excluded",
    [
        ("release-17", True),
        ("release", True),
        ("func-xml", True),
        ("catalogs", True),
        ("appendix-obsolete-auth-radius", True),
        ("mvcc", False),
        ("config", False),
        ("functions", True),
    ],
)
def test_excluded_names_follow_the_pre_registered_prefixes(name, excluded):
    assert is_excluded_name(name) is excluded


def test_multiline_nested_indexterm_is_removed():
    text = (
        "<para>Before</para>\n"
        '<indexterm zone="x">\n  <primary>a</primary>\n  <secondary>b</secondary>\n'
        "  <see>c</see>\n</indexterm>\n<para>After</para>"
    )
    assert remove_indexterms(text) == "<para>Before</para>\n\n<para>After</para>"


def test_self_closed_indexterm_is_removed_without_eating_following_content():
    text = '<indexterm zone="x"/><para>Keep</para><indexterm><primary>p</primary></indexterm>'
    assert remove_indexterms(text) == "<para>Keep</para>"


def test_paragraph_text_containing_the_word_indexterm_survives():
    assert remove_indexterms("<para>an indexterm is metadata</para>") == (
        "<para>an indexterm is metadata</para>"
    )


def test_system_entities_are_parsed_from_declarations():
    declarations = '<!ENTITY advanced   SYSTEM "advanced.sgml">\n<!ENTITY query SYSTEM "query.sgml">\n'
    assert parse_system_entities(declarations) == {
        "advanced": "advanced.sgml",
        "query": "query.sgml",
    }


def test_includes_are_inlined_recursively():
    files = {"a.sgml": "A &b;", "b.sgml": "B"}
    result = inline_includes("start &a; end", {"a": "a.sgml", "b": "b.sgml"}, files.get)
    assert result == "start A B end"


def test_unknown_unreadable_and_cyclic_includes_are_left_alone():
    files = {"loop.sgml": "&loop;"}
    includes = {"loop": "loop.sgml", "gone": "gone.sgml"}
    assert inline_includes("&nope; &gone;", includes, files.get) == "&nope; &gone;"
    assert "&loop;" in inline_includes("&loop;", includes, files.get)


def test_known_entities_become_numeric_references_or_text():
    assert replace_entities("a&mdash;b &version; x&zwsp;y") == "a&#8212;b current xy"


def test_xml_builtin_entities_are_preserved_and_unknown_ones_dropped():
    assert replace_entities("&lt;a&gt; &amp; &mystery;") == "&lt;a&gt; &amp; "


def test_empty_spans_are_removed_but_spans_with_content_stay():
    markdown = 'a<span class="indexterm"></span>b <span id="x"> </span>c <span>kept</span>'
    assert remove_empty_spans(markdown) == "ab c <span>kept</span>"


def test_prepared_markdown_collapses_blank_runs_and_ends_with_newline():
    assert prepare_markdown("# T\n\n\n\n\nbody<span></span>\n") == "# T\n\n\nbody\n"


def test_markdown_without_title_heading_is_rejected():
    with pytest.raises(ValueError):
        prepare_markdown("body only\n")
