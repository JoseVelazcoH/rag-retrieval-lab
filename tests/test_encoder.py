from docsearch.constants import QUERY_PREFIX
from docsearch.encoder import format_passage, format_query


def test_format_query_adds_bge_retrieval_instruction():
    assert format_query("slow site") == QUERY_PREFIX + "slow site"
    assert QUERY_PREFIX == "Represent this sentence for searching relevant passages: "


def test_format_passage_leaves_text_unchanged():
    assert format_passage("proxy_read_timeout 120s;") == "proxy_read_timeout 120s;"
