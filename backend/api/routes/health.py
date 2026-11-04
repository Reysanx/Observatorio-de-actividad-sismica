"""Database and ingestion freshness endpoint."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from api.db import connection_pool
from api.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Report API/database readiness and persisted live-ingestion freshness."""
    pool = connection_pool(request.app)
    try:
        row = await pool.fetchrow(
            """
            SELECT clock_timestamp() AS api_time,
                   (SELECT max(completed_at)
                    FROM ingestion_audit
                    WHERE source = 'usgs_live' AND status = 'succeeded')
                       AS last_successful_poll_at,
                   (SELECT max(ingested_at) FROM current_earthquakes)
                       AS last_event_ingested_at,
                   (SELECT max(updated_utc) FROM current_earthquakes)
                       AS latest_event_updated_at
            """
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database is unavailable") from exc
    now = row["api_time"] or datetime.now(timezone.utc)
    latest_updated = row["latest_event_updated_at"]
    delay = None
    if latest_updated is not None:
        delay = max(0.0, (now - latest_updated).total_seconds())
    return HealthResponse(
        api_time=now,
        last_successful_poll_at=row["last_successful_poll_at"],
        last_event_ingested_at=row["last_event_ingested_at"],
        latest_event_updated_at=row["latest_event_updated_at"],
        ingestion_delay_seconds=delay,
    )
