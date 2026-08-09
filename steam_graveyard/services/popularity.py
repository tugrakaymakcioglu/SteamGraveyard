"""Deterministic popularity scoring."""

from __future__ import annotations

from math import log1p


def _log_component(value: int, ceiling: int = 1_000_000) -> float:
    return min(1.0, log1p(max(0, value)) / log1p(ceiling))


def calculate_popularity(
    *,
    historical_peak_players: int | None,
    review_count: int | None,
    review_score: float | None,
) -> float | None:
    """Return a 0-100 score, reweighting only available components."""
    components: list[tuple[float, float]] = []
    if historical_peak_players is not None:
        components.append((0.50, _log_component(historical_peak_players)))
    if review_count is not None:
        components.append((0.30, _log_component(review_count)))
    if review_score is not None:
        components.append((0.20, min(1.0, max(0.0, review_score / 100))))
    if not components:
        return None
    total_weight = sum(weight for weight, _ in components)
    score = sum(weight * value for weight, value in components) / total_weight
    return round(score * 100, 1)
