from docsearch.quote_match import (
    first_hit_rank,
    is_hit,
    normalize,
    partial_quote_in_chunk,
    quote_in_chunk,
)

QUOTE = "A Pod is the smallest deployable unit of computing that you can create and manage in Kubernetes"


def test_normalize_lowercases_strips_syntax_and_collapses_whitespace():
    assert normalize("## A  `Pod`\n| is *the* _unit_ >") == "a pod is the unit"


def test_quote_is_found_through_markdown_differences():
    chunk = "# Pods\n\nA **Pod** is the smallest deployable unit of `computing`\nthat you can create and manage in Kubernetes."
    assert quote_in_chunk(QUOTE, chunk)


def test_unrelated_chunk_is_not_a_hit():
    assert not is_hit(QUOTE, "Nodes run containers for the cluster and report status to the control plane.")


def test_quote_split_across_chunks_hits_through_the_first_part():
    first_part = "intro text. A Pod is the smallest deployable unit of computing that you can create"
    assert not quote_in_chunk(QUOTE, first_part)
    assert partial_quote_in_chunk(QUOTE, first_part)
    assert is_hit(QUOTE, first_part)


def test_quote_split_across_chunks_hits_through_the_last_part():
    second_part = "unit of computing that you can create and manage in Kubernetes and more text follows"
    assert partial_quote_in_chunk(QUOTE, second_part)


def test_less_than_sixty_percent_is_not_a_hit():
    fragment = "A Pod is the smallest deployable"
    assert not partial_quote_in_chunk(QUOTE, fragment)


def test_partial_match_must_be_contiguous():
    scattered = "A Pod is the smallest unit deployable of computing that you can create"
    assert not partial_quote_in_chunk(QUOTE, scattered)


def test_short_quotes_never_use_the_partial_fallback():
    assert not partial_quote_in_chunk("restart the pod", "restart the")
    assert is_hit("restart the pod", "Then restart the pod now.")


def test_partial_match_respects_word_boundaries():
    quote = "one two three four five six seven"
    assert not partial_quote_in_chunk(quote, "xone two three four five six")


def test_first_hit_rank_is_one_based():
    chunks = ["nothing here", "still nothing", f"yes: {QUOTE}"]
    assert first_hit_rank(QUOTE, chunks) == 3


def test_first_hit_rank_is_none_without_a_hit():
    assert first_hit_rank(QUOTE, ["nothing", "else"]) is None
