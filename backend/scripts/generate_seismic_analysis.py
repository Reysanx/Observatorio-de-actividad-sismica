"""Generate a provenance-rich JSON report for the seismic analysis."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

import asyncpg

from api.analysis import (
    COMPARISON_MAGNITUDE_THRESHOLD,
    HISTORICAL_DATASET_KEY,
    summarize_comparison,
)
from api.filters import build_geographic_predicates
from consumer.historical_import import historical_cache_directory
from scripts.download_historical_2025 import (
    HistoricalDownloadError,
    load_complete_cache,
)

LOGGER = logging.getLogger(__name__)
ANALYSIS_METHOD_VERSION = "1.0"


class BaselineConnection(Protocol):
    async def fetchrow(
        self,
        query: str,
        *args: Any,
    ) -> asyncpg.Record | None: ...


def validate_baseline(
    imported_event_count: int,
    stored_event_count: int,
    manifest: dict[str, Any],
) -> None:
    """Reject an import whose registry, rows, or source manifest disagree."""
    expected_months = {f"2025-{month:02d}" for month in range(1, 13)}
    manifest_months = manifest.get("months")
    manifest_query = manifest.get("query")
    if imported_event_count <= 0 or stored_event_count != imported_event_count:
        raise ValueError("2025 baseline is missing, empty, or inconsistent with its import record")
    if (
        manifest.get("year") != 2025
        or manifest.get("complete") is not True
        or not isinstance(manifest_months, dict)
        or set(manifest_months) != expected_months
        or manifest.get("unique_event_count") != imported_event_count
        or not isinstance(manifest_query, dict)
        or manifest_query.get("minmagnitude") != "4.0"
    ):
        raise ValueError("2025 source manifest is incomplete or inconsistent with the import")


async def _load_baseline_metadata(
    connection: BaselineConnection,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    row = await connection.fetchrow(
        """
        SELECT imports.dataset_key, imports.event_count AS imported_event_count,
               imports.imported_at,
               count(baseline.event_id)::BIGINT AS stored_event_count,
               min(baseline.time_utc) AS first_event_utc,
               max(baseline.time_utc) AS last_event_utc
        FROM dataset_imports imports
        LEFT JOIN historical_2025 baseline ON TRUE
        WHERE imports.dataset_key = $1
        GROUP BY imports.dataset_key, imports.event_count, imports.imported_at
        """,
        HISTORICAL_DATASET_KEY,
    )
    if row is None:
        raise ValueError("successful 2025 baseline import is not registered")
    imported_count = int(row["imported_event_count"])
    stored_count = int(row["stored_event_count"])
    validate_baseline(imported_count, stored_count, manifest)
    if row["first_event_utc"] is None or row["last_event_utc"] is None:
        raise ValueError("2025 baseline has no event timestamps")
    if row["first_event_utc"] < datetime(2025, 1, 1, tzinfo=timezone.utc):
        raise ValueError("2025 baseline contains events before the target year")
    if row["last_event_utc"] >= datetime(2026, 1, 1, tzinfo=timezone.utc):
        raise ValueError("2025 baseline contains events after the target year")
    months = manifest["months"]
    return {
        "dataset_key": row["dataset_key"],
        "imported_event_count": imported_count,
        "stored_event_count": stored_count,
        "imported_at_utc": row["imported_at"].astimezone(timezone.utc).isoformat(),
        "first_event_utc": row["first_event_utc"].astimezone(timezone.utc).isoformat(),
        "last_event_utc": row["last_event_utc"].astimezone(timezone.utc).isoformat(),
        "source": "USGS FDSNWS event catalog",
        "source_manifest": {
            "generated_at": manifest.get("generated_at"),
            "schema_version": manifest.get("schema_version"),
            "query": manifest.get("query"),
            "unique_event_count": manifest.get("unique_event_count"),
            "months": {
                key: {
                    "file": value["file"],
                    "sha256": value["sha256"],
                    "feature_count": value["feature_count"],
                }
                for key, value in sorted(months.items())
            },
        },
    }


async def _fetch_cohort_summary(
    connection: asyncpg.Connection,
    relation: str,
    event_alias: str,
    country_alias: str,
    start: datetime,
    end: datetime,
    filters: dict[str, str | None],
) -> dict[str, int | float | None]:
    predicate, geography_values = build_geographic_predicates(
        **filters,
        event_alias=event_alias,
        country_alias=country_alias,
        first_parameter=3,
    )
    row = await connection.fetchrow(
        f"""
        SELECT count(*)::BIGINT AS eligible_event_count,
               count(*) FILTER (WHERE {event_alias}.adm0_a3 <> 'N/A')::BIGINT
                   AS assigned_event_count,
               count(*) FILTER (WHERE {event_alias}.adm0_a3 = 'N/A')::BIGINT
                   AS unassigned_event_count
        FROM {relation} {event_alias}
        JOIN dim_countries {country_alias}
          ON {country_alias}.adm0_a3 = {event_alias}.adm0_a3
        WHERE {event_alias}.time_utc >= $1 AND {event_alias}.time_utc < $2
          AND {event_alias}.mag >= {COMPARISON_MAGNITUDE_THRESHOLD}
          AND ({predicate})
        """,
        start,
        end,
        *geography_values,
    )
    total = int(row["eligible_event_count"])
    assigned = int(row["assigned_event_count"])
    unassigned = int(row["unassigned_event_count"])
    return {
        "eligible_event_count": total,
        "assigned_event_count": assigned,
        "unassigned_event_count": unassigned,
        "assigned_share": assigned / total if total else None,
        "unassigned_share": unassigned / total if total else None,
    }


async def generate_report(
    pool: asyncpg.Pool,
    cache_dir: Path,
    filters: dict[str, str | None],
) -> dict[str, Any]:
    """Generate all required conclusions from one read-only database snapshot."""
    cache = load_complete_cache(cache_dir)
    manifest = cache["manifest"]
    generated_at = datetime.now(timezone.utc)
    recent_start = generated_at - timedelta(hours=24)

    async with pool.acquire() as connection:
        async with connection.transaction(isolation="repeatable_read", readonly=True):
            baseline = await _load_baseline_metadata(connection, manifest)
            recent_summary = await _fetch_cohort_summary(
                connection,
                "current_earthquakes",
                "live",
                "live_country",
                recent_start,
                generated_at,
                filters,
            )
            historical_summary = await _fetch_cohort_summary(
                connection,
                "historical_2025",
                "baseline",
                "baseline_country",
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                filters,
            )
            geography_predicate, geography_values = build_geographic_predicates(
                **filters,
                event_alias="baseline",
                country_alias="baseline_country",
                first_parameter=1,
            )
            daily_rows = await connection.fetch(
                f"""
                WITH calendar AS (
                    SELECT generate_series(
                        DATE '2025-01-01',
                        DATE '2025-12-31',
                        INTERVAL '1 day'
                    )::DATE AS day_utc
                )
                SELECT calendar.day_utc,
                       count(baseline.event_id)::BIGINT AS event_count
                FROM calendar
                LEFT JOIN (
                    historical_2025 baseline
                    JOIN dim_countries baseline_country
                      ON baseline_country.adm0_a3 = baseline.adm0_a3
                )
                  ON baseline.time_utc >= calendar.day_utc::TIMESTAMP AT TIME ZONE 'UTC'
                 AND baseline.time_utc < (calendar.day_utc + 1)::TIMESTAMP AT TIME ZONE 'UTC'
                 AND baseline.mag >= {COMPARISON_MAGNITUDE_THRESHOLD}
                 AND ({geography_predicate})
                GROUP BY calendar.day_utc
                ORDER BY calendar.day_utc
                """,
                *geography_values,
            )
            depth_rows = await connection.fetch(
                f"""
                SELECT COALESCE(NULLIF(baseline_country.subregion, ''), 'Sin subregión')
                           AS geographic_region,
                       count(baseline.depth_km) FILTER (
                           WHERE baseline.depth_km::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
                       )::BIGINT AS depth_population_count,
                       percentile_cont(0.90) WITHIN GROUP (ORDER BY baseline.depth_km)
                           FILTER (
                               WHERE baseline.depth_km::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
                           ) AS depth_p90_km
                FROM historical_2025 baseline
                JOIN dim_countries baseline_country
                  ON baseline_country.adm0_a3 = baseline.adm0_a3
                WHERE baseline.time_utc >= TIMESTAMPTZ '2025-01-01 00:00:00+00'
                  AND baseline.time_utc < TIMESTAMPTZ '2026-01-01 00:00:00+00'
                  AND baseline.mag >= {COMPARISON_MAGNITUDE_THRESHOLD}
                  AND ({geography_predicate})
                GROUP BY 1
                ORDER BY 1
                """,
                *geography_values,
            )

    if len(daily_rows) != 365:
        raise ValueError(f"expected 365 daily rows, received {len(daily_rows)}")
    daily_counts = [int(row["event_count"]) for row in daily_rows]
    comparison = summarize_comparison(
        daily_counts,
        int(recent_summary["eligible_event_count"]),
    )
    return {
        "report_schema_version": 1,
        "analysis_method_version": ANALYSIS_METHOD_VERSION,
        "baseline_query_version": HISTORICAL_DATASET_KEY,
        "calculation_methods": {
            "daily_average": "arithmetic_mean_over_365_utc_days",
            "daily_standard_deviation": "population_standard_deviation_ddof_0",
            "depth_p90": "hyndman_fan_type_7",
            "time_zone": "UTC",
        },
        "analysis_id": str(uuid.uuid4()),
        "generated_at_utc": generated_at.isoformat(),
        "source": baseline,
        "comparison": {
            **comparison,
            "recent_event_count": recent_summary["eligible_event_count"],
            "magnitude_threshold": COMPARISON_MAGNITUDE_THRESHOLD,
            "recent_window_start_utc": recent_start.isoformat(),
            "recent_window_end_utc": generated_at.isoformat(),
            "geographic_filters": filters,
        },
        "annual_daily_counts": [
            {
                "date_utc": row["day_utc"].isoformat(),
                "event_count": int(row["event_count"]),
            }
            for row in daily_rows
        ],
        "geographic_assignment": {
            "recent_24h": recent_summary,
            "historical_2025": historical_summary,
            "unassigned_caveat": (
                "Sin país asignado indica falta de coincidencia con el catálogo "
                "de polígonos y no demuestra por sí solo una ubicación submarina."
            ),
        },
        "historical_depth_by_subregion": [
            {
                "geographic_region": row["geographic_region"],
                "depth_population_count": int(row["depth_population_count"]),
                "depth_p90_km": row["depth_p90_km"],
                "method": "hyndman_fan_type_7",
            }
            for row in depth_rows
        ],
        "limitations": [
            "La ventana reciente móvil de 24 horas no es un día natural y no equivale a una muestra aleatoria del año 2025.",
            "La desviación observada describe variabilidad histórica y no predice riesgo sísmico.",
            "Las interpretaciones tectónicas requieren fuentes externas; estas métricas no demuestran causalidad.",
        ],
    }


async def _run(args: argparse.Namespace) -> None:
    cache_dir = historical_cache_directory(args.cache_root)
    filters = {
        "adm0_a3": args.adm0_a3,
        "continent": args.continent,
        "subregion": args.subregion,
    }
    pool = await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "almacenamiento"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "observatorio"),
        user=os.getenv("POSTGRES_USER", "observatorio"),
        password=os.environ["POSTGRES_PASSWORD"],
        min_size=1,
        max_size=2,
    )
    try:
        report = await generate_report(pool, cache_dir, filters)
    finally:
        await pool.close()
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2, allow_nan=False)
    sys.stdout.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path(os.getenv("USGS_CACHE_DIR", "/var/lib/observatorio/cache")),
    )
    parser.add_argument("--adm0-a3")
    parser.add_argument("--continent")
    parser.add_argument("--subregion")
    args = parser.parse_args()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    try:
        asyncio.run(_run(args))
    except (asyncpg.PostgresError, HistoricalDownloadError, OSError, ValueError) as exc:
        LOGGER.error("Analysis report generation failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
