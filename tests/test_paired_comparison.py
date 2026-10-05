from docsearch.evaluation import paired_comparison


def test_counts_discordant_pairs_at_the_cutoff():
    result = paired_comparison([1, 5, None, 2], [4, 1, None, 2], k=3)
    assert (result["only_a"], result["only_b"]) == (1, 1)
    assert (result["both"], result["neither"]) == (1, 1)
    assert result["k"] == 3


def test_identical_systems_have_p_value_one():
    assert paired_comparison([1, 2], [1, 2], k=3)["p_value"] == 1.0


def test_one_sided_wins_are_significant():
    result = paired_comparison([1] * 8, [None] * 8, k=3)
    assert result["only_a"] == 8
    assert result["p_value"] < 0.05
