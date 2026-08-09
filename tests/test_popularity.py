from steam_graveyard.services.popularity import calculate_popularity


def test_popularity_is_deterministic_and_bounded() -> None:
    score = calculate_popularity(
        historical_peak_players=1_000_000,
        review_count=1_000_000,
        review_score=100,
    )
    assert score == 100.0


def test_popularity_reweights_missing_components() -> None:
    assert (
        calculate_popularity(
            historical_peak_players=None,
            review_count=None,
            review_score=80,
        )
        == 80.0
    )


def test_popularity_does_not_invent_missing_data() -> None:
    assert (
        calculate_popularity(
            historical_peak_players=None,
            review_count=None,
            review_score=None,
        )
        is None
    )


def test_popularity_clamps_input_components() -> None:
    assert (
        calculate_popularity(
            historical_peak_players=2_000_000,
            review_count=2_000_000,
            review_score=120,
        )
        == 100.0
    )
