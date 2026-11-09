"""Shared definitions and deterministic statistics for seismic analysis."""

from __future__ import annotations

import math
import statistics
from typing import Any

HISTORICAL_DATASET_KEY = "usgs_2025_magnitude_4_v1"
COMPARISON_MAGNITUDE_THRESHOLD = 4.5
HISTORICAL_DAYS = 365


def summarize_comparison(
    daily_counts: list[int],
    recent_event_count: int,
) -> dict[str, Any]:
    """Derive comparison metrics from the complete 2025 daily population."""
    if len(daily_counts) != HISTORICAL_DAYS:
        raise ValueError(f"expected {HISTORICAL_DAYS} daily counts")
    if any(count < 0 for count in daily_counts) or recent_event_count < 0:
        raise ValueError("event counts must be non-negative")

    daily_average = math.fsum(daily_counts) / HISTORICAL_DAYS
    daily_stddev = statistics.pstdev(daily_counts)
    standardized_deviation = (
        (recent_event_count - daily_average) / daily_stddev
        if daily_stddev > 0
        else None
    )
    if standardized_deviation is None:
        deviation_band = "unavailable"
    elif abs(standardized_deviation) <= 1:
        deviation_band = "within_1_sd"
    elif abs(standardized_deviation) <= 2:
        deviation_band = "between_1_and_2_sd"
    else:
        deviation_band = "beyond_2_sd"

    return {
        "historical_days": HISTORICAL_DAYS,
        "historical_2025_event_count": sum(daily_counts),
        "historical_daily_average": daily_average,
        "historical_daily_population_stddev": daily_stddev,
        "recent_standard_deviations_from_mean": standardized_deviation,
        "deviation_band": deviation_band,
        "ratio_to_historical_daily_average": (
            recent_event_count / daily_average if daily_average > 0 else None
        ),
    }


def type_7_percentile(values: list[float], probability: float) -> float | None:
    """Return a Hyndman–Fan Type 7 quantile, or None for an empty population."""
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between zero and one")
    if not values:
        return None
    if any(not math.isfinite(value) for value in values):
        raise ValueError("quantile values must be finite")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * probability
    lower = math.floor(rank)
    upper = math.ceil(rank)
    fraction = rank - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])
