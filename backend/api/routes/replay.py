"""Replay lifecycle state endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.db import connection_pool
from api.models import ReplayStateResponse

router = APIRouter()


@router.get("/replay/state", response_model=ReplayStateResponse)
async def replay_state(request: Request) -> ReplayStateResponse:
    """Return the newest persisted replay run without querying live event data."""
    pool = connection_pool(request.app)
    row = await pool.fetchrow(
        """
        SELECT run_id, status, started_at, finished_at,
               events_received, events_processed, events_quarantined
        FROM replay_runs
        ORDER BY started_at DESC, run_id DESC
        LIMIT 1
        """
    )
    if row is None:
        return ReplayStateResponse(
            run_id=None,
            active=False,
            status="idle",
            started_at=None,
            finished_at=None,
            events_received=0,
            events_processed=0,
            events_quarantined=0,
        )

    return ReplayStateResponse(
        run_id=row["run_id"],
        active=row["status"] in {"starting", "running"},
        status=row["status"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        events_received=row["events_received"],
        events_processed=row["events_processed"],
        events_quarantined=row["events_quarantined"],
    )
