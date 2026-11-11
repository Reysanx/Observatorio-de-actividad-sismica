"""Build a read-only evidence report for the three source datasets."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import asyncpg
from shapely import __version__ as shapely_version

from consumer.spatial import SpatialIndex
from scripts.download_historical_2025 import (
    build_month_intervals,
    load_complete_cache,
    month_key,
)


def _iso_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def summarize_live_polls(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize poll records without treating them as user/API queries."""
    status_counts = {"succeeded": 0, "partial": 0, "failed": 0}
    http_status_counts: dict[str, int] = {}
    received = accepted = excluded = quarantined = 0
    error_counts: dict[str, int] = {}
    durations_ms: list[float] = []
    subsecond_durations_ms: list[float] = []
    requested_at: list[datetime] = []
    timestamp_values: list[datetime] = []

    for row in rows:
        status = row["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        http_status = row["http_status"]
        http_status_key = str(http_status) if http_status is not None else "none"
        http_status_counts[http_status_key] = (
            http_status_counts.get(http_status_key, 0) + 1
        )
        received += row["records_received"]
        accepted += row["records_accepted"]
        excluded += row["records_excluded"]
        quarantined += row["records_quarantined"]

        started = row["requested_at"]
        completed = row["completed_at"]
        requested_at.append(started)
        timestamp_values.extend((started, completed))
        duration_ms = (completed - started).total_seconds() * 1000
        durations_ms.append(duration_ms)
        if started.microsecond or completed.microsecond:
            subsecond_durations_ms.append(duration_ms)

        error_code = row["error_code"]
        error_message = row["error_message"]
        if status != "succeeded" or error_code is not None or error_message is not None:
            key = error_code or "unspecified"
            error_counts[key] = error_counts.get(key, 0) + 1

    ordered_requests = sorted(requested_at)
    intervals_seconds = [
        (right - left).total_seconds()
        for left, right in zip(ordered_requests, ordered_requests[1:])
    ]
    whole_second_timestamps = bool(timestamp_values) and all(
        value.microsecond == 0 for value in timestamp_values
    )

    return {
        "poll_count": len(rows),
        "status_counts": status_counts,
        "http_status_counts": http_status_counts,
        "records_received": received,
        "records_accepted": accepted,
        "records_excluded": excluded,
        "records_quarantined": quarantined,
        "error_count": sum(error_counts.values()),
        "errors_by_code": error_counts,
        "first_requested_at_utc": _iso_timestamp(min(requested_at))
        if requested_at
        else None,
        "last_completed_at_utc": _iso_timestamp(
            max(row["completed_at"] for row in rows)
        )
        if rows
        else None,
        "poll_interval_median_seconds": statistics.median(intervals_seconds)
        if intervals_seconds
        else None,
        "stored_duration_median_ms": statistics.median(durations_ms)
        if durations_ms
        else None,
        "stored_duration_p95_ms": _percentile(durations_ms, 0.95),
        "stored_duration_max_ms": max(durations_ms) if durations_ms else None,
        "subsecond_precision_poll_count": len(subsecond_durations_ms),
        "subsecond_duration_median_ms": statistics.median(subsecond_durations_ms)
        if subsecond_durations_ms
        else None,
        "subsecond_duration_p95_ms": _percentile(subsecond_durations_ms, 0.95),
        "subsecond_duration_max_ms": max(subsecond_durations_ms)
        if subsecond_durations_ms
        else None,
        "timestamps_have_whole_second_precision": whole_second_timestamps,
        "duration_note": (
            "Whole-second rows are quantized and are not request-latency "
            "measurements. Subsecond metrics include only rows with fractional "
            "timestamps."
        ),
    }


def inspect_historical_cache(cache_dir: Path) -> dict[str, Any]:
    started = time.perf_counter()
    cache = load_complete_cache(cache_dir)
    validation_seconds = time.perf_counter() - started

    manifest_path = cache_dir / "2025_manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    cache_digest = hashlib.sha256()
    cache_digest.update(manifest_bytes)
    monthly_counts: dict[str, int] = {}
    event_ids: set[str] = set()
    for interval_start, _ in build_month_intervals():
        key = month_key(interval_start)
        file_name = f"2025_m{interval_start.month:02d}.geojson"
        file_bytes = (cache_dir / file_name).read_bytes()
        cache_digest.update(file_name.encode("utf-8"))
        cache_digest.update(file_bytes)
        features = cache["months"][key]["features"]
        monthly_counts[file_name] = len(features)
        event_ids.update(feature["id"] for feature in features)

    return {
        "source_id": "usgs_2025",
        "kind": "verified_historical_cache",
        "cache_validation_seconds": validation_seconds,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "cache_sha256": cache_digest.hexdigest(),
        "manifest_generated_at": cache["manifest"].get("generated_at"),
        "monthly_feature_counts": monthly_counts,
        "cached_feature_count": sum(monthly_counts.values()),
        "unique_event_ids": len(event_ids),
        "validation_errors": [],
        "download_and_database_import_duration_recorded": False,
        "duration_note": (
            "This run measures local cache validation only. The existing import "
            "registry has no download or database-import duration."
        ),
    }


def inspect_country_catalog(path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    index = SpatialIndex.from_geojson(path)
    load_seconds = time.perf_counter() - started
    return {
        "source_id": "natural_earth_countries",
        "kind": "local_reference_catalog",
        "file_name": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "features_indexed": len(index.countries),
        "load_and_index_seconds": load_seconds,
        "errors": [],
        "duration_note": (
            "Catalog validation and in-memory STRtree construction; this is not "
            "a remote download or database-import duration."
        ),
    }


async def collect_database_evidence(pool: asyncpg.Pool) -> dict[str, Any]:
    async with pool.acquire() as connection:
        async with connection.transaction(
            isolation="repeatable_read", readonly=True
        ):
            captured_at = await connection.fetchval("SELECT clock_timestamp()")
            poll_rows = await connection.fetch(
                """
                SELECT status, http_status, requested_at, completed_at, records_received,
                       records_accepted, records_excluded, records_quarantined,
                       error_code, error_message
                FROM ingestion_audit
                WHERE source = 'usgs_live'
                ORDER BY requested_at
                """
            )
            import_record = await connection.fetchrow(
                """
                SELECT dataset_key, event_count, imported_at
                FROM dataset_imports
                WHERE dataset_key = 'usgs_2025_magnitude_4_v1'
                """
            )
            historical_rows = await connection.fetchrow(
                """
                SELECT count(*) AS row_count, count(DISTINCT event_id) AS unique_events
                FROM historical_2025
                """
            )

    return {
        "captured_at_utc": _iso_timestamp(captured_at),
        "live_poll_audit": summarize_live_polls(poll_rows),
        "historical_database_import": {
            "dataset_key": import_record["dataset_key"] if import_record else None,
            "registered_event_count": import_record["event_count"]
            if import_record
            else None,
            "imported_at_utc": _iso_timestamp(import_record["imported_at"])
            if import_record
            else None,
            "historical_rows": historical_rows["row_count"],
            "unique_event_ids": historical_rows["unique_events"],
            "errors": [],
        },
    }


async def build_report(cache_dir: Path, countries_path: Path) -> dict[str, Any]:
    cache_evidence = inspect_historical_cache(cache_dir)
    country_evidence = inspect_country_catalog(countries_path)
    pool = await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "almacenamiento"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "observatorio"),
        user=os.getenv("POSTGRES_USER", "observatorio"),
        password=os.environ["POSTGRES_PASSWORD"],
        min_size=1,
        max_size=1,
    )
    try:
        database_evidence = await collect_database_evidence(pool)
    finally:
        await pool.close()

    return {
        "report": "three_source_ingestion_evidence",
        "mode": "read_only",
        "database_snapshot_at_utc": database_evidence["captured_at_utc"],
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "shapely": shapely_version,
        },
        "sources": [
            {
                "source_id": "usgs_live",
                "kind": "live_feed_poll_audit",
                "evidence": database_evidence["live_poll_audit"],
            },
            {
                **cache_evidence,
                "database_import": database_evidence[
                    "historical_database_import"
                ],
            },
            country_evidence,
        ],
        "audit_semantics": (
            "ingestion_audit records source poll attempts and their outcomes; it "
            "does not record user/API reads. User-query auditing would require a "
            "separate table and contract."
        ),
    }


def main() -> None:
    cache_root = Path(os.getenv("USGS_CACHE_DIR", "/var/lib/observatorio/cache"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=cache_root / "historical",
        help="verified 2025 cache directory",
    )
    parser.add_argument(
        "--countries",
        type=Path,
        default=Path(os.getenv("NATURAL_EARTH_GEOJSON", "/app/data/paises.geojson")),
        help="Natural Earth GeoJSON path",
    )
    args = parser.parse_args()
    report = asyncio.run(build_report(args.cache_dir, args.countries))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
