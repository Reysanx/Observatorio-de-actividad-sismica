"""Tests for the reproducible spatial benchmark input and batching."""

from __future__ import annotations

import json

import pytest

from scripts.benchmark_spatial import _load_source, run_benchmark


def _write_geojson(path, features):
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}),
        encoding="utf-8",
    )


def _make_cache(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "2025_manifest.json").write_text("{}", encoding="utf-8")
    feature = {
        "type": "Feature",
        "id": "test-event",
        "properties": {},
        "geometry": {"type": "Point", "coordinates": [0.0, 0.0, 1.0]},
    }
    for month in range(1, 13):
        _write_geojson(cache / f"2025_m{month:02}.geojson", [feature])
    return cache


def _make_countries(path):
    feature = {
        "type": "Feature",
        "properties": {"ADM0_A3": "TST", "ADMIN": "Test", "NAME_ES": "Prueba"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]]],
        },
    }
    _write_geojson(path, [feature])


def test_load_source_requires_all_twelve_months(tmp_path):
    cache = _make_cache(tmp_path)
    (cache / "2025_m12.geojson").unlink()

    with pytest.raises(ValueError, match="expected 12 monthly"):
        _load_source(cache)


def test_run_benchmark_marks_reused_source_and_reports_measurements(tmp_path):
    cache = _make_cache(tmp_path)
    countries = tmp_path / "countries.geojson"
    _make_countries(countries)

    report = run_benchmark(cache, countries, sizes=(2,), repetitions=1)

    assert report["input"]["source_feature_count"] == 12
    assert report["input"]["source_unique_event_ids"] == 1
    assert report["batches"][0]["source_events_reused"] == 0
    assert report["batches"][0]["warmup_lookups_before_repetitions"] == 12
    assert report["batches"][0]["wall_median_seconds"] >= 0
    assert report["batches"][0]["tracemalloc_peak_median_bytes"] >= 0
