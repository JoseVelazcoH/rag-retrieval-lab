from docsearch.constants import E5_MODEL, EMBEDDING_MODEL, QUERY_PREFIX
from docsearch.encoder import format_passage, format_query


def test_format_query_adds_bge_retrieval_instruction():
    assert format_query("slow site") == QUERY_PREFIX + "slow site"
    assert QUERY_PREFIX == "Represent this sentence for searching relevant passages: "


def test_format_passage_leaves_text_unchanged():
    assert format_passage("proxy_read_timeout 120s;") == "proxy_read_timeout 120s;"


def test_e5_uses_query_and_passage_prefixes():
    assert format_query("slow site", E5_MODEL) == "query: slow site"
    assert format_passage("proxy_read_timeout 120s;", E5_MODEL) == "passage: proxy_read_timeout 120s;"


def test_bge_model_name_matches_the_defaults():
    assert format_query("q", EMBEDDING_MODEL) == format_query("q")
    assert format_passage("p", EMBEDDING_MODEL) == "p"


def test_unknown_model_gets_no_prefixes():
    assert format_query("q", "some/other-model") == "q"
    assert format_passage("p", "some/other-model") == "p"
