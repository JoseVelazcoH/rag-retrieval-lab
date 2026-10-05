import pytest

from docsearch.hybrid import RRF_K, fuse_rankings


def test_fuse_rankings_scores_with_reciprocal_rank():
    hits = fuse_rankings({"bm25": [7, 3], "vector": [7]})
    top = hits[0]
    assert top.chunk_id == 7
    assert top.score == pytest.approx(2 / (RRF_K + 1))


def test_fuse_rankings_reports_contributing_methods():
    hits = {h.chunk_id: h for h in fuse_rankings({"bm25": [1, 2], "vector": [2, 3]})}
    assert hits[1].sources == ("bm25",)
    assert hits[2].sources == ("bm25", "vector")
    assert hits[3].sources == ("vector",)


def test_fuse_rankings_rewards_agreement_over_single_first_place():
    hits = fuse_rankings({"bm25": [1, 2], "vector": [3, 2]})
    assert hits[0].chunk_id == 2


def test_fuse_rankings_with_no_rankings_is_empty():
    assert fuse_rankings({}) == []


def test_weights_scale_each_method_contribution():
    hits = fuse_rankings({"bm25": [1], "vector": [2]}, {"bm25": 0.3, "vector": 0.7})
    assert [h.chunk_id for h in hits] == [2, 1]
    assert hits[0].score == pytest.approx(0.7 / (RRF_K + 1))


def test_vector_heavy_weights_let_vector_order_win_a_tie():
    rankings = {"bm25": [1, 2], "vector": [2, 1]}
    assert fuse_rankings(rankings, {"bm25": 0.3, "vector": 0.7})[0].chunk_id == 2


def test_missing_weight_defaults_to_one():
    assert fuse_rankings({"bm25": [5]}, {"vector": 0.7})[0].score == pytest.approx(1 / (RRF_K + 1))
