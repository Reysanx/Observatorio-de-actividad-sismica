"""Live 24-hour versus immutable 2025 baseline comparison."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request

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
    """Compare recent M4+ live events with 2025 daily mean over all 365 days."""
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
        first_parameter=len(recent_values) + 3,
    )
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)
    sql = f"""
        SELECT clock_timestamp() AS calculated_at,
               (SELECT count(*)::BIGINT
                FROM current_earthquakes live
                JOIN dim_countries live_country
                  ON live_country.adm0_a3 = live.adm0_a3
                WHERE live.time_utc >= $1 AND live.time_utc < $2
                  AND live.mag >= 4.0 AND ({recent_predicate}))
                    AS recent_event_count,
               (SELECT count(*)::BIGINT
                FROM historical_2025 baseline
                JOIN dim_countries baseline_country
                  ON baseline_country.adm0_a3 = baseline.adm0_a3
                WHERE baseline.time_utc >= TIMESTAMPTZ '2025-01-01 00:00:00+00'
                  AND baseline.time_utc < TIMESTAMPTZ '2026-01-01 00:00:00+00'
                  AND baseline.mag >= 4.0 AND ({historical_predicate}))
                    AS historical_2025_event_count
    """
    params = [start, now, *recent_values, *historical_values]
    try:
        async with pool.acquire() as connection:
            row = await connection.fetchrow(sql, *params)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database query failed") from exc
    recent_count = int(row["recent_event_count"] or 0)
    historical_count = int(row["historical_2025_event_count"] or 0)
    daily_average = historical_count / 365.0
    ratio = recent_count / daily_average if daily_average > 0 else None
    return HistoricalComparisonResponse(
        calculated_at=row["calculated_at"],
        window_start_utc=start,
        window_end_utc=now,
        recent_event_count=recent_count,
        historical_2025_event_count=historical_count,
        historical_days=365,
        historical_daily_average=daily_average,
        ratio_to_historical_daily_average=ratio,
        adm0_a3=adm0_a3,
        continent=continent,
        subregion=subregion,
    )
