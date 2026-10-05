from docsearch.embedding_cache import chunk_key


def test_key_is_stable_for_same_inputs():
    assert chunk_key("m", ["a", "b"]) == chunk_key("m", ["a", "b"])


def test_key_changes_with_model_text_or_order():
    base = chunk_key("m", ["a", "b"])
    assert chunk_key("other", ["a", "b"]) != base
    assert chunk_key("m", ["a", "c"]) != base
    assert chunk_key("m", ["b", "a"]) != base


def test_chunk_boundaries_matter():
    assert chunk_key("m", ["ab", "c"]) != chunk_key("m", ["a", "bc"])
