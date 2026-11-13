"""Filtered and paginated event listing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from api.db import connection_pool
from api.filters import EventFilters, build_predicates, event_filters
from api.models import EarthquakePage

router = APIRouter()

EVENT_COLUMNS = """
    e.event_id, e.mag, e.mag_type, e.depth_km, e.time_utc, e.updated_utc,
    e.ingested_at, e.adm0_a3, c.display_name AS country_name, c.continent,
    c.subregion, e.place, e.geom_lon, e.geom_lat, e.source
"""
COUNTRY_JOIN = "JOIN dim_countries c ON c.adm0_a3 = e.adm0_a3"


@router.get("/earthquakes", response_model=EarthquakePage)
async def list_earthquakes(
    request: Request,
    filters: EventFilters = Depends(event_filters),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> EarthquakePage:
    """Return a stable page of live events or one explicitly selected replay."""
    pool = connection_pool(request.app)
    predicate, values = build_predicates(filters)
    relation = filters.relation
    try:
        async with pool.acquire() as connection:
            total = await connection.fetchval(
                f"SELECT count(*) FROM {relation} e {COUNTRY_JOIN} WHERE {predicate}",
                *values,
            )
            page_values = [*values, limit, offset]
            rows = await connection.fetch(
                f"""
                SELECT {EVENT_COLUMNS}
                FROM {relation} e
                {COUNTRY_JOIN}
                WHERE {predicate}
                ORDER BY e.time_utc DESC, e.event_id ASC
                LIMIT ${len(values) + 1} OFFSET ${len(values) + 2}
                """,
                *page_values,
            )
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"detail": "database query failed"},
        )
    return EarthquakePage(
        items=[dict(row) for row in rows],
        total=total or 0,
        limit=limit,
        offset=offset,
        scope=filters.scope,
        run_id=filters.run_id,
    )
