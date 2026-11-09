"""Explicit consumer-owned bootstrap for the cached USGS 2025 baseline."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg

from consumer.db_writer import load_country_dimension, persist_historical_events
from consumer.historical import HistoricalEvent, HistoricalImportError, normalize_historical_feature
from consumer.spatial import SpatialIndex
from scripts.download_historical_2025 import (
    HistoricalDownloadError,
    build_month_intervals,
    load_complete_cache,
    month_key,
)

LOGGER = logging.getLogger(__name__)
HISTORICAL_DATASET_KEY = "usgs_2025_magnitude_4_v1"


def historical_cache_directory(cache_root: str | Path) -> Path:
    return Path(cache_root) / "historical"


def load_historical_events(
    cache_dir: Path,
    *,
    ingested_at: datetime | None = None,
) -> tuple[list[HistoricalEvent], int]:
    """Read every verified month and deduplicate event IDs across boundaries."""
    try:
        cache = load_complete_cache(cache_dir)
    except HistoricalDownloadError as exc:
        raise HistoricalImportError(str(exc)) from exc

    events: list[HistoricalEvent] = []
    seen_ids: set[str] = set()
    cached_count = 0
    for start, end in build_month_intervals():
        key = month_key(start)
        features = cache["months"][key]["features"]
        cached_count += len(features)
        for feature in features:
            event = normalize_historical_feature(feature, ingested_at=ingested_at)
            if not start <= event.time_utc < end:
                raise HistoricalImportError(
                    f"event {event.event_id} is outside cache partition {key}"
                )
            if event.event_id in seen_ids:
                continue
            seen_ids.add(event.event_id)
            events.append(event)
    if not events:
        raise HistoricalImportError("verified historical cache contains no 2025 events")
    return events, cached_count


async def import_historical_cache(
    cache_dir: Path,
    country_geojson: Path,
    pool: asyncpg.Pool,
    *,
    ingested_at: datetime | None = None,
    dataset_key: str | None = HISTORICAL_DATASET_KEY,
) -> dict[str, int]:
    """Enrich and atomically import the immutable baseline into PostgreSQL."""
    imported_at = ingested_at or datetime.now(timezone.utc)
    events, cached_count = load_historical_events(cache_dir, ingested_at=imported_at)
    spatial_index = SpatialIndex.from_geojson(country_geojson)
    await load_country_dimension(pool, spatial_index.countries)
    if dataset_key is not None:
        async with pool.acquire() as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dataset_imports (
                    dataset_key TEXT PRIMARY KEY,
                    event_count BIGINT NOT NULL CHECK (event_count >= 0),
                    imported_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
                )
                """
            )
    enriched = [
        (event, spatial_index.find_country(event.geom_lon, event.geom_lat))
        for event in events
    ]
    await persist_historical_events(pool, enriched, dataset_key=dataset_key)
    return {
        "cached_feature_count": cached_count,
        "unique_event_count": len(events),
        "country_count": len(spatial_index.countries),
    }


async def _run(cache_dir: Path, country_geojson: Path) -> dict[str, int]:
    pool = await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "almacenamiento"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "observatorio"),
        user=os.getenv("POSTGRES_USER", "observatorio"),
        password=os.environ["POSTGRES_PASSWORD"],
        min_size=1,
        max_size=4,
    )
    try:
        return await import_historical_cache(cache_dir, country_geojson, pool)
    finally:
        await pool.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    cache_root = Path(os.getenv("USGS_CACHE_DIR", "data"))
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=historical_cache_directory(cache_root),
        help="directory containing 2025_mXX.geojson and the completed manifest",
    )
    parser.add_argument(
        "--countries",
        type=Path,
        default=Path(os.getenv("NATURAL_EARTH_GEOJSON", "/app/data/paises.geojson")),
        help="Natural Earth GeoJSON path",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    result = asyncio.run(_run(args.cache_dir, args.countries))
    LOGGER.info(
        "USGS 2025 baseline imported atomically: cached_features=%s unique_events=%s countries=%s",
        result["cached_feature_count"],
        result["unique_event_count"],
        result["country_count"],
    )


if __name__ == "__main__":
    main()
