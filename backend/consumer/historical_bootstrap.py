"""Download and import the USGS 2025 baseline once the database is ready."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import asyncpg

from consumer.historical_import import (
    HISTORICAL_DATASET_KEY,
    historical_cache_directory,
    import_historical_cache,
)
from scripts.download_historical_2025 import download_historical_2025

LOGGER = logging.getLogger(__name__)
_ADVISORY_LOCK_NAMESPACE = 814275
_ADVISORY_LOCK_ID = 2025


async def bootstrap_historical_baseline(
    pool: asyncpg.Pool,
    cache_dir: Path,
    country_geojson: Path,
) -> dict[str, Any]:
    """Fetch and import the baseline exactly once, safely across restarts."""
    async with pool.acquire() as lock_connection:
        await lock_connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dataset_imports (
                dataset_key TEXT PRIMARY KEY,
                event_count BIGINT NOT NULL CHECK (event_count >= 0),
                imported_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
            )
            """
        )
        await lock_connection.execute(
            "SELECT pg_advisory_lock($1, $2)",
            _ADVISORY_LOCK_NAMESPACE,
            _ADVISORY_LOCK_ID,
        )
        try:
            imported_count = await lock_connection.fetchval(
                "SELECT event_count FROM dataset_imports WHERE dataset_key = $1",
                HISTORICAL_DATASET_KEY,
            )
            if imported_count is not None:
                LOGGER.info(
                    "USGS 2025 baseline already imported (%s events); skipping",
                    imported_count,
                )
                return {"already_imported": True, "unique_event_count": imported_count}

            download_result = await download_historical_2025(cache_dir)
            import_result = await import_historical_cache(
                cache_dir,
                country_geojson,
                pool,
                dataset_key=HISTORICAL_DATASET_KEY,
            )
            LOGGER.info(
                "USGS 2025 baseline imported: unique_events=%s cache_hit=%s",
                import_result["unique_event_count"],
                download_result["cache_hit"],
            )
            return {
                "already_imported": False,
                "unique_event_count": import_result["unique_event_count"],
            }
        finally:
            await lock_connection.execute(
                "SELECT pg_advisory_unlock($1, $2)",
                _ADVISORY_LOCK_NAMESPACE,
                _ADVISORY_LOCK_ID,
            )


async def _run(cache_dir: Path, country_geojson: Path) -> dict[str, Any]:
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
        return await bootstrap_historical_baseline(pool, cache_dir, country_geojson)
    finally:
        await pool.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    cache_root = Path(os.getenv("USGS_CACHE_DIR", "data"))
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=historical_cache_directory(cache_root),
        help="directory containing the verified 2025 cache",
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
    asyncio.run(_run(args.cache_dir, args.countries))


if __name__ == "__main__":
    main()
