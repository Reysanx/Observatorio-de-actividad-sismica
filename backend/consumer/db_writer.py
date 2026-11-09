"""Transactional PostgreSQL persistence for validated live consumer records."""

from __future__ import annotations

import json
from typing import Any

import asyncpg

from consumer.historical import HistoricalEvent
from consumer.quality import PollAudit, ReplayControl, ValidatedEvent
from consumer.spatial import Country

_UPSERT_CURRENT = """
INSERT INTO current_earthquakes (
    event_id, mag, mag_type, depth_km, time_utc, updated_utc, ingested_at,
    adm0_a3, place, geom_lon, geom_lat, source, content_hash, raw_payload
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14::jsonb
)
ON CONFLICT (event_id) DO UPDATE
SET mag = EXCLUDED.mag,
    mag_type = EXCLUDED.mag_type,
    depth_km = EXCLUDED.depth_km,
    time_utc = EXCLUDED.time_utc,
    updated_utc = EXCLUDED.updated_utc,
    ingested_at = EXCLUDED.ingested_at,
    adm0_a3 = EXCLUDED.adm0_a3,
    place = EXCLUDED.place,
    geom_lon = EXCLUDED.geom_lon,
    geom_lat = EXCLUDED.geom_lat,
    content_hash = EXCLUDED.content_hash,
    raw_payload = EXCLUDED.raw_payload
WHERE EXCLUDED.updated_utc > current_earthquakes.updated_utc
RETURNING event_id, updated_utc
"""

_INSERT_VERSION = """
INSERT INTO earthquake_versions (
    event_id, updated_utc, ingested_at, mag, mag_type, depth_km, time_utc,
    adm0_a3, place, geom_lon, geom_lat, source, content_hash, raw_payload
) VALUES (
    $1, $6, $7, $2, $3, $4, $5, $8, $9, $10, $11, $12, $13, $14::jsonb
)
ON CONFLICT (event_id, updated_utc) DO NOTHING
"""

_UPSERT_REPLAY_EVENT = """
INSERT INTO replay_earthquakes (
    run_id, event_id, mag, mag_type, depth_km, time_utc, updated_utc,
    ingested_at, adm0_a3, place, geom_lon, geom_lat, source, content_hash,
    raw_payload
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15::jsonb
)
ON CONFLICT (run_id, event_id) DO UPDATE
SET mag = EXCLUDED.mag,
    mag_type = EXCLUDED.mag_type,
    depth_km = EXCLUDED.depth_km,
    time_utc = EXCLUDED.time_utc,
    updated_utc = EXCLUDED.updated_utc,
    ingested_at = EXCLUDED.ingested_at,
    adm0_a3 = EXCLUDED.adm0_a3,
    place = EXCLUDED.place,
    geom_lon = EXCLUDED.geom_lon,
    geom_lat = EXCLUDED.geom_lat,
    source = EXCLUDED.source,
    content_hash = EXCLUDED.content_hash,
    raw_payload = EXCLUDED.raw_payload
WHERE EXCLUDED.updated_utc > replay_earthquakes.updated_utc
RETURNING event_id, updated_utc
"""

_INSERT_REPLAY_VERSION = """
INSERT INTO replay_versions (
    run_id, event_id, updated_utc, ingested_at, mag, mag_type, depth_km,
    time_utc, adm0_a3, place, geom_lon, geom_lat, source, content_hash,
    raw_payload
) VALUES (
    $1, $2, $7, $8, $3, $4, $5, $6, $9, $10, $11, $12, $13, $14, $15::jsonb
)
ON CONFLICT (run_id, event_id, updated_utc) DO NOTHING
"""

_INSERT_COUNTRY = """
INSERT INTO dim_countries (
    adm0_a3, name_es, admin_name, display_name, continent, subregion, source_props
) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
ON CONFLICT (adm0_a3) DO UPDATE
SET name_es = EXCLUDED.name_es,
    admin_name = EXCLUDED.admin_name,
    display_name = EXCLUDED.display_name,
    continent = EXCLUDED.continent,
    subregion = EXCLUDED.subregion,
    source_props = EXCLUDED.source_props
"""

_INSERT_HISTORICAL_KEY = """
INSERT INTO historical_2025_event_keys (event_id, occurred_utc)
VALUES ($1, $2)
ON CONFLICT (event_id) DO NOTHING
"""

_INSERT_HISTORICAL_EVENT = """
INSERT INTO historical_2025 (
    event_id, time_utc, mag, mag_type, depth_km, updated_utc, ingested_at,
    adm0_a3, place, geom_lon, geom_lat, source, content_hash, raw_payload
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14::jsonb
)
ON CONFLICT (event_id, time_utc) DO NOTHING
"""


async def load_country_dimension(
    pool: asyncpg.Pool,
    countries: tuple[Country, ...],
) -> None:
    """Idempotently seed the DB country dimension from the indexed catalog."""
    records = [
        (
            country.adm0_a3,
            country.name_es,
            country.admin_name,
            country.display_name,
            country.continent,
            country.subregion,
            _json(country.source_props),
        )
        for country in countries
    ]
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.executemany(_INSERT_COUNTRY, records)


async def persist_live_event(
    pool: asyncpg.Pool,
    event: ValidatedEvent,
    country: Country,
) -> bool:
    """UPSERT current state and append a version atomically when newer.

    Returns ``True`` only when the event inserted/updated current state. Equal
    and stale revisions return ``False`` and do not create version rows.
    """
    values = (
        event.event_id,
        event.mag,
        event.mag_type,
        event.depth_km,
        event.time_utc,
        event.updated_utc,
        event.ingested_at,
        country.adm0_a3,
        event.place,
        event.geom_lon,
        event.geom_lat,
        event.source,
        event.content_hash,
        _json(event.payload),
    )
    async with pool.acquire() as connection:
        async with connection.transaction():
            accepted = await connection.fetchrow(_UPSERT_CURRENT, *values)
            if accepted is None:
                return False
            await connection.execute(_INSERT_VERSION, *values)
    return True


async def persist_replay_started(
    pool: asyncpg.Pool,
    control: ReplayControl,
) -> None:
    """Create a run once; replay start redeliveries do not reset its counters."""
    if control.record_type != "replay_started":
        raise ValueError("control must be replay_started")
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute(
                """
                INSERT INTO replay_runs (run_id, status, source, started_at)
                VALUES ($1, 'running', 'usgs_replay', $2)
                ON CONFLICT (run_id) DO NOTHING
                """,
                control.run_id,
                control.timestamp,
            )


async def persist_replay_finished(
    pool: asyncpg.Pool,
    control: ReplayControl,
) -> bool:
    """Finish an existing run, treating an identical finish as idempotent."""
    if control.record_type != "replay_finished":
        raise ValueError("control must be replay_finished")
    async with pool.acquire() as connection:
        async with connection.transaction():
            existing = await connection.fetchrow(
                """
                SELECT status, started_at FROM replay_runs
                WHERE run_id = $1
                FOR UPDATE
                """,
                control.run_id,
            )
            if existing is None:
                return False
            if existing["status"] != "running":
                return existing["status"] == control.status
            if control.timestamp < existing["started_at"]:
                return False
            await connection.execute(
                """
                UPDATE replay_runs
                SET status = $2, finished_at = $3, error_message = $4
                WHERE run_id = $1
                """,
                control.run_id,
                control.status,
                control.timestamp,
                control.error_message,
            )
            return True


async def persist_replay_event(
    pool: asyncpg.Pool,
    event: ValidatedEvent,
    country: Country,
) -> bool:
    """Persist replay state and its accepted revision only within one active run.

    The return value reports whether the run accepted the message, not whether
    the revision changed; equal and stale event versions are successful no-ops.
    """
    if event.mode != "replay" or not event.run_id:
        raise ValueError("replay event requires replay mode and a run_id")
    values = (
        event.run_id,
        event.event_id,
        event.mag,
        event.mag_type,
        event.depth_km,
        event.time_utc,
        event.updated_utc,
        event.ingested_at,
        country.adm0_a3,
        event.place,
        event.geom_lon,
        event.geom_lat,
        event.source,
        event.content_hash,
        _json(event.payload),
    )
    async with pool.acquire() as connection:
        async with connection.transaction():
            run = await connection.fetchrow(
                """
                SELECT status FROM replay_runs
                WHERE run_id = $1
                FOR UPDATE
                """,
                event.run_id,
            )
            if run is None or run["status"] != "running":
                return False
            accepted = await connection.fetchrow(_UPSERT_REPLAY_EVENT, *values)
            if accepted is not None:
                await connection.execute(_INSERT_REPLAY_VERSION, *values)
            await connection.execute(
                """
                UPDATE replay_runs
                SET events_received = events_received + 1,
                    events_processed = events_processed + 1
                WHERE run_id = $1
                """,
                event.run_id,
            )
    return True


async def persist_historical_events(
    pool: asyncpg.Pool,
    events: list[tuple[HistoricalEvent, Country]],
    *,
    dataset_key: str | None = None,
) -> None:
    """Insert a complete baseline in one transaction without mutating prior rows.

    The registry and monthly fact table have a deferred circular foreign key.
    Writing both sets in one transaction preserves global event-ID uniqueness
    and makes a failed import all-or-nothing. Existing event IDs/facts are
    immutable and therefore use ``DO NOTHING`` on conflict.
    """
    if not events:
        raise ValueError("historical baseline batch must not be empty")

    key_records = [(event.event_id, event.time_utc) for event, _ in events]
    fact_records = [
        (
            event.event_id,
            event.time_utc,
            event.mag,
            event.mag_type,
            event.depth_km,
            event.updated_utc,
            event.ingested_at,
            country.adm0_a3,
            event.place,
            event.geom_lon,
            event.geom_lat,
            event.source,
            event.content_hash,
            _json(event.payload),
        )
        for event, country in events
    ]
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.executemany(_INSERT_HISTORICAL_KEY, key_records)
            await connection.executemany(_INSERT_HISTORICAL_EVENT, fact_records)
            if dataset_key is not None:
                await connection.execute(
                    """
                    INSERT INTO dataset_imports (dataset_key, event_count)
                    VALUES ($1, $2)
                    ON CONFLICT (dataset_key) DO NOTHING
                    """,
                    dataset_key,
                    len(events),
                )


async def persist_poll_audit(pool: asyncpg.Pool, audit: PollAudit) -> None:
    """Persist one producer poll result; repeated offsets remain harmless."""
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute(
                """
                INSERT INTO ingestion_audit (
                    poll_id, source, requested_at, completed_at, http_status,
                    content_hash, records_received, records_accepted,
                    records_excluded, records_quarantined, status, error_code,
                    error_message
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
                )
                ON CONFLICT (poll_id) DO NOTHING
                """,
                audit.poll_id,
                audit.source,
                audit.requested_at,
                audit.completed_at,
                audit.http_status,
                audit.content_hash,
                audit.records_received,
                audit.records_accepted,
                audit.records_excluded,
                audit.records_quarantined,
                audit.status,
                audit.error_code,
                audit.error_message,
            )


async def persist_quarantine(
    pool: asyncpg.Pool,
    *,
    source_topic: str,
    source_partition: int,
    source_offset: int,
    raw_message: bytes | None,
    raw_payload: Any,
    source_event_id: str | None,
    failure_reason: str,
    failure_detail: str,
) -> None:
    """Store an invalid record once per Kafka position in one DB transaction."""
    if source_topic != "earthquakes.live":
        raise ValueError(f"unsupported quarantine topic: {source_topic}")
    # Kafka tombstones have no value bytes; persist JSON null so the schema's
    # raw-data check still makes this poison record durably quarantinable.
    json_payload = (
        _json(raw_payload)
        if raw_payload is not None
        else ("null" if raw_message is None else None)
    )
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute(
                """
                INSERT INTO quarantine_events (
                    source_event_id, failure_reason, failure_detail, raw_payload,
                    raw_message, source_topic, source_partition, source_offset
                ) VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8)
                ON CONFLICT (source_topic, source_partition, source_offset) DO NOTHING
                """,
                source_event_id,
                failure_reason[:128],
                failure_detail,
                json_payload,
                raw_message,
                source_topic,
                source_partition,
                source_offset,
            )


async def persist_replay_quarantine(
    pool: asyncpg.Pool,
    *,
    source_partition: int,
    source_offset: int,
    raw_message: bytes | None,
    raw_payload: Any,
    run_id: str | None,
    source_event_id: str | None,
    failure_reason: str,
    failure_detail: str,
    count_as_event: bool = False,
) -> None:
    """Isolate replay poison records by topic/offset and, when possible, run."""
    json_payload = (
        _json(raw_payload)
        if raw_payload is not None
        else ("null" if raw_message is None else None)
    )
    safe_run_id = (
        run_id
        if isinstance(run_id, str) and run_id.strip() and len(run_id) <= 64
        else None
    )
    async with pool.acquire() as connection:
        async with connection.transaction():
            inserted = await connection.fetchrow(
                """
                INSERT INTO replay_quarantine_events (
                    run_id, source_event_id, failure_reason, failure_detail,
                    raw_payload, raw_message, source_topic, source_partition,
                    source_offset
                ) VALUES (
                    (SELECT run_id FROM replay_runs WHERE run_id = $1),
                    $2, $3, $4, $5::jsonb, $6, 'earthquakes.replay', $7, $8
                )
                ON CONFLICT (source_topic, source_partition, source_offset)
                DO NOTHING
                RETURNING quarantine_id
                """,
                safe_run_id,
                source_event_id,
                failure_reason[:128],
                failure_detail,
                json_payload,
                raw_message,
                source_partition,
                source_offset,
            )
            if inserted is not None and count_as_event and safe_run_id is not None:
                await connection.execute(
                    """
                    UPDATE replay_runs
                    SET events_received = events_received + 1,
                        events_quarantined = events_quarantined + 1
                    WHERE run_id = $1 AND status = 'running'
                    """,
                    safe_run_id,
                )


def _json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
