import pytest

from docsearch.md_clean import (
    clean_body,
    clean_document,
    collapse_blank_lines,
    extract_title,
    remove_html_comments,
    replace_shortcodes,
    split_fences,
    split_front_matter,
    strip_links,
)


def test_front_matter_is_split_from_body():
    front, body = split_front_matter("---\ntitle: Pods\nweight: 10\n---\nBody text\n")
    assert front == "title: Pods\nweight: 10"
    assert body == "Body text\n"


def test_file_without_front_matter_keeps_everything_as_body():
    assert split_front_matter("Just text\n") == ("", "Just text\n")


@pytest.mark.parametrize(
    "front, expected",
    [
        ("title: Pods", "Pods"),
        ('title: "Services, Load Balancing"', "Services, Load Balancing"),
        ("title:    Spaced Out", "Spaced Out"),
        ("weight: 3\ntitle: 'Quoted'", "Quoted"),
    ],
)
def test_title_is_read_from_front_matter(front, expected):
    assert extract_title(front) == expected


def test_missing_title_is_none():
    assert extract_title("weight: 3") is None


def test_glossary_tooltip_becomes_its_text():
    text = 'Run {{< glossary_tooltip text="Pods" term_id="pod" >}} here'
    assert replace_shortcodes(text) == "Run Pods here"


def test_glossary_tooltip_without_text_uses_term_id():
    assert replace_shortcodes('A {{< glossary_tooltip term_id="node" >}} fails') == "A node fails"


def test_percent_delimiters_are_handled():
    assert replace_shortcodes('x {{% glossary_tooltip text="Pod" term_id="pod" %}} y') == "x Pod y"


def test_inline_shortcodes_are_removed():
    text = 'Intro\n{{< feature-state for_k8s_version="v1.20" state="stable" >}}\nMore'
    assert replace_shortcodes(text) == "Intro\n\nMore"


def test_block_shortcodes_keep_inner_content():
    text = "{{< note >}}\nKeep this.\n{{< /note >}}"
    assert replace_shortcodes(text).split() == ["Keep", "this."]


def test_closing_tag_without_spaces_is_removed():
    assert replace_shortcodes("{{<warning>}}Careful{{</warning>}}") == "Careful"


def test_percent_block_shortcode_keeps_inner_content():
    assert replace_shortcodes("{{% tab name=\"a\" %}}Inner{{% /tab %}}") == "Inner"


def test_comment_shortcode_block_is_dropped_entirely():
    text = "Before {{< comment >}}authoring note{{< /comment >}} after"
    assert replace_shortcodes(text) == "Before  after"


def test_html_comments_are_removed_including_multiline():
    assert remove_html_comments("a <!-- overview --> b <!--\nx\n--> c") == "a  b  c"


def test_links_keep_their_text():
    assert strip_links("See [the docs](/docs/concepts/) now") == "See the docs now"


def test_link_urls_with_parentheses_are_removed_whole():
    assert strip_links("[Go](https://x.io/a_(b)) ok") == "Go ok"


def test_link_with_title_attribute():
    assert strip_links('[Go](/a "Title") ok') == "Go ok"


def test_images_keep_alt_text():
    assert strip_links("![diagram](/img/a.png)") == "diagram"


def test_bracketed_text_without_url_is_untouched():
    assert strip_links("`[eviction-signal][operator]`") == "`[eviction-signal][operator]`"


def test_three_blank_lines_collapse_to_two():
    assert collapse_blank_lines("a\n\n\n\nb") == "a\n\n\nb"


def test_two_blank_lines_are_kept():
    assert collapse_blank_lines("a\n\n\nb") == "a\n\n\nb"


def test_fences_are_split_into_code_and_prose():
    text = "intro\n```yaml\na: 1\n```\nafter\n"
    assert split_fences(text) == [
        (False, "intro\n"),
        (True, "```yaml\na: 1\n```\n"),
        (False, "after\n"),
    ]


def test_longer_fence_is_not_closed_by_a_shorter_one():
    text = "````\n```\ninner\n```\n````\n"
    assert split_fences(text) == [(True, text)]


def test_code_blocks_are_not_cleaned():
    body = "```\n[a](b) {{< x >}} <!-- c -->\n```\n"
    assert clean_body(body) == body.strip()


def test_clean_document_starts_with_title_and_drops_front_matter():
    raw = '---\ntitle: "Pods"\nweight: 1\n---\n<!-- overview -->\nA {{< glossary_tooltip text="Pod" term_id="pod" >}}.\n'
    text, words = clean_document(raw, "fallback")
    assert text == "# Pods\n\nA Pod.\n"
    assert words == 2


def test_clean_document_uses_fallback_title():
    text, _ = clean_document("---\nweight: 1\n---\nBody\n", "fallback")
    assert text.startswith("# fallback\n")


def test_headings_lists_and_tables_survive():
    raw = "---\ntitle: T\n---\n## H\n\n- a\n- b\n\n| x | y |\n|---|---|\n| 1 | 2 |\n"
    text, _ = clean_document(raw, "t")
    assert "## H" in text and "- a" in text and "| x | y |" in text
