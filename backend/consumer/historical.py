"""Validation and normalization for the immutable USGS 2025 baseline."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


class HistoricalImportError(ValueError):
    """Raised when a cached feature cannot satisfy the baseline contract."""


@dataclass(frozen=True)
class HistoricalEvent:
    event_id: str
    mag: float
    mag_type: str | None
    depth_km: float
    time_utc: datetime
    updated_utc: datetime
    ingested_at: datetime
    place: str | None
    geom_lon: float
    geom_lat: float
    content_hash: str
    payload: dict[str, Any]
    source: str = "usgs_2025"


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HistoricalImportError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise HistoricalImportError(f"{field} must be a finite number")
    return number


def _timestamp(value: Any, field: str) -> datetime:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HistoricalImportError(f"{field} must be an integer Unix timestamp in milliseconds")
    try:
        return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise HistoricalImportError(f"{field} is outside the supported UTC range") from exc


def normalize_historical_feature(
    feature: Any,
    *,
    ingested_at: datetime | None = None,
) -> HistoricalEvent:
    """Validate a USGS Feature without reclassifying it as a live envelope."""
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise HistoricalImportError("historical record must be a GeoJSON Feature")
    event_id = feature.get("id")
    if not isinstance(event_id, str) or not event_id.strip() or len(event_id) > 32:
        raise HistoricalImportError("historical Feature has an invalid USGS event ID")

    properties = feature.get("properties")
    if not isinstance(properties, dict) or properties.get("type") != "earthquake":
        raise HistoricalImportError("historical Feature must have earthquake properties")
    magnitude = _finite_number(properties.get("mag"), "mag")
    if magnitude < 4.0:
        raise HistoricalImportError("historical magnitude is below the 4.0 baseline threshold")

    geometry = feature.get("geometry")
    if not isinstance(geometry, dict) or geometry.get("type") != "Point":
        raise HistoricalImportError("historical Feature geometry must be a Point")
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 3:
        raise HistoricalImportError("historical Feature requires longitude, latitude, and depth")
    longitude = _finite_number(coordinates[0], "longitude")
    latitude = _finite_number(coordinates[1], "latitude")
    depth_km = _finite_number(coordinates[2], "depth_km")
    if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
        raise HistoricalImportError("historical coordinates are outside WGS84 bounds")

    time_utc = _timestamp(properties.get("time"), "time")
    updated_utc = _timestamp(properties.get("updated"), "updated")
    if not (
        datetime(2025, 1, 1, tzinfo=timezone.utc)
        <= time_utc
        < datetime(2026, 1, 1, tzinfo=timezone.utc)
    ):
        raise HistoricalImportError("historical event time is outside calendar year 2025")
    if updated_utc < time_utc:
        raise HistoricalImportError("historical update time precedes event time")

    mag_type = properties.get("magType")
    place = properties.get("place")
    if mag_type is not None and (
        not isinstance(mag_type, str) or len(mag_type) > 16
    ):
        raise HistoricalImportError("magType must be a string of at most 16 characters or null")
    if place is not None and not isinstance(place, str):
        raise HistoricalImportError("place must be a string or null")

    ingested = ingested_at or datetime.now(timezone.utc)
    if ingested.tzinfo is None or ingested.utcoffset() is None:
        raise HistoricalImportError("ingested_at must be timezone-aware")
    ingested = ingested.astimezone(timezone.utc)
    try:
        canonical = json.dumps(
            feature,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise HistoricalImportError("historical Feature is not valid finite JSON") from exc

    return HistoricalEvent(
        event_id=event_id,
        mag=magnitude,
        mag_type=mag_type,
        depth_km=depth_km,
        time_utc=time_utc,
        updated_utc=updated_utc,
        ingested_at=ingested,
        place=place,
        geom_lon=longitude,
        geom_lat=latitude,
        content_hash=f"sha256:{hashlib.sha256(canonical).hexdigest()}",
        payload=feature,
    )
