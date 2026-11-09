"""Geographic, hourly, and histogram analytics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.db import connection_pool
from api.filters import EventFilters, build_predicates, event_filters
from api.models import (
    DistributionResponse,
    GeoStatsResponse,
    HourlyStatsResponse,
)
from api.routes.earthquakes import COUNTRY_JOIN

router = APIRouter()


@router.get("/stats/geo", response_model=GeoStatsResponse)
async def geo_stats(
    request: Request,
    filters: EventFilters = Depends(event_filters),
) -> GeoStatsResponse:
    pool = connection_pool(request.app)
    predicate, values = build_predicates(filters)
    relation = filters.relation
    try:
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                f"""
                WITH filtered AS (
                    SELECT e.adm0_a3, e.mag, c.display_name AS country_name,
                           c.continent, c.subregion
                    FROM {relation} e
                    {COUNTRY_JOIN}
                    WHERE {predicate}
                ), aggregated AS (
                    SELECT adm0_a3, country_name, continent, subregion,
                           count(*)::BIGINT AS event_count,
                           count(mag)::BIGINT AS magnitude_count,
                           avg(mag)::DOUBLE PRECISION AS average_magnitude,
                           max(mag)::DOUBLE PRECISION AS maximum_magnitude
                    FROM filtered
                    GROUP BY adm0_a3, country_name, continent, subregion
                )
                SELECT * FROM aggregated
                UNION ALL
                SELECT 'N/A', 'Sin país asignado', NULL, NULL,
                       0::BIGINT, 0::BIGINT, NULL::DOUBLE PRECISION,
                       NULL::DOUBLE PRECISION
                WHERE NOT EXISTS (SELECT 1 FROM aggregated WHERE adm0_a3 = 'N/A')
                ORDER BY event_count DESC, adm0_a3 ASC
                """,
                *values,
            )
    except Exception:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="database query failed")
    return GeoStatsResponse(
        items=[dict(row) for row in rows],
        scope=filters.scope,
        run_id=filters.run_id,
    )


@router.get("/stats/hourly", response_model=HourlyStatsResponse)
async def hourly_stats(
    request: Request,
    filters: EventFilters = Depends(event_filters),
) -> HourlyStatsResponse:
    pool = connection_pool(request.app)
    predicate, values = build_predicates(filters)
    relation = filters.relation
    try:
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                f"""
                SELECT date_trunc('hour', e.time_utc AT TIME ZONE 'UTC')
                           AT TIME ZONE 'UTC' AS hour_utc,
                       count(*)::BIGINT AS event_count,
                       count(e.mag)::BIGINT AS magnitude_count,
                       avg(e.mag)::DOUBLE PRECISION AS average_magnitude
                FROM {relation} e
                {COUNTRY_JOIN}
                WHERE {predicate}
                GROUP BY 1
                ORDER BY 1
                """,
                *values,
            )
    except Exception:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="database query failed")
    return HourlyStatsResponse(
        items=[dict(row) for row in rows],
        scope=filters.scope,
        run_id=filters.run_id,
    )


@router.get("/stats/distributions", response_model=DistributionResponse)
async def distributions(
    request: Request,
    filters: EventFilters = Depends(event_filters),
) -> DistributionResponse:
    pool = connection_pool(request.app)
    predicate, values = build_predicates(filters)
    relation = filters.relation
    try:
        async with pool.acquire() as connection:
            counts = await connection.fetchrow(
                f"""
                SELECT count(*) FILTER (WHERE e.mag IS NULL)::BIGINT
                           AS magnitude_null_count,
                       count(*) FILTER (WHERE e.depth_km IS NULL)::BIGINT
                           AS depth_null_count,
                       count(e.depth_km) FILTER (
                           WHERE e.depth_km IS NOT NULL
                             AND e.depth_km::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
                       )::BIGINT AS depth_population_count,
                       percentile_cont(0.90) WITHIN GROUP (ORDER BY e.depth_km)
                           FILTER (
                               WHERE e.depth_km IS NOT NULL
                                 AND e.depth_km::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
                           ) AS depth_p90_km
                FROM {relation} e
                {COUNTRY_JOIN}
                WHERE {predicate}
                """,
                *values,
            )
            magnitude_rows = await connection.fetch(
                f"""
                SELECT floor(e.mag / 0.5) * 0.5 AS bin_start,
                       floor(e.mag / 0.5) * 0.5 + 0.5 AS bin_end,
                       count(*)::BIGINT AS count
                FROM {relation} e
                {COUNTRY_JOIN}
                WHERE {predicate} AND e.mag IS NOT NULL
                GROUP BY 1, 2 ORDER BY 1
                """,
                *values,
            )
            depth_rows = await connection.fetch(
                f"""
                SELECT floor(e.depth_km / 20.0) * 20.0 AS bin_start,
                       floor(e.depth_km / 20.0) * 20.0 + 20.0 AS bin_end,
                       count(*)::BIGINT AS count
                FROM {relation} e
                {COUNTRY_JOIN}
                WHERE {predicate} AND e.depth_km IS NOT NULL
                GROUP BY 1, 2 ORDER BY 1
                """,
                *values,
            )
    except Exception:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="database query failed")
    return DistributionResponse(
        magnitude_bins=[dict(row) for row in magnitude_rows],
        depth_bins=[dict(row) for row in depth_rows],
        magnitude_null_count=counts["magnitude_null_count"] or 0,
        depth_null_count=counts["depth_null_count"] or 0,
        depth_p90_km=counts["depth_p90_km"],
        depth_population_count=counts["depth_population_count"] or 0,
        depth_period_start_utc=filters.start_utc,
        depth_period_end_utc=filters.end_utc,
        scope=filters.scope,
        run_id=filters.run_id,
    )
