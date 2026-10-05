import pytest

from docsearch.evaluation import (
    bootstrap_interval,
    dedupe_ranking,
    first_rank,
    first_rank_any,
    hit_at_k,
    mrr,
    parse_qrels,
    recall_at_k,
    reciprocal_rank,
    sign_test_p_value,
)


def test_first_rank_is_one_based():
    assert first_rank(["a", "b", "c"], "b") == 2


def test_first_rank_is_none_when_missing():
    assert first_rank(["a", "b"], "z") is None


def test_reciprocal_rank_halves_at_second_position():
    assert reciprocal_rank(["a", "b"], "b") == 0.5


def test_reciprocal_rank_is_zero_when_missing():
    assert reciprocal_rank(["a"], "z") == 0.0


def test_hit_at_k_respects_the_cutoff():
    assert hit_at_k(["a", "b", "c"], "c", 3)
    assert not hit_at_k(["a", "b", "c"], "c", 2)


def test_recall_at_k_is_the_share_of_queries_with_a_hit():
    rankings = [["a", "b"], ["x", "a"], ["x", "y"]]
    expected = ["a", "a", "a"]
    assert recall_at_k(rankings, expected, 1) == pytest.approx(1 / 3)
    assert recall_at_k(rankings, expected, 2) == pytest.approx(2 / 3)


def test_mrr_averages_reciprocal_ranks():
    rankings = [["a", "b"], ["x", "a"], ["x", "y"]]
    assert mrr(rankings, ["a", "a", "a"]) == pytest.approx((1 + 0.5 + 0) / 3)


def test_metrics_are_zero_without_queries():
    assert recall_at_k([], [], 1) == 0.0
    assert mrr([], []) == 0.0


def test_metrics_reject_mismatched_inputs():
    with pytest.raises(ValueError):
        recall_at_k([["a"]], [], 1)


def test_dedupe_ranking_keeps_first_occurrence_order():
    assert dedupe_ranking(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_bootstrap_interval_contains_the_mean():
    values = [1.0] * 12 + [0.0] * 3
    low, high = bootstrap_interval(values)
    assert low <= 0.8 <= high


def test_bootstrap_interval_is_wide_for_small_samples():
    low, high = bootstrap_interval([1.0] * 12 + [0.0] * 3)
    assert high - low > 0.2


def test_bootstrap_interval_collapses_when_values_agree():
    assert bootstrap_interval([1.0] * 10) == (1.0, 1.0)


def test_bootstrap_interval_is_deterministic():
    values = [1.0, 0.0, 1.0, 1.0, 0.0]
    assert bootstrap_interval(values) == bootstrap_interval(values)


def test_bootstrap_interval_of_nothing_is_zero():
    assert bootstrap_interval([]) == (0.0, 0.0)


def test_first_rank_any_returns_the_best_relevant_position():
    assert first_rank_any(["a", "b", "c"], {"c", "b"}) == 2


def test_first_rank_any_is_none_without_relevant_docs():
    assert first_rank_any(["a", "b"], {"z"}) is None


def test_sign_test_is_one_without_discordant_pairs():
    assert sign_test_p_value(0, 0) == 1.0


def test_sign_test_is_one_for_a_balanced_split():
    assert sign_test_p_value(5, 5) == 1.0


def test_sign_test_matches_the_exact_binomial_value():
    # 2 * P(X <= 1) for n=10: 2 * (1 + 10) / 1024
    assert sign_test_p_value(1, 9) == pytest.approx(22 / 1024)


def test_sign_test_is_symmetric():
    assert sign_test_p_value(3, 12) == sign_test_p_value(12, 3)


def test_sign_test_one_sided_extreme_is_tiny():
    assert sign_test_p_value(0, 10) == pytest.approx(2 / 1024)


def test_parse_qrels_skips_header_and_zero_scores():
    lines = [
        "query-id\tcorpus-id\tscore\n",
        "1\td1\t1\n",
        "1\td2\t0\n",
        "2\td3\t1\n",
        "\n",
    ]
    assert parse_qrels(lines) == {"1": {"d1"}, "2": {"d3"}}


def test_parse_qrels_groups_several_relevant_docs():
    lines = ["h\n", "1\ta\t1\n", "1\tb\t2\n"]
    assert parse_qrels(lines) == {"1": {"a", "b"}}
