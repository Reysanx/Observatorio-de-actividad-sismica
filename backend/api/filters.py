"""Validation and safe SQL predicate construction for event queries."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import HTTPException, Query


@dataclass(frozen=True)
class EventFilters:
    start_utc: datetime
    end_utc: datetime
    mag_min: float | None
    mag_max: float | None
    depth_min_km: float | None
    depth_max_km: float | None
    adm0_a3: str | None
    continent: str | None
    subregion: str | None
    scope: Literal["live", "replay"]
    run_id: str | None

    @property
    def relation(self) -> str:
        return "current_earthquakes" if self.scope == "live" else "replay_earthquakes"


def event_filters(
    start_utc: datetime | None = Query(default=None),
    end_utc: datetime | None = Query(default=None),
    mag_min: float | None = Query(default=None),
    mag_max: float | None = Query(default=None),
    depth_min_km: float | None = Query(default=None),
    depth_max_km: float | None = Query(default=None),
    adm0_a3: str | None = Query(default=None, min_length=1, max_length=8),
    continent: str | None = Query(default=None, min_length=1, max_length=80),
    subregion: str | None = Query(default=None, min_length=1, max_length=80),
    scope: Literal["live", "replay"] = Query(default="live"),
    run_id: str | None = Query(default=None, min_length=1, max_length=64),
) -> EventFilters:
    """Parse common filters, defaulting to the previous 24 UTC hours."""
    now = datetime.now(timezone.utc)
    start = _normalize_timestamp(start_utc, "start_utc") if start_utc else now - timedelta(hours=24)
    end = _normalize_timestamp(end_utc, "end_utc") if end_utc else now
    if start >= end:
        raise HTTPException(status_code=422, detail="start_utc must be earlier than end_utc")
    if mag_min is not None and mag_max is not None and mag_min > mag_max:
        raise HTTPException(status_code=422, detail="mag_min must not exceed mag_max")
    if depth_min_km is not None and depth_max_km is not None and depth_min_km > depth_max_km:
        raise HTTPException(status_code=422, detail="depth_min_km must not exceed depth_max_km")
    for name, value in (
        ("mag_min", mag_min),
        ("mag_max", mag_max),
        ("depth_min_km", depth_min_km),
        ("depth_max_km", depth_max_km),
    ):
        if value is not None and not math.isfinite(value):
            raise HTTPException(status_code=422, detail=f"{name} must be finite")
    if scope == "replay" and run_id is None:
        raise HTTPException(status_code=422, detail="run_id is required when scope=replay")
    if scope == "live" and run_id is not None:
        raise HTTPException(status_code=422, detail="run_id is only valid when scope=replay")
    return EventFilters(
        start_utc=start,
        end_utc=end,
        mag_min=mag_min,
        mag_max=mag_max,
        depth_min_km=depth_min_km,
        depth_max_km=depth_max_km,
        adm0_a3=adm0_a3,
        continent=continent,
        subregion=subregion,
        scope=scope,
        run_id=run_id,
    )


def normalize_query_timestamp(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    return _normalize_timestamp(value, name)


def build_predicates(
    filters: EventFilters,
    *,
    event_alias: str = "e",
    country_alias: str = "c",
    include_time: bool = True,
) -> tuple[str, list[object]]:
    """Build bound SQL conditions; only fixed aliases/relations enter SQL text."""
    predicates: list[str] = []
    values: list[object] = []

    def add(expression: str, value: object) -> None:
        values.append(value)
        predicates.append(expression.replace("?", f"${len(values)}"))

    if include_time:
        add(f"{event_alias}.time_utc >= ?", filters.start_utc)
        add(f"{event_alias}.time_utc < ?", filters.end_utc)
    if filters.scope == "replay":
        add(f"{event_alias}.run_id = ?", filters.run_id)
    if filters.mag_min is not None:
        add(f"{event_alias}.mag >= ?", filters.mag_min)
    if filters.mag_max is not None:
        add(f"{event_alias}.mag <= ?", filters.mag_max)
    if filters.depth_min_km is not None:
        add(f"{event_alias}.depth_km >= ?", filters.depth_min_km)
    if filters.depth_max_km is not None:
        add(f"{event_alias}.depth_km <= ?", filters.depth_max_km)
    if filters.adm0_a3 is not None:
        add(f"{event_alias}.adm0_a3 = ?", filters.adm0_a3)
    if filters.continent is not None:
        add(f"{country_alias}.continent = ?", filters.continent)
    if filters.subregion is not None:
        add(f"{country_alias}.subregion = ?", filters.subregion)
    return " AND ".join(predicates) if predicates else "TRUE", values


def build_geographic_predicates(
    *,
    adm0_a3: str | None,
    continent: str | None,
    subregion: str | None,
    event_alias: str,
    country_alias: str,
    first_parameter: int = 1,
) -> tuple[str, list[object]]:
    """Build geography-only predicates for the fixed 24h/2025 comparison."""
    predicates: list[str] = []
    values: list[object] = []
    for expression, value in (
        (f"{event_alias}.adm0_a3 = ?", adm0_a3),
        (f"{country_alias}.continent = ?", continent),
        (f"{country_alias}.subregion = ?", subregion),
    ):
        if value is not None:
            values.append(value)
            predicates.append(expression.replace("?", f"${first_parameter + len(values) - 1}"))
    return " AND ".join(predicates) if predicates else "TRUE", values


def _normalize_timestamp(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(status_code=422, detail=f"{name} must include a UTC offset")
    return value.astimezone(timezone.utc)
