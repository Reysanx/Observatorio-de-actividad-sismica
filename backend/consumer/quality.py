"""Schema, completeness, validity, and consistency checks for Kafka records."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


class QualityError(ValueError):
    """An input failure that should be durably quarantined before offset commit."""

    def __init__(
        self,
        reason: str,
        detail: str,
        *,
        raw_payload: Any = None,
    ) -> None:
        super().__init__(detail)
        self.reason = reason[:128]
        self.detail = detail
        self.raw_payload = raw_payload


@dataclass(frozen=True)
class ValidatedEvent:
    event_id: str
    mag: float | None
    mag_type: str | None
    depth_km: float
    time_utc: datetime
    updated_utc: datetime
    ingested_at: datetime
    place: str | None
    geom_lon: float
    geom_lat: float
    source: str
    content_hash: str
    payload: dict[str, Any]
    envelope: dict[str, Any]
    mode: str
    run_id: str | None


@dataclass(frozen=True)
class PollAudit:
    poll_id: str
    source: str
    requested_at: datetime
    completed_at: datetime
    http_status: int | None
    content_hash: str | None
    records_received: int
    records_accepted: int
    records_excluded: int
    records_quarantined: int
    status: str
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class ReplayControl:
    record_type: str
    run_id: str
    timestamp: datetime
    status: str
    error_message: str | None


def decode_message(raw_message: bytes | None) -> Any:
    """Decode Kafka JSON while preserving non-standard numeric tokens for checks."""
    if raw_message is None:
        raise QualityError("CORRUPT_JSON_SYNTAX", "Kafka record has no value")
    try:
        text = raw_message.decode("utf-8")
        return json.loads(text, parse_constant=lambda token: token)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise QualityError("CORRUPT_JSON_SYNTAX", "Kafka value is not valid UTF-8 JSON") from exc


def validate_event(record: Any, *, topic: str) -> ValidatedEvent:
    """Validate a version-1 live or run-scoped replay event envelope."""
    if not isinstance(record, dict):
        raise QualityError(
            "INVALID_EVENT_SCHEMA", "Kafka JSON root must be an object", raw_payload=record
        )
    if topic not in {"earthquakes.live", "earthquakes.replay"}:
        raise QualityError("TOPIC_MODE_MISMATCH", "event arrived on an unexpected topic")
    schema_version = record.get("schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version != 1:
        raise QualityError("INVALID_EVENT_SCHEMA", "unsupported event schema version", raw_payload=record)
    expected_mode = "live" if topic == "earthquakes.live" else "replay"
    expected_source = "usgs_live" if expected_mode == "live" else "usgs_replay"
    if record.get("record_type") != "event" or record.get("mode") != expected_mode:
        raise QualityError(
            "TOPIC_MODE_MISMATCH",
            f"{expected_mode} topic requires a {expected_mode} event envelope",
            raw_payload=record,
        )
    if record.get("source") != expected_source:
        raise QualityError(
            "INVALID_EVENT_SCHEMA",
            f"{expected_mode} event source must be {expected_source}",
            raw_payload=record,
        )
    run_id = record.get("run_id")
    if expected_mode == "live":
        if run_id is not None:
            raise QualityError(
                "TOPIC_MODE_MISMATCH",
                "live event must not carry a replay run_id",
                raw_payload=record,
            )
    elif not isinstance(run_id, str) or not run_id.strip() or len(run_id) > 64:
        raise QualityError(
            "TOPIC_MODE_MISMATCH",
            "replay event requires a non-empty run_id of at most 64 characters",
            raw_payload=record,
        )

    payload = record.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "Feature":
        raise QualityError("INVALID_EVENT_SCHEMA", "payload must be a GeoJSON Feature", raw_payload=record)
    event_id = payload.get("id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise QualityError("MISSING_MANDATORY_IDENTIFIER", "USGS Feature id is missing", raw_payload=record)
    if len(event_id) > 32:
        raise QualityError("INVALID_EVENT_IDENTIFIER", "USGS Feature id exceeds 32 characters", raw_payload=record)
    if record.get("event_id") != event_id:
        raise QualityError("INCONSISTENT_EVENT_IDENTIFIER", "envelope event_id differs from payload id", raw_payload=record)

    properties = payload.get("properties")
    if not isinstance(properties, dict):
        raise QualityError("INVALID_EVENT_SCHEMA", "Feature properties must be an object", raw_payload=record)
    if properties.get("type") != "earthquake":
        raise QualityError("EXCLUDED_EVENT_TYPE", "only USGS earthquake records are accepted", raw_payload=record)

    geometry = payload.get("geometry")
    if not isinstance(geometry, dict) or geometry.get("type") != "Point":
        raise QualityError("INVALID_EVENT_SCHEMA", "Feature geometry must be a GeoJSON Point", raw_payload=record)
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if not isinstance(coordinates, list) or len(coordinates) < 3:
        raise QualityError("MISSING_MANDATORY_COORDINATES", "Feature requires longitude, latitude, and depth", raw_payload=record)
    longitude = _finite_number(
        coordinates[0],
        non_finite_reason="NON_FINITE_COORDINATES",
        invalid_reason="INVALID_COORDINATES",
        field="longitude",
        raw_payload=record,
    )
    latitude = _finite_number(
        coordinates[1],
        non_finite_reason="NON_FINITE_COORDINATES",
        invalid_reason="INVALID_COORDINATES",
        field="latitude",
        raw_payload=record,
    )
    if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
        raise QualityError(
            "INVALID_COORDINATES_OUT_OF_BOUNDS",
            "longitude/latitude exceed WGS84 coordinate bounds",
            raw_payload=record,
        )
    depth = _finite_number(
        coordinates[2],
        non_finite_reason="NON_FINITE_DEPTH",
        invalid_reason="INVALID_DEPTH",
        field="depth_km",
        raw_payload=record,
    )

    magnitude = properties.get("mag")
    if magnitude is not None:
        magnitude = _finite_number(
            magnitude,
            non_finite_reason="NON_FINITE_MAGNITUDE",
            invalid_reason="INVALID_MAGNITUDE",
            field="mag",
            raw_payload=record,
        )
    mag_type = properties.get("magType")
    place = properties.get("place")
    if mag_type is not None and not isinstance(mag_type, str):
        raise QualityError("INVALID_MAGNITUDE_TYPE", "magType must be a string or null", raw_payload=record)
    if isinstance(mag_type, str) and len(mag_type) > 16:
        raise QualityError("INVALID_MAGNITUDE_TYPE", "magType exceeds the 16-character database limit", raw_payload=record)
    if place is not None and not isinstance(place, str):
        raise QualityError("INVALID_PLACE", "place must be a string or null", raw_payload=record)

    time_utc = _epoch_milliseconds(properties.get("time"), "time", record)
    updated_utc = _epoch_milliseconds(properties.get("updated"), "updated", record)
    updated_ms = record.get("updated_ms")
    if isinstance(updated_ms, bool) or not isinstance(updated_ms, int) or updated_ms != properties.get("updated"):
        raise QualityError("INCONSISTENT_UPDATED_TIMESTAMP", "envelope updated_ms must match payload updated", raw_payload=record)
    if time_utc > updated_utc:
        raise QualityError("INVALID_EVENT_TIME_ORDER", "event time is after its update time", raw_payload=record)
    ingested_at = _utc_timestamp(record.get("ingested_at"), "ingested_at", record)

    content_hash = record.get("content_hash")
    if not isinstance(content_hash, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", content_hash) is None:
        raise QualityError("INVALID_EVENT_SCHEMA", "content_hash must be a sha256 digest", raw_payload=record)
    return ValidatedEvent(
        event_id=event_id,
        mag=magnitude,
        mag_type=mag_type,
        depth_km=depth,
        time_utc=time_utc,
        updated_utc=updated_utc,
        ingested_at=ingested_at,
        place=place,
        geom_lon=longitude,
        geom_lat=latitude,
        source=expected_source,
        content_hash=content_hash,
        payload=payload,
        envelope=record,
        mode=expected_mode,
        run_id=run_id if expected_mode == "replay" else None,
    )


def validate_replay_control(record: Any, *, topic: str) -> ReplayControl:
    """Validate a start/finish control record on the isolated replay topic."""
    if (
        not isinstance(record, dict)
        or topic != "earthquakes.replay"
        or record.get("record_type") not in {"replay_started", "replay_finished"}
    ):
        raise QualityError(
            "TOPIC_MODE_MISMATCH",
            "replay control records are only valid on earthquakes.replay",
            raw_payload=record,
        )
    schema_version = record.get("schema_version")
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != 1
        or record.get("source") != "usgs_replay"
    ):
        raise QualityError(
            "INVALID_REPLAY_CONTROL",
            "unsupported replay control schema or source",
            raw_payload=record,
        )
    run_id = record.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip() or len(run_id) > 64:
        raise QualityError(
            "INVALID_REPLAY_CONTROL",
            "run_id must be a non-empty string of at most 64 characters",
            raw_payload=record,
        )

    record_type = record["record_type"]
    if record_type == "replay_started":
        timestamp = _utc_timestamp(record.get("started_at"), "started_at", record)
        return ReplayControl(record_type, run_id, timestamp, "running", None)

    timestamp = _utc_timestamp(record.get("finished_at"), "finished_at", record)
    status = record.get("status", "completed")
    error_message = record.get("error_message")
    if status not in {"completed", "failed"}:
        raise QualityError(
            "INVALID_REPLAY_CONTROL",
            "replay finish status must be completed or failed",
            raw_payload=record,
        )
    if error_message is not None and not isinstance(error_message, str):
        raise QualityError(
            "INVALID_REPLAY_CONTROL",
            "error_message must be a string or null",
            raw_payload=record,
        )
    if error_message is not None and len(error_message) > 2000:
        error_message = error_message[:2000]
    return ReplayControl(record_type, run_id, timestamp, status, error_message)


def validate_poll_audit(record: Any, *, topic: str) -> PollAudit:
    """Validate producer poll-control metadata for the ingestion audit table."""
    if not isinstance(record, dict):
        raise QualityError("INVALID_AUDIT_RECORD", "poll audit must be an object", raw_payload=record)
    if topic != "earthquakes.live" or record.get("record_type") != "poll_audit":
        raise QualityError("TOPIC_MODE_MISMATCH", "poll audit arrived on an unexpected topic", raw_payload=record)
    schema_version = record.get("schema_version")
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != 1
        or record.get("source") != "usgs_live"
    ):
        raise QualityError("INVALID_AUDIT_RECORD", "unsupported poll audit schema or source", raw_payload=record)
    poll_id = record.get("poll_id")
    if not isinstance(poll_id, str) or not poll_id.strip() or len(poll_id) > 64:
        raise QualityError("INVALID_AUDIT_RECORD", "poll_id must be a non-empty string up to 64 characters", raw_payload=record)
    requested_at = _utc_timestamp(record.get("requested_at"), "requested_at", record)
    completed_at = _utc_timestamp(record.get("completed_at"), "completed_at", record)
    if completed_at < requested_at:
        raise QualityError("INVALID_AUDIT_RECORD", "completed_at precedes requested_at", raw_payload=record)

    http_status = record.get("http_status")
    if http_status is not None and (
        isinstance(http_status, bool) or not isinstance(http_status, int) or not 100 <= http_status <= 599
    ):
        raise QualityError("INVALID_AUDIT_RECORD", "http_status must be null or an HTTP status code", raw_payload=record)
    counts = [
        _nonnegative_integer(record.get(key), key, record)
        for key in ("records_received", "records_accepted", "records_excluded")
    ]
    if counts[1] + counts[2] != counts[0]:
        raise QualityError(
            "INVALID_AUDIT_RECORD",
            "accepted plus excluded records must equal records_received",
            raw_payload=record,
        )
    error_code = record.get("error_code")
    error_message = record.get("error_message")
    if error_code is not None and not isinstance(error_code, str):
        raise QualityError("INVALID_AUDIT_RECORD", "error_code must be a string or null", raw_payload=record)
    if error_message is not None and not isinstance(error_message, str):
        raise QualityError("INVALID_AUDIT_RECORD", "error_message must be a string or null", raw_payload=record)
    content_hash = record.get("content_hash")
    if content_hash is not None and not isinstance(content_hash, str):
        raise QualityError("INVALID_AUDIT_RECORD", "content_hash must be a string or null", raw_payload=record)
    if content_hash is not None and (
        len(content_hash) > 80
        or re.fullmatch(r"sha256:[0-9a-f]{64}", content_hash) is None
    ):
        raise QualityError("INVALID_AUDIT_RECORD", "content_hash is not a supported sha256 digest", raw_payload=record)
    if error_code is not None and len(error_code) > 64:
        raise QualityError("INVALID_AUDIT_RECORD", "error_code exceeds the database column limit", raw_payload=record)
    status = (
        "failed"
        if error_code is not None or http_status is None or not 200 <= http_status < 300
        else "succeeded"
    )
    return PollAudit(
        poll_id=poll_id,
        source="usgs_live",
        requested_at=requested_at,
        completed_at=completed_at,
        http_status=http_status,
        content_hash=content_hash,
        records_received=counts[0],
        records_accepted=counts[1],
        records_excluded=counts[2],
        records_quarantined=0,
        status=status,
        error_code=error_code,
        error_message=error_message,
    )


def _finite_number(
    value: Any,
    *,
    non_finite_reason: str,
    invalid_reason: str,
    field: str,
    raw_payload: Any,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        if isinstance(value, str) and value.strip().lower() in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
            raise QualityError(non_finite_reason, f"{field} is not finite", raw_payload=raw_payload)
        raise QualityError(invalid_reason, f"{field} must be a number", raw_payload=raw_payload)
    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise QualityError(non_finite_reason, f"{field} is not finite", raw_payload=raw_payload)
    if not math.isfinite(number):
        raise QualityError(non_finite_reason, f"{field} is not finite", raw_payload=raw_payload)
    return number


def _epoch_milliseconds(value: Any, field: str, raw_payload: Any) -> datetime:
    if isinstance(value, bool) or not isinstance(value, int):
        raise QualityError("INVALID_EVENT_TIMESTAMP", f"{field} must be an integer Unix millisecond value", raw_payload=raw_payload)
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise QualityError("INVALID_EVENT_TIMESTAMP", f"{field} is outside supported UTC range", raw_payload=raw_payload) from exc


def _utc_timestamp(value: Any, field: str, raw_payload: Any) -> datetime:
    if not isinstance(value, str):
        raise QualityError("INVALID_EVENT_TIMESTAMP", f"{field} must be an RFC 3339 timestamp", raw_payload=raw_payload)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualityError("INVALID_EVENT_TIMESTAMP", f"{field} is not a valid timestamp", raw_payload=raw_payload) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise QualityError("INVALID_EVENT_TIMESTAMP", f"{field} must include a UTC offset", raw_payload=raw_payload)
    if parsed.utcoffset() != timedelta(0):
        raise QualityError("INVALID_EVENT_TIMESTAMP", f"{field} must be expressed in UTC", raw_payload=raw_payload)
    return parsed.astimezone(timezone.utc)


def _nonnegative_integer(value: Any, field: str, raw_payload: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2_147_483_647:
        raise QualityError(
            "INVALID_AUDIT_RECORD",
            f"{field} must fit a non-negative PostgreSQL INTEGER",
            raw_payload=raw_payload,
        )
    return value
