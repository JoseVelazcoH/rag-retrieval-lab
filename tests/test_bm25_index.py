from docsearch.bm25_index import Bm25Index

DOCS = [
    "nginx returns 504 gateway timeout from the proxy",
    "vacation policy and days off",
    "rotate the jwt token signing key",
]


def test_search_ranks_document_sharing_keywords_first():
    index = Bm25Index.build(DOCS)
    hits = index.search("timeout 504 nginx", k=3)
    assert hits[0].chunk_id == 0


def test_search_ignores_accents_in_query():
    index = Bm25Index.build(["the café policy", "other text"])
    hits = index.search("cafe", k=2)
    assert [h.chunk_id for h in hits] == [0]


def test_search_omits_documents_with_zero_score():
    index = Bm25Index.build(DOCS)
    assert index.search("kubernetes", k=3) == []


def test_index_round_trips_through_disk(tmp_path):
    Bm25Index.build(DOCS).save(tmp_path)
    loaded = Bm25Index.load(tmp_path)
    assert loaded.search("vacation", k=1)[0].chunk_id == 1
