"""Generate a read-only, reproducible report for the six data-quality dimensions."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import math
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import asyncpg

from api.analysis import HISTORICAL_DATASET_KEY, type_7_percentile
from consumer.historical_import import (
    HistoricalImportError,
    historical_cache_directory,
    normalize_historical_feature,
)
from scripts.download_historical_2025 import (
    HistoricalDownloadError,
    build_month_intervals,
    load_complete_cache,
    month_key,
)

LOGGER = logging.getLogger(__name__)
METHOD_VERSION = "1.0"
RULE_SET_VERSION = "historical.py:1.0;quality.py:1.0"
DIMENSIONS = (
    "completeness",
    "uniqueness",
    "validity",
    "consistency",
    "currency",
    "accuracy",
)
UTC = timezone.utc
YEAR_START = datetime(2025, 1, 1, tzinfo=UTC)
YEAR_END = datetime(2026, 1, 1, tzinfo=UTC)


class ReportError(ValueError):
    """Raised when source data cannot support a trustworthy report."""


@dataclass(frozen=True)
class CacheSnapshot:
    features: list[dict[str, Any]]
    monthly_feature_count: int
    duplicate_feature_count: int
    manifest: dict[str, Any]
    manifest_sha256: str
    month_sha256: dict[str, str]


@dataclass(frozen=True)
class DatabaseSnapshot:
    import_record: Mapping[str, Any]
    historical_rows: list[Mapping[str, Any]]
    audit_rows: list[Mapping[str, Any]]
    current_rows: list[Mapping[str, Any]]
    quarantine_count: int
    quarantine_first_at: datetime | None
    quarantine_last_at: datetime | None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ReportError("source data is not finite, serializable JSON") from exc


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ReportError("database timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _row_dict(row: Mapping[str, Any] | asyncpg.Record) -> dict[str, Any]:
    return dict(row)


def snapshot_from_loaded_cache(
    cache: Mapping[str, Any],
    manifest_sha256: str,
) -> CacheSnapshot:
    """Build a unique-ID source cohort while retaining monthly duplicate counts."""
    manifest = cache.get("manifest")
    months = cache.get("months")
    if not isinstance(manifest, dict) or not isinstance(months, dict):
        raise ReportError("verified cache is missing its manifest or monthly files")

    unique_features: dict[str, dict[str, Any]] = {}
    source_hashes: dict[str, str] = {}
    monthly_feature_count = 0
    duplicate_feature_count = 0
    month_hashes: dict[str, str] = {}

    expected_months = {month_key(start) for start, _ in build_month_intervals()}
    if set(months) != expected_months:
        raise ReportError("verified cache does not contain all 12 monthly partitions")

    for key in sorted(expected_months):
        collection = months[key]
        if not isinstance(collection, dict) or not isinstance(collection.get("features"), list):
            raise ReportError(f"cached month {key} has no Feature list")
        manifest_entry = manifest.get("months", {}).get(key)
        if not isinstance(manifest_entry, dict):
            raise ReportError(f"manifest entry for {key} is missing")
        month_hashes[key] = manifest_entry["sha256"]
        for feature in collection["features"]:
            monthly_feature_count += 1
            if not isinstance(feature, dict):
                raise ReportError(f"cached month {key} contains a non-object Feature")
            event_id = feature.get("id")
            if not isinstance(event_id, str) or not event_id.strip():
                raise ReportError(f"cached month {key} contains a Feature without a valid id")
            canonical = _canonical_json(feature)
            digest = _sha256(canonical.encode("utf-8"))
            if event_id in unique_features:
                if source_hashes[event_id] != digest:
                    raise ReportError(f"conflicting cached Features share event_id {event_id}")
                duplicate_feature_count += 1
                continue
            unique_features[event_id] = feature
            source_hashes[event_id] = digest

    declared_unique_count = manifest.get("unique_event_count")
    if declared_unique_count != len(unique_features):
        raise ReportError("cache manifest unique_event_count disagrees with cached Feature IDs")
    if not unique_features:
        raise ReportError("verified historical cache contains no 2025 events")

    return CacheSnapshot(
        features=list(unique_features.values()),
        monthly_feature_count=monthly_feature_count,
        duplicate_feature_count=duplicate_feature_count,
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        month_sha256=month_hashes,
    )


def load_cache_snapshot(cache_dir: Path) -> CacheSnapshot:
    """Load all cached months only after the downloader verifies their hashes."""
    try:
        cache = load_complete_cache(cache_dir)
        manifest_bytes = (cache_dir / "2025_manifest.json").read_bytes()
    except (HistoricalDownloadError, OSError) as exc:
        raise ReportError(f"unable to load verified historical cache: {exc}") from exc
    return snapshot_from_loaded_cache(cache, _sha256(manifest_bytes))


async def read_database_snapshot(connection: asyncpg.Connection) -> DatabaseSnapshot:
    """Read historical, live-audit, and quarantine evidence in one read-only snapshot."""
    async with connection.transaction(isolation="repeatable_read", readonly=True):
        import_record = await connection.fetchrow(
            """
            SELECT dataset_key, event_count, imported_at
            FROM dataset_imports
            WHERE dataset_key = $1
            """,
            HISTORICAL_DATASET_KEY,
        )
        if import_record is None:
            raise ReportError("the USGS 2025 dataset import is not registered")

        historical_rows = await connection.fetch(
            """
            SELECT event_id, time_utc, mag, mag_type, depth_km, updated_utc,
                   ingested_at, adm0_a3, place, geom_lon, geom_lat, source,
                   raw_payload
            FROM historical_2025
            ORDER BY event_id, time_utc
            """
        )
        audit_rows = await connection.fetch(
            """
            SELECT poll_id, source, requested_at, completed_at, http_status,
                   records_received, records_accepted, records_excluded,
                   records_quarantined, status
            FROM ingestion_audit
            WHERE source = 'usgs_live'
            ORDER BY poll_id
            """
        )
        current_rows = await connection.fetch(
            """
            SELECT event_id, updated_utc, ingested_at
            FROM current_earthquakes
            ORDER BY event_id
            """
        )
        quarantine_summary = await connection.fetchrow(
            """
            SELECT count(*)::BIGINT AS row_count,
                   min(quarantined_at) AS first_at,
                   max(quarantined_at) AS last_at
            FROM quarantine_events
            """
        )

    return DatabaseSnapshot(
        import_record=_row_dict(import_record),
        historical_rows=[_row_dict(row) for row in historical_rows],
        audit_rows=[_row_dict(row) for row in audit_rows],
        current_rows=[_row_dict(row) for row in current_rows],
        quarantine_count=int(quarantine_summary["row_count"]),
        quarantine_first_at=quarantine_summary["first_at"],
        quarantine_last_at=quarantine_summary["last_at"],
    )


def _decode_payload(value: Any, event_id: str) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ReportError(f"stored raw_payload is invalid JSON for event {event_id}") from exc
    return value


def _index_database_rows(
    rows: list[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for source_row in rows:
        row = _row_dict(source_row)
        event_id = row.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ReportError("historical database row has no event_id")
        if event_id in indexed:
            raise ReportError(f"historical database contains duplicate event_id {event_id}")
        row["raw_payload"] = _decode_payload(row.get("raw_payload"), event_id)
        indexed[event_id] = row
    return indexed


def _path_value(value: Any, path: str) -> Any:
    current = value
    for component in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(component)
    return current


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    converted = float(value)
    return converted if math.isfinite(converted) else None


def _timestamp_from_ms(value: Any) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def _valid_source_feature(feature: dict[str, Any]) -> bool:
    try:
        normalize_historical_feature(feature, ingested_at=YEAR_END)
    except (HistoricalImportError, TypeError, ValueError):
        return False
    return True


def _valid_stored_row(row: Mapping[str, Any]) -> bool:
    magnitude = _number(row.get("mag"))
    depth = _number(row.get("depth_km"))
    longitude = _number(row.get("geom_lon"))
    latitude = _number(row.get("geom_lat"))
    time_utc = row.get("time_utc")
    updated_utc = row.get("updated_utc")
    return bool(
        isinstance(row.get("event_id"), str)
        and magnitude is not None
        and magnitude >= 4
        and depth is not None
        and longitude is not None
        and -180 <= longitude <= 180
        and latitude is not None
        and -90 <= latitude <= 90
        and isinstance(time_utc, datetime)
        and isinstance(updated_utc, datetime)
        and time_utc.utcoffset() is not None
        and updated_utc.utcoffset() is not None
        and time_utc <= updated_utc
        and YEAR_START <= time_utc.astimezone(UTC) < YEAR_END
        and row.get("source") == "usgs_2025"
    )


def _feature_matches_row(feature: dict[str, Any], row: Mapping[str, Any]) -> bool:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return False
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 3:
        return False

    source_time = _timestamp_from_ms(properties.get("time"))
    source_updated = _timestamp_from_ms(properties.get("updated"))
    if source_time is None or source_updated is None:
        return False
    source_mag = _number(properties.get("mag"))
    source_depth = _number(coordinates[2])
    source_longitude = _number(coordinates[0])
    source_latitude = _number(coordinates[1])
    if any(value is None for value in (source_mag, source_depth, source_longitude, source_latitude)):
        return False
    source_values = (
        row.get("event_id") == feature.get("id"),
        _number(row.get("mag")) == source_mag,
        row.get("mag_type") == properties.get("magType"),
        _number(row.get("depth_km")) == source_depth,
        row.get("time_utc") == source_time,
        row.get("updated_utc") == source_updated,
        row.get("place") == properties.get("place"),
        _number(row.get("geom_lon")) == source_longitude,
        _number(row.get("geom_lat")) == source_latitude,
    )
    return all(source_values)


def _metric(
    metric_id: str,
    stage: str,
    numerator: int | None,
    denominator: int | None,
    value: float | None,
    unit: str | None,
    formula: str,
    evidence: list[str] | None = None,
    limitations: list[str] | None = None,
    *,
    reference_independent: bool | None = None,
    proxy: bool | None = None,
) -> dict[str, Any]:
    result = {
        "metric_id": metric_id,
        "stage": stage,
        "numerator": numerator,
        "denominator": denominator,
        "value": round(value, 6) if value is not None else None,
        "unit": unit,
        "formula": formula,
        "evidence": evidence or [],
        "limitations": limitations or [],
    }
    if reference_independent is not None:
        result["reference_independent"] = reference_independent
    if proxy is not None:
        result["proxy"] = proxy
    return result


def _not_verifiable(
    metric_id: str,
    reason: str,
    *,
    reference_independent: bool | None = None,
) -> dict[str, Any]:
    return _metric(
        metric_id,
        "not_verifiable",
        None,
        None,
        None,
        None,
        "No se calcula: faltan datos o una referencia adecuada.",
        limitations=[reason],
        reference_independent=reference_independent,
        proxy=False if reference_independent is not None else None,
    )


def _ratio_metric(
    metric_id: str,
    stage: str,
    numerator: int,
    denominator: int,
    formula: str,
    evidence: str,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    if denominator <= 0:
        return _not_verifiable(metric_id, "La población elegible está vacía.")
    return _metric(
        metric_id,
        stage,
        numerator,
        denominator,
        100.0 * numerator / denominator,
        "percent",
        formula,
        [evidence],
        limitations,
    )


def _field_present(value: Any, path: str) -> bool:
    return _path_value(value, path) is not None


def _field_metrics(
    features: list[dict[str, Any]],
    rows: dict[str, dict[str, Any]],
    matched_ids: set[str],
) -> list[dict[str, Any]]:
    fields = (
        ("event_id", "id", "identificador", False),
        ("mag", "properties.mag", "magnitud", False),
        ("mag_type", "properties.magType", "tipo de magnitud (opcional)", True),
        ("place", "properties.place", "descripción del lugar (opcional)", True),
        ("time", "properties.time", "tiempo de ocurrencia", False),
        ("updated", "properties.updated", "tiempo de actualización", False),
        ("geometry", "geometry.coordinates", "coordenadas GeoJSON", False),
    )
    metrics: list[dict[str, Any]] = []
    for metric_id, source_path, label, optional in fields:
        if metric_id == "geometry":
            source_count = sum(
                isinstance(_path_value(feature, source_path), list)
                and bool(_path_value(feature, source_path))
                for feature in features
            )
        else:
            source_count = sum(_field_present(feature, source_path) for feature in features)
        source_metric = _ratio_metric(
            f"source_{metric_id}_present",
            "before",
            source_count,
            len(features),
            f"presencias no nulas de {label} / Features únicos de la caché * 100",
            "Features de los 12 archivos mensuales verificados por el manifest.",
            ["El campo es opcional; su ausencia no equivale por sí sola a incumplimiento."]
            if optional
            else None,
        )
        metrics.append(source_metric)

        persisted_values = {
            "event_id": "event_id",
            "mag": "mag",
            "mag_type": "mag_type",
            "place": "place",
            "time": "time_utc",
            "updated": "updated_utc",
            "geometry": "geom_lon",
        }
        persisted_field = persisted_values[metric_id]
        if metric_id == "geometry":
            persisted_count = sum(
                rows[event_id].get("geom_lon") is not None
                and rows[event_id].get("geom_lat") is not None
                for event_id in matched_ids
            )
        else:
            persisted_count = sum(
                rows[event_id].get(persisted_field) is not None
                for event_id in matched_ids
            )
        metrics.append(
            _ratio_metric(
                f"persisted_{metric_id}_present",
                "after",
                persisted_count,
                len(matched_ids),
                f"valores no nulos de {label} / filas históricas emparejadas * 100",
                "Columnas de historical_2025 para event_id emparejados.",
                ["El campo es opcional; su ausencia no equivale por sí sola a incumplimiento."]
                if optional
                else None,
            )
        )
    return metrics


def _stat_metrics(
    metric_prefix: str,
    stage: str,
    values: list[float],
    evidence: str,
    limitations: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not values:
        return [
            _not_verifiable(
                f"{metric_prefix}_{statistic}",
                "No hay timestamps válidos y comparables para calcular la latencia.",
            )
            for statistic in ("min", "median", "p90", "max")
        ]
    count = len(values)
    ordered = sorted(values)
    p90 = type_7_percentile(values, 0.9)
    median = (
        ordered[count // 2]
        if count % 2
        else (ordered[count // 2 - 1] + ordered[count // 2]) / 2
    )
    results: list[dict[str, Any]] = []
    for statistic, value, formula in (
        ("min", min(values), f"mínimo({metric_prefix})"),
        ("median", median, f"mediana({metric_prefix})"),
        ("p90", p90, f"percentil 90 Hyndman-Fan tipo 7({metric_prefix})"),
        ("max", max(values), f"máximo({metric_prefix})"),
    ):
        results.append(
            _metric(
                f"{metric_prefix}_{statistic}",
                stage,
                count,
                count,
                value,
                "milliseconds",
                formula,
                [evidence],
                limitations,
            )
        )
    return results


def _source_delay_values(features: list[dict[str, Any]]) -> tuple[list[float], int]:
    values: list[float] = []
    invalid_count = 0
    for feature in features:
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            invalid_count += 1
            continue
        occurred = _timestamp_from_ms(properties.get("time"))
        updated = _timestamp_from_ms(properties.get("updated"))
        if occurred is None or updated is None or updated < occurred:
            invalid_count += 1
            continue
        values.append((updated - occurred).total_seconds() * 1000)
    return values, invalid_count


def _historical_population(
    cache: CacheSnapshot,
    rows: list[Mapping[str, Any]],
    import_record: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    db_by_id = _index_database_rows(rows)
    source_by_id = {feature["id"]: feature for feature in cache.features}
    source_ids = set(source_by_id)
    database_ids = set(db_by_id)
    matched_ids = source_ids & database_ids
    missing_ids = source_ids - database_ids
    unmatched_ids = database_ids - source_ids
    field_metrics = _field_metrics(cache.features, db_by_id, matched_ids)

    source_unique_metric = _ratio_metric(
        "unique_source_ids",
        "before",
        len(source_ids),
        cache.monthly_feature_count,
        "IDs de evento únicos / Features de las particiones mensuales * 100",
        "IDs de Features deduplicados entre los 12 archivos de caché.",
    )
    persisted_unique_metric = _ratio_metric(
        "unique_persisted_ids",
        "after",
        len(database_ids),
        len(rows),
        "event_id distintos / filas de historical_2025 * 100",
        "Lectura de solo lectura de historical_2025.",
    )

    source_valid = sum(_valid_source_feature(feature) for feature in cache.features)
    stored_valid = sum(_valid_stored_row(row) for row in db_by_id.values())
    validity_metrics = [
        _ratio_metric(
            "source_features_satisfying_historical_rules",
            "before",
            source_valid,
            len(cache.features),
            "Features válidas según normalize_historical_feature / Features únicos * 100",
            "Reglas de importación histórica backend/consumer/historical.py.",
        ),
        _ratio_metric(
            "persisted_rows_satisfying_historical_rules",
            "after",
            stored_valid,
            len(rows),
            "Filas que cumplen restricciones históricas aplicables / filas leídas * 100",
            "Columnas y reglas de historical_2025 definidas en backend/db/init.sql.",
        ),
    ]

    matched_field_count = 0
    matching_rows = 0
    raw_payload_matches = 0
    consistency_rows = 0
    for event_id in matched_ids:
        feature = source_by_id[event_id]
        row = db_by_id[event_id]
        if _feature_matches_row(feature, row):
            matching_rows += 1
        payload_matches = row.get("raw_payload") == feature
        raw_payload_matches += payload_matches
        payload = row.get("raw_payload")
        properties = _path_value(payload, "properties")
        source_time = _timestamp_from_ms(_path_value(payload, "properties.time"))
        source_updated = _timestamp_from_ms(_path_value(payload, "properties.updated"))
        internally_consistent = bool(
            isinstance(payload, dict)
            and payload.get("id") == event_id
            and isinstance(properties, dict)
            and isinstance(row.get("time_utc"), datetime)
            and isinstance(row.get("updated_utc"), datetime)
            and row.get("time_utc") == source_time
            and row.get("updated_utc") == source_updated
            and row.get("time_utc") <= row.get("updated_utc")
        )
        consistency_rows += internally_consistent
        matched_field_count += 1

    consistency_metrics = [
        _ratio_metric(
            "stored_payload_id_and_timestamps_consistent",
            "comparison",
            consistency_rows,
            matched_field_count,
            "Filas con ID y tiempos de raw_payload consistentes con columnas / filas emparejadas * 100",
            "Comparación por event_id entre Feature cacheada, raw_payload y columnas temporales.",
        ),
    ]
    accuracy_metrics = [
        _ratio_metric(
            "payload_retention_proxy",
            "comparison",
            raw_payload_matches,
            len(matched_ids),
            "raw_payload idéntico al Feature cacheado / filas emparejadas * 100",
            "Comparación JSON del Feature de caché con historical_2025.raw_payload.",
            [
                "Mide preservación del payload, no la veracidad científica de sus valores."
            ],
        ),
        _ratio_metric(
            "canonical_column_fidelity_proxy",
            "comparison",
            matching_rows,
            len(matched_ids),
            "Filas cuyas columnas canónicas coinciden con el Feature / filas emparejadas * 100",
            "Comparación de campos Feature→columnas de historical_2025 por event_id.",
            [
                "Mide fidelidad de transformación, no la exactitud instrumental de la ubicación o magnitud."
            ],
        ),
        _not_verifiable(
            "absolute_seismic_accuracy",
            "No existe una referencia independiente de verdad sísmica para esta población.",
            reference_independent=False,
        ),
    ]
    accuracy_metrics[0]["reference_independent"] = False
    accuracy_metrics[0]["proxy"] = True
    accuracy_metrics[1]["reference_independent"] = False
    accuracy_metrics[1]["proxy"] = True

    source_delays, invalid_timestamp_count = _source_delay_values(cache.features)
    currency_metrics = _stat_metrics(
        "source_update_delay",
        "before",
        source_delays,
        "Diferencia entre properties.updated y properties.time del Feature USGS, en milisegundos.",
        [
            "Mide demora entre ocurrencia y última actualización fuente, no el tiempo de respuesta del pipeline."
        ]
        + (
            [f"Se excluyeron {invalid_timestamp_count} Features con timestamps inválidos o no comparables."]
            if invalid_timestamp_count
            else []
        ),
    )

    changed_rows = len(matched_ids) - matching_rows
    transformations = [
        {
            "transformation_id": "cache_partition_deduplication",
            "stage": "agregación de particiones cacheadas antes de la importación",
            "status": "measured",
            "affected_count": cache.duplicate_feature_count,
            "denominator": cache.monthly_feature_count,
            "overlap_policy": "not_applicable",
            "definition": "Features repetidas por event_id entre particiones mensuales idénticas que el importador colapsa.",
            "evidence": ["Conteo de IDs y hashes canónicos de los 12 archivos verificados."],
            "limitations": ["No mide duplicados eliminados por el descargador dentro de cada respuesta antes de guardar."],
        },
        {
            "transformation_id": "source_to_persisted_columns",
            "stage": "Feature cacheada a columnas canónicas de historical_2025",
            "status": "measured",
            "affected_count": changed_rows,
            "denominator": len(matched_ids),
            "overlap_policy": "may_overlap",
            "definition": "Filas emparejadas con al menos un campo canónico distinto del valor derivado del Feature fuente.",
            "evidence": ["Comparación de event_id, mag, mag_type, profundidad, tiempos, place y coordenadas."],
            "limitations": ["Solo se evalúan IDs presentes tanto en caché como en la tabla."],
        },
        {
            "transformation_id": "pre_cache_magnitude_filter",
            "stage": "consulta USGS anterior a la escritura de caché",
            "status": "not_verifiable",
            "affected_count": None,
            "denominator": None,
            "overlap_policy": "not_applicable",
            "definition": "Features excluidos por el filtro de magnitud mínima M≥4 antes de persistir la caché.",
            "evidence": ["El contrato de descarga fija minmagnitude=4.0; no conserva el feed previo al filtro."],
            "limitations": ["No existe la población bruta necesaria para cuantificar excluidos."],
        },
        {
            "transformation_id": "pre_cache_deduplication",
            "stage": "respuesta USGS anterior a la escritura de caché",
            "status": "not_verifiable",
            "affected_count": None,
            "denominator": None,
            "overlap_policy": "not_applicable",
            "definition": "Duplicados descartados por el descargador dentro de respuestas mensuales.",
            "evidence": ["El descargador deduplica por id antes de guardar el GeoJSON."],
            "limitations": ["No se conserva una captura de entrada previa a la deduplicación."],
        },
        {
            "transformation_id": "historical_quarantine",
            "stage": "validación de importación histórica",
            "status": "not_verifiable",
            "affected_count": None,
            "denominator": None,
            "overlap_policy": "not_applicable",
            "definition": "Destino de Features históricos rechazados durante la importación.",
            "evidence": ["El importador histórico valida y detiene la importación; no persiste un ledger completo de cuarentena."],
            "limitations": ["La tabla de cuarentena live no permite inferir disposiciones del histórico."],
        },
    ]

    historical_rows_fingerprint = _sha256(
        _canonical_json(
            [
                {
                    **{key: _json_value(value) for key, value in row.items() if key != "raw_payload"},
                    "raw_payload_sha256": _sha256(
                        _canonical_json(row.get("raw_payload")).encode("utf-8")
                    ),
                }
                for row in sorted(db_by_id.values(), key=lambda item: item["event_id"])
            ]
        ).encode("utf-8")
    )
    imported_count = int(import_record.get("event_count", 0))
    limitations: list[str] = []
    if imported_count != len(rows):
        limitations.append(
            "dataset_imports.event_count no coincide con el número actual de filas históricas."
        )

    population = {
        "population_id": "historical_2025_cache",
        "source": "Caché mensual GeoJSON USGS 2025 verificada y tabla historical_2025",
        "period_start_utc": _iso_utc(YEAR_START),
        "period_end_utc": _iso_utc(YEAR_END),
        "filters": {
            "eventtype": "earthquake",
            "minmagnitude": "4.0",
            "period": "[2025-01-01T00:00:00Z, 2026-01-01T00:00:00Z)",
            "monthly_feature_count": cache.monthly_feature_count,
            "unique_event_count": len(cache.features),
            "cache_manifest": "2025_manifest.json",
            "manifest_generated_at": cache.manifest.get("generated_at"),
            "query": cache.manifest.get("query"),
            "monthly_files_sha256": cache.month_sha256,
            "persisted_snapshot_sha256": historical_rows_fingerprint,
            "dataset_import_event_count": imported_count,
            "dataset_imported_at_utc": _iso_utc(import_record.get("imported_at")),
        },
        "input_count": len(cache.features),
        "after_count": len(matched_ids),
        "input_identity": {
            "kind": "sha256",
            "value": "2025_manifest.json",
            "sha256": cache.manifest_sha256,
        },
        "dispositions": [
            {
                "category": "matched",
                "count": len(matched_ids),
                "definition": "event_id presente en la caché única y en historical_2025.",
            },
            {
                "category": "missing_after",
                "count": len(missing_ids),
                "definition": "event_id de caché sin fila correspondiente en historical_2025.",
            },
            {
                "category": "unmatched_source",
                "count": len(unmatched_ids),
                "definition": "event_id de historical_2025 sin Feature correspondiente en esta caché.",
            },
        ],
        "transformations": transformations,
        "results": [
            {"dimension": "completeness", "metrics": field_metrics},
            {
                "dimension": "uniqueness",
                "metrics": [
                    source_unique_metric,
                    persisted_unique_metric,
                ],
            },
            {"dimension": "validity", "metrics": validity_metrics},
            {"dimension": "consistency", "metrics": consistency_metrics},
            {"dimension": "currency", "metrics": currency_metrics},
            {"dimension": "accuracy", "metrics": accuracy_metrics},
        ],
    }
    if limitations:
        population["limitations"] = limitations
    return population, historical_rows_fingerprint


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _iso_utc(value)
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _audit_rows_fingerprint(rows: list[Mapping[str, Any]]) -> str:
    normalized = [
        {key: _json_value(value) for key, value in _row_dict(row).items()}
        for row in rows
    ]
    return _sha256(_canonical_json(normalized).encode("utf-8"))


def _audit_population(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    audits = [_row_dict(row) for row in rows]
    input_count = len(audits)
    received = sum(int(row.get("records_received", 0)) for row in audits)
    accepted = sum(int(row.get("records_accepted", 0)) for row in audits)
    excluded = sum(int(row.get("records_excluded", 0)) for row in audits)
    valid_balances = sum(
        int(row.get("records_received", 0))
        == int(row.get("records_accepted", 0)) + int(row.get("records_excluded", 0))
        for row in audits
    )
    balances_reconcile = valid_balances == input_count
    valid_ids = sum(isinstance(row.get("poll_id"), str) and bool(row["poll_id"]) for row in audits)
    unique_ids = len({row.get("poll_id") for row in audits})
    delays = []
    for row in audits:
        requested = row.get("requested_at")
        completed = row.get("completed_at")
        if isinstance(requested, datetime) and isinstance(completed, datetime) and completed >= requested:
            delays.append((completed - requested).total_seconds() * 1000)
    evidence = "Filas usgs_live de ingestion_audit; no contiene el payload bruto completo."
    latency_metrics = _stat_metrics(
        "poll_completion_delay",
        "comparison",
        delays,
        "completed_at - requested_at de ingestion_audit, en milisegundos.",
        ["Latencia de consulta USGS registrada; no representa latencia extremo a extremo Kafka/BD."],
    )
    results = [
        {
            "dimension": "completeness",
            "metrics": [
                _ratio_metric(
                    "audit_poll_id_present",
                    "after",
                    valid_ids,
                    input_count,
                    "poll_id no nulo / filas de auditoría * 100",
                    evidence,
                )
            ],
        },
        {
            "dimension": "uniqueness",
            "metrics": [
                _ratio_metric(
                    "unique_audit_poll_ids",
                    "after",
                    unique_ids,
                    input_count,
                    "poll_id distintos / filas de auditoría * 100",
                    evidence,
                )
            ],
        },
        {
            "dimension": "validity",
            "metrics": [
                _ratio_metric(
                    "audit_received_balance",
                    "after",
                    valid_balances,
                    input_count,
                    "polls con records_received = records_accepted + records_excluded / polls * 100",
                    evidence,
                    ["El balance es del poll de origen; no reconcilia descartes ni cuarentena posteriores."],
                )
            ],
        },
        {
            "dimension": "consistency",
            "metrics": [
                _ratio_metric(
                    "audit_counts_consistent",
                    "comparison",
                    valid_balances,
                    input_count,
                    "polls con conteos internamente consistentes / polls * 100",
                    evidence,
                )
            ],
        },
        {"dimension": "currency", "metrics": latency_metrics},
        {
            "dimension": "accuracy",
            "metrics": [
                _not_verifiable(
                    "live_absolute_accuracy",
                    "La auditoría no conserva una referencia independiente ni el feed bruto para comprobar exactitud.",
                    reference_independent=False,
                )
            ],
        },
    ]
    return {
        "population_id": "live_ingestion_audit",
        "source": "Tabla PostgreSQL ingestion_audit limitada a source=usgs_live",
        "filters": {
            "source": "usgs_live",
            "poll_count": input_count,
            "records_received": received,
            "snapshot_scope": "todas las filas usgs_live presentes durante la transacción de lectura",
        },
        "input_count": input_count,
        "after_count": input_count,
        "input_identity": {
            "kind": "sha256",
            "value": "filas de auditoría usgs_live de la instantánea de lectura",
            "sha256": _audit_rows_fingerprint(rows),
        },
        "dispositions": [
            {
                "category": "accepted",
                "count": accepted,
                "definition": "Registros que pasaron el filtro de tipo en los polls USGS; denominador records_received.",
            },
            {
                "category": "excluded",
                "count": excluded,
                "definition": "Registros excluidos por el productor durante esos polls; denominador records_received.",
            },
        ],
        "transformations": [
            {
                "transformation_id": "live_poll_acceptance",
                "stage": "filtrado del poll USGS live",
                "status": "measured",
                "affected_count": accepted,
                "denominator": received,
                "overlap_policy": "mutually_exclusive" if balances_reconcile else "may_overlap",
                "definition": "Suma de records_accepted en polls auditados.",
                "evidence": [evidence],
                "limitations": ["No incluye pérdidas ni cuarentena posteriores al poll."],
            },
            {
                "transformation_id": "live_poll_exclusion",
                "stage": "filtrado del poll USGS live",
                "status": "measured",
                "affected_count": excluded,
                "denominator": received,
                "overlap_policy": "mutually_exclusive" if balances_reconcile else "may_overlap",
                "definition": "Suma de records_excluded en polls auditados.",
                "evidence": [evidence],
                "limitations": ["No incluye pérdidas ni cuarentena posteriores al poll."],
            },
        ],
        "results": results,
    }


def _quarantine_population(
    count: int,
    first_at: datetime | None,
    last_at: datetime | None,
) -> dict[str, Any]:
    identity_data = {
        "count": count,
        "first_at": _iso_utc(first_at),
        "last_at": _iso_utc(last_at),
    }
    fingerprint = _sha256(_canonical_json(identity_data).encode("utf-8"))
    reason = (
        "Solo se consultó el recuento y el intervalo temporal; no se leyeron los payloads ni los motivos."
    )
    return {
        "population_id": "live_quarantine",
        "source": "Tabla PostgreSQL quarantine_events (topic earthquakes.live)",
        "period_start_utc": _iso_utc(first_at),
        "period_end_utc": _iso_utc(last_at),
        "filters": {
            "source_topic": "earthquakes.live",
            "count_scope": "filas presentes en la tabla durante la transacción de lectura",
        },
        "input_count": count,
        "after_count": count,
        "input_identity": {
            "kind": "sha256",
            "value": "recuento e intervalo de quarantine_events",
            "sha256": fingerprint,
        },
        "dispositions": [
            {
                "category": "quarantined",
                "count": count,
                "definition": "Filas observadas en quarantine_events; no se atribuyen a una cohorte de entrada live concreta.",
            }
        ],
        "transformations": [
            {
                "transformation_id": "observed_live_quarantine_rows",
                "stage": "cuarentena del consumidor live",
                "status": "measured",
                "affected_count": count,
                "denominator": count,
                "overlap_policy": "not_applicable",
                "definition": "Recuento de filas directamente observables en quarantine_events.",
                "evidence": ["SELECT count(*), min(quarantined_at), max(quarantined_at) FROM quarantine_events."],
                "limitations": [reason],
            }
        ],
        "results": [
            {
                "dimension": dimension,
                "metrics": [
                    _not_verifiable(
                        f"quarantine_{dimension}",
                        reason,
                        reference_independent=False if dimension == "accuracy" else None,
                    )
                ],
            }
            for dimension in DIMENSIONS
        ],
    }


def _current_state_population(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    records = [_row_dict(row) for row in rows]
    delays: list[float] = []
    invalid_count = 0
    for row in records:
        updated = row.get("updated_utc")
        ingested = row.get("ingested_at")
        if not isinstance(updated, datetime) or not isinstance(ingested, datetime):
            invalid_count += 1
            continue
        delays.append((ingested - updated).total_seconds() * 1000)
    delay_metrics = _stat_metrics(
        "live_update_to_ingestion_delay",
        "comparison",
        delays,
        "Diferencia entre current_earthquakes.ingested_at y updated_utc, en milisegundos.",
        [
            "La tabla contiene únicamente el estado live actual; no conserva cada entrega ni mide latencia Kafka extremo a extremo.",
            "Los valores negativos se conservan y no se recortan.",
        ]
        + (
            [f"Se excluyeron {invalid_count} filas con timestamps no disponibles."]
            if invalid_count
            else []
        ),
    )
    fingerprint = _sha256(
        _canonical_json(
            [
                {key: _json_value(value) for key, value in row.items()}
                for row in records
            ]
        ).encode("utf-8")
    )
    evidence = "Columnas updated_utc e ingested_at de current_earthquakes."
    return {
        "population_id": "live_current_state",
        "source": "Tabla PostgreSQL current_earthquakes (source=usgs_live)",
        "filters": {
            "source": "usgs_live",
            "record_count": len(records),
            "snapshot_scope": "estado actual durante la transacción de lectura",
        },
        "input_count": len(records),
        "after_count": len(records),
        "input_identity": {
            "kind": "sha256",
            "value": "event_id, updated_utc e ingested_at de current_earthquakes",
            "sha256": fingerprint,
        },
        "dispositions": [
            {
                "category": "accepted",
                "count": len(records),
                "definition": "Filas presentes en el estado actual live; no es un recuento de entregas.",
            }
        ],
        "transformations": [
            {
                "transformation_id": "live_current_state_observation",
                "stage": "estado actual de PostgreSQL",
                "status": "measured",
                "affected_count": len(records),
                "denominator": len(records),
                "overlap_policy": "not_applicable",
                "definition": "Número de eventos live retenidos actualmente en current_earthquakes.",
                "evidence": [evidence],
                "limitations": ["El estado UPSERT no conserva versiones anteriores ni todas las entregas."],
            }
        ],
        "results": [
            {
                "dimension": "completeness",
                "metrics": [
                    _ratio_metric(
                        "live_event_id_present",
                        "after",
                        sum(bool(row.get("event_id")) for row in records),
                        len(records),
                        "event_id no nulos / filas current_earthquakes * 100",
                        evidence,
                    )
                ],
            },
            {
                "dimension": "uniqueness",
                "metrics": [
                    _ratio_metric(
                        "live_event_id_unique",
                        "after",
                        len({row.get("event_id") for row in records}),
                        len(records),
                        "event_id distintos / filas current_earthquakes * 100",
                        evidence,
                    )
                ],
            },
            {
                "dimension": "validity",
                "metrics": [
                    _ratio_metric(
                        "live_update_ingestion_timestamps_present",
                        "after",
                        sum(
                            isinstance(row.get("updated_utc"), datetime)
                            and isinstance(row.get("ingested_at"), datetime)
                            for row in records
                        ),
                        len(records),
                        "filas con updated_utc e ingested_at válidos / filas current_earthquakes * 100",
                        evidence,
                    )
                ],
            },
            {
                "dimension": "consistency",
                "metrics": [
                    _not_verifiable(
                        "live_cross_source_consistency",
                        "La tabla de estado no conserva el Feature original de cada evento para una comparación independiente.",
                    )
                ],
            },
            {"dimension": "currency", "metrics": delay_metrics},
            {
                "dimension": "accuracy",
                "metrics": [
                    _not_verifiable(
                        "live_absolute_accuracy",
                        "No existe una referencia independiente de verdad sísmica para el estado live.",
                        reference_independent=False,
                    )
                ],
            },
        ],
    }


def validate_report_structure(report: Mapping[str, Any]) -> None:
    """Reject output that violates the report's core schema invariants."""
    required_report_fields = {
        "schema_version",
        "evaluation_id",
        "generated_at_utc",
        "method_version",
        "rule_set_version",
        "populations",
        "limitations",
    }
    if not required_report_fields <= report.keys():
        missing = sorted(required_report_fields - report.keys())
        raise ReportError(f"report is missing required fields: {', '.join(missing)}")
    populations = report.get("populations")
    if not isinstance(populations, list) or not populations:
        raise ReportError("report must contain at least one population")

    required_metric_fields = {
        "metric_id",
        "stage",
        "numerator",
        "denominator",
        "value",
        "unit",
        "formula",
        "evidence",
        "limitations",
    }
    required_transformation_fields = {
        "transformation_id",
        "stage",
        "status",
        "affected_count",
        "denominator",
        "overlap_policy",
        "definition",
        "evidence",
        "limitations",
    }
    for population in populations:
        results = population.get("results") if isinstance(population, Mapping) else None
        if not isinstance(results, list):
            raise ReportError("each population must contain a results array")
        dimensions = [
            result.get("dimension")
            for result in results
            if isinstance(result, Mapping)
        ]
        if Counter(dimensions) != Counter(DIMENSIONS):
            raise ReportError("each population must contain exactly one result per 6D dimension")

        for result in results:
            metrics = result.get("metrics")
            if not isinstance(metrics, list) or not metrics:
                raise ReportError("each dimension result must contain one or more metrics")
            for metric in metrics:
                if not isinstance(metric, Mapping) or not required_metric_fields <= metric.keys():
                    raise ReportError("each metric must include all required report fields")
                if not isinstance(metric["formula"], str) or not metric["formula"]:
                    raise ReportError("each metric must include a formula")
                if metric["stage"] == "not_verifiable":
                    if any(
                        metric[field] is not None
                        for field in ("numerator", "denominator", "value", "unit")
                    ) or not metric["limitations"]:
                        raise ReportError(
                            "not-verifiable metrics require null values and an explanation"
                        )
                elif metric["stage"] in {"before", "after", "comparison"}:
                    if (
                        isinstance(metric["numerator"], bool)
                        or not isinstance(metric["numerator"], int)
                        or isinstance(metric["denominator"], bool)
                        or not isinstance(metric["denominator"], int)
                        or not isinstance(metric["value"], (int, float))
                        or not math.isfinite(float(metric["value"]))
                        or not isinstance(metric["unit"], str)
                        or not metric["unit"]
                        or not metric["evidence"]
                    ):
                        raise ReportError(
                            "measured metrics require numeric counts, value, unit, and evidence"
                        )
                else:
                    raise ReportError(f"unsupported metric stage: {metric['stage']}")
                if result["dimension"] == "accuracy":
                    if metric.get("reference_independent") is not False:
                        raise ReportError("accuracy metrics must state that no independent reference exists")
                    if not isinstance(metric.get("proxy"), bool):
                        raise ReportError("accuracy metrics must identify whether they are proxies")
                    if metric["stage"] in {"before", "after", "comparison"} and not metric["proxy"]:
                        raise ReportError("measured accuracy comparisons must be labeled as proxies")

        transformations = population.get("transformations")
        if not isinstance(transformations, list) or not transformations:
            raise ReportError("each population must include its transformation inventory")
        for transformation in transformations:
            if (
                not isinstance(transformation, Mapping)
                or not required_transformation_fields <= transformation.keys()
            ):
                raise ReportError("each transformation must include all required report fields")
            if transformation["status"] == "not_verifiable":
                if (
                    transformation["affected_count"] is not None
                    or transformation["denominator"] is not None
                    or not transformation["limitations"]
                ):
                    raise ReportError(
                        "not-verifiable transformations require null counts and an explanation"
                    )
            elif transformation["status"] == "measured":
                if (
                    isinstance(transformation["affected_count"], bool)
                    or not isinstance(transformation["affected_count"], int)
                    or isinstance(transformation["denominator"], bool)
                    or not isinstance(transformation["denominator"], int)
                    or not transformation["evidence"]
                ):
                    raise ReportError(
                        "measured transformations require integer counts and evidence"
                    )
            else:
                raise ReportError(f"unsupported transformation status: {transformation['status']}")


def build_report(
    cache: CacheSnapshot,
    historical_rows: list[Mapping[str, Any]],
    import_record: Mapping[str, Any],
    audit_rows: list[Mapping[str, Any]],
    quarantine_count: int,
    *,
    current_rows: list[Mapping[str, Any]] | None = None,
    quarantine_first_at: datetime | None = None,
    quarantine_last_at: datetime | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or datetime.now(UTC)
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ReportError("generated_at must be timezone-aware")

    historical, historical_fingerprint = _historical_population(
        cache,
        historical_rows,
        import_record,
    )
    populations = [historical]
    if audit_rows:
        populations.append(_audit_population(audit_rows))
    if current_rows:
        populations.append(_current_state_population(current_rows))
    populations.append(
        _quarantine_population(quarantine_count, quarantine_first_at, quarantine_last_at)
    )

    identity = _sha256(
        _canonical_json(
            {
                "method_version": METHOD_VERSION,
                "rule_set_version": RULE_SET_VERSION,
                "manifest_sha256": cache.manifest_sha256,
                "historical_rows_sha256": historical_fingerprint,
                "live_audit_sha256": _audit_rows_fingerprint(audit_rows),
                "quarantine_count": quarantine_count,
                "quarantine_first_at": _iso_utc(quarantine_first_at),
                "quarantine_last_at": _iso_utc(quarantine_last_at),
            }
        ).encode("utf-8")
    )
    report = {
        "schema_version": "1.0",
        "evaluation_id": identity,
        "generated_at_utc": _iso_utc(generated_at),
        "method_version": METHOD_VERSION,
        "rule_set_version": RULE_SET_VERSION,
        "populations": populations,
        "limitations": [
            "La caché USGS ya aplica filtros y deduplicación; no representa el feed bruto.",
            "Las métricas live y la cuarentena se publican en poblaciones separadas y no reconcilian el histórico.",
            "La cuarentena histórica no puede cuantificarse con las tablas de observabilidad disponibles.",
            "Sin referencia independiente, la exactitud sísmica absoluta no es verificable.",
        ],
    }
    validate_report_structure(report)
    return report


async def _generate(cache_dir: Path) -> dict[str, Any]:
    cache = load_cache_snapshot(cache_dir)
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
        async with pool.acquire() as connection:
            snapshot = await read_database_snapshot(connection)
    finally:
        await pool.close()
    return build_report(
        cache,
        snapshot.historical_rows,
        snapshot.import_record,
        snapshot.audit_rows,
        snapshot.quarantine_count,
        current_rows=snapshot.current_rows,
        quarantine_first_at=snapshot.quarantine_first_at,
        quarantine_last_at=snapshot.quarantine_last_at,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    cache_root = Path(os.getenv("USGS_CACHE_DIR", "/var/lib/observatorio/cache"))
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=historical_cache_directory(cache_root),
        help="directory containing the verified 2025 monthly GeoJSON files and manifest",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    try:
        report = asyncio.run(_generate(args.cache_dir))
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2, allow_nan=False)
        sys.stdout.write("\n")
    except (asyncpg.PostgresError, HistoricalDownloadError, OSError, ReportError, ValueError) as exc:
        LOGGER.error("Quality report generation failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
