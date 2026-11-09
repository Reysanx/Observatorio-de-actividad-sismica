"""Live 24-hour versus immutable 2025 baseline comparison."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request

from api.analysis import (
    COMPARISON_MAGNITUDE_THRESHOLD,
    HISTORICAL_DAYS,
    HISTORICAL_DATASET_KEY,
    summarize_comparison,
)
from api.db import connection_pool
from api.filters import build_geographic_predicates
from api.models import HistoricalComparisonResponse

router = APIRouter()


@router.get("/stats/historical-comparison", response_model=HistoricalComparisonResponse)
async def historical_comparison(
    request: Request,
    adm0_a3: str | None = Query(default=None, min_length=1, max_length=8),
    continent: str | None = Query(default=None, min_length=1, max_length=80),
    subregion: str | None = Query(default=None, min_length=1, max_length=80),
) -> HistoricalComparisonResponse:
    """Compare recent M4.5+ live events with the complete 2025 daily baseline."""
    pool = connection_pool(request.app)
    recent_predicate, recent_values = build_geographic_predicates(
        adm0_a3=adm0_a3,
        continent=continent,
        subregion=subregion,
        event_alias="live",
        country_alias="live_country",
        first_parameter=3,
    )
    historical_predicate, historical_values = build_geographic_predicates(
        adm0_a3=adm0_a3,
        continent=continent,
        subregion=subregion,
        event_alias="baseline",
        country_alias="baseline_country",
        first_parameter=1,
    )
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)
    comparison_sql = f"""
        SELECT (SELECT count(*)::BIGINT
                FROM current_earthquakes live
                JOIN dim_countries live_country
                  ON live_country.adm0_a3 = live.adm0_a3
                WHERE live.time_utc >= $1 AND live.time_utc < $2
                  AND live.mag >= {COMPARISON_MAGNITUDE_THRESHOLD}
                  AND ({recent_predicate})) AS recent_event_count,
               (SELECT count(*)::BIGINT
                FROM historical_2025) AS stored_event_count,
               (SELECT event_count
                FROM dataset_imports
                WHERE dataset_key = '{HISTORICAL_DATASET_KEY}')
                    AS imported_event_count
    """
    daily_sql = f"""
        WITH calendar AS (
            SELECT generate_series(
                DATE '2025-01-01',
                DATE '2025-12-31',
                INTERVAL '1 day'
            )::DATE AS day_utc
        )
        SELECT calendar.day_utc,
               count(baseline.event_id)::BIGINT AS event_count
        FROM calendar
        LEFT JOIN (
            historical_2025 baseline
            JOIN dim_countries baseline_country
              ON baseline_country.adm0_a3 = baseline.adm0_a3
        )
          ON baseline.time_utc >= calendar.day_utc::TIMESTAMP AT TIME ZONE 'UTC'
         AND baseline.time_utc < (calendar.day_utc + 1)::TIMESTAMP AT TIME ZONE 'UTC'
         AND baseline.mag >= {COMPARISON_MAGNITUDE_THRESHOLD}
          AND ({historical_predicate})
        GROUP BY calendar.day_utc
        ORDER BY calendar.day_utc
    """
    try:
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                comparison_sql, start, now, *recent_values
            )
            daily_rows = await connection.fetch(daily_sql, *historical_values)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database query failed") from exc

    if (
        row["imported_event_count"] is None
        or int(row["imported_event_count"]) <= 0
        or int(row["imported_event_count"]) != int(row["stored_event_count"])
        or len(daily_rows) != HISTORICAL_DAYS
    ):
        raise HTTPException(
            status_code=503,
            detail="2025 historical baseline is missing or inconsistent",
        )

    recent_count = int(row["recent_event_count"] or 0)
    daily_counts = [int(daily["event_count"]) for daily in daily_rows]
    metrics = summarize_comparison(daily_counts, recent_count)
    return HistoricalComparisonResponse(
        calculated_at=now,
        window_start_utc=start,
        window_end_utc=now,
        magnitude_threshold=COMPARISON_MAGNITUDE_THRESHOLD,
        recent_event_count=recent_count,
        **metrics,
        adm0_a3=adm0_a3,
        continent=continent,
        subregion=subregion,
    )
