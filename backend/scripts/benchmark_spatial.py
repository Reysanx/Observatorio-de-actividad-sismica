"""Reproduce spatial lookup benchmarks from the cached USGS 2025 features."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely import __version__ as shapely_version

from consumer.spatial import SpatialIndex, UNASSIGNED

DEFAULT_SIZES = (500, 10_000, 100_000)


def _load_source(input_dir: Path) -> tuple[list[tuple[float, float]], dict[str, Any]]:
    manifest_path = input_dir / "2025_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"historical cache manifest not found: {manifest_path}")
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid historical cache manifest: {manifest_path}") from exc

    files = sorted(input_dir.glob("2025_m??.geojson"))
    if len(files) != 12:
        raise ValueError(f"expected 12 monthly GeoJSON files in {input_dir}, found {len(files)}")

    source_hash = hashlib.sha256()
    source_hash.update(manifest_bytes)
    coordinates: list[tuple[float, float]] = []
    event_ids: set[str] = set()
    monthly_counts: dict[str, int] = {}
    for path in files:
        content = path.read_bytes()
        source_hash.update(path.name.encode("utf-8"))
        source_hash.update(content)
        try:
            collection = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid monthly GeoJSON: {path}") from exc
        if not isinstance(collection, dict) or collection.get("type") != "FeatureCollection":
            raise ValueError(f"monthly source must be a GeoJSON FeatureCollection: {path}")
        features = collection.get("features")
        if not isinstance(features, list):
            raise ValueError(f"monthly source has no feature list: {path}")
        monthly_counts[path.name] = len(features)
        for position, feature in enumerate(features):
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise ValueError(f"invalid feature {position} in {path}")
            event_id = feature.get("id")
            geometry = feature.get("geometry")
            point = geometry.get("coordinates") if isinstance(geometry, dict) else None
            if (
                not isinstance(event_id, str)
                or not event_id
                or not isinstance(point, list)
                or len(point) < 2
            ):
                raise ValueError(f"feature {position} in {path} lacks ID or point coordinates")
            longitude, latitude = point[0], point[1]
            if (
                isinstance(longitude, bool)
                or isinstance(latitude, bool)
                or not isinstance(longitude, (int, float))
                or not isinstance(latitude, (int, float))
                or not math.isfinite(longitude)
                or not math.isfinite(latitude)
            ):
                raise ValueError(f"feature {event_id} in {path} has non-finite coordinates")
            coordinates.append((float(longitude), float(latitude)))
            event_ids.add(event_id)

    if not coordinates:
        raise ValueError(f"historical cache contains no event coordinates: {input_dir}")
    return coordinates, {
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "cache_sha256": source_hash.hexdigest(),
        "monthly_feature_counts": monthly_counts,
        "source_feature_count": len(coordinates),
        "source_unique_event_ids": len(event_ids),
        "monthly_files": [path.name for path in files],
    }


def _measure_batch(
    index: SpatialIndex,
    coordinates: list[tuple[float, float]],
    event_count: int,
    repetitions: int,
) -> dict[str, Any]:
    warmup_count = min(max(1_000, event_count), len(coordinates))
    for position in range(warmup_count):
        longitude, latitude = coordinates[position]
        index.find_country(longitude, latitude)

    wall_seconds: list[float] = []
    cpu_seconds: list[float] = []
    peak_python_bytes: list[int] = []
    unassigned_counts: list[int] = []
    for _ in range(repetitions):
        unassigned = 0
        tracemalloc.start()
        cpu_start = time.process_time()
        wall_start = time.perf_counter()
        for position in range(event_count):
            longitude, latitude = coordinates[position % len(coordinates)]
            if index.find_country(longitude, latitude).adm0_a3 == UNASSIGNED:
                unassigned += 1
        wall_seconds.append(time.perf_counter() - wall_start)
        cpu_seconds.append(time.process_time() - cpu_start)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_python_bytes.append(peak)
        unassigned_counts.append(unassigned)

    median_wall = statistics.median(wall_seconds)
    return {
        "events_per_run": event_count,
        "source_events_reused": max(0, event_count - len(coordinates)),
        "repetitions": repetitions,
        "warmup_lookups_before_repetitions": warmup_count,
        "wall_seconds": wall_seconds,
        "wall_median_seconds": median_wall,
        "process_cpu_seconds": cpu_seconds,
        "process_cpu_median_seconds": statistics.median(cpu_seconds),
        "lookups_per_second_at_median": event_count / median_wall if median_wall else None,
        "tracemalloc_peak_bytes": peak_python_bytes,
        "tracemalloc_peak_median_bytes": int(statistics.median(peak_python_bytes)),
        "unassigned_lookups_per_run": unassigned_counts,
    }


def run_benchmark(
    input_dir: Path,
    countries_path: Path,
    sizes: tuple[int, ...] = DEFAULT_SIZES,
    repetitions: int = 3,
) -> dict[str, Any]:
    if not sizes or any(size <= 0 for size in sizes):
        raise ValueError("all batch sizes must be positive")
    if repetitions < 1:
        raise ValueError("repetitions must be at least one")

    coordinates, source = _load_source(input_dir)
    tracemalloc.start()
    index_wall_start = time.perf_counter()
    index = SpatialIndex.from_geojson(countries_path)
    index_wall_seconds = time.perf_counter() - index_wall_start
    _, index_peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "benchmark": "historical_feature_point_in_polygon",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "Cached historical feature coordinates passed through the production "
            "SpatialIndex.find_country implementation; no Kafka or database writes."
        ),
        "input": {
            **source,
            "countries_catalog": countries_path.name,
            "countries_catalog_sha256": hashlib.sha256(countries_path.read_bytes()).hexdigest(),
            "countries_indexed": len(index.countries),
            "source_unique_coordinates": len(coordinates),
            "larger_batches_reuse_source_coordinates": True,
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "shapely": shapely_version,
            "memory_metric": "tracemalloc peak Python allocations, not process RSS",
        },
        "catalog_load_and_index_build": {
            "wall_seconds": index_wall_seconds,
            "tracemalloc_peak_bytes": index_peak_bytes,
        },
        "limitations": [
            "The 100,000-lookup batch cycles through observed cached coordinates if the source has fewer events; it is not 100,000 distinct earthquakes.",
            "tracemalloc excludes GEOS native allocations, process RSS, imported modules, and already-loaded source coordinates.",
            "Measurements cover in-process spatial lookup only; Kafka, PostgreSQL, network, and API timings are not included.",
            "Results depend on hardware, Python/Shapely versions, operating-system scheduling, and cache state.",
        ],
        "batches": [
            _measure_batch(index, coordinates, size, repetitions) for size in sizes
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("/var/lib/observatorio/cache/historical"),
        help="directory with the 2025 manifest and twelve monthly GeoJSON files",
    )
    parser.add_argument(
        "--countries",
        type=Path,
        default=Path("/app/data/paises.geojson"),
        help="Natural Earth GeoJSON used by the consumer",
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=DEFAULT_SIZES,
        help="lookup batch sizes (default: 500 10000 100000)",
    )
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    try:
        result = run_benchmark(
            args.input_dir,
            args.countries,
            tuple(args.sizes),
            args.repetitions,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
