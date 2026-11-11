from __future__ import annotations

import unittest
from copy import deepcopy
from datetime import datetime, timezone

from scripts.quality_report import (
    CacheSnapshot,
    ReportError,
    build_report,
    snapshot_from_loaded_cache,
    validate_report_structure,
)


UTC = timezone.utc
GENERATED_AT = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)


def _feature(
    event_id: str = "us-test",
    *,
    mag: float | None = 4.5,
    updated_ms: int = 1735689601000,
) -> dict:
    return {
        "type": "Feature",
        "id": event_id,
        "properties": {
            "type": "earthquake",
            "time": 1735689600000,
            "updated": updated_ms,
            "mag": mag,
            "magType": None,
            "place": None,
        },
        "geometry": {"type": "Point", "coordinates": [-70.0, -30.0, -1.5]},
    }


def _row(feature: dict, **overrides) -> dict:
    properties = feature["properties"]
    longitude, latitude, depth = feature["geometry"]["coordinates"]
    row = {
        "event_id": feature["id"],
        "time_utc": datetime.fromtimestamp(properties["time"] / 1000, tz=UTC),
        "updated_utc": datetime.fromtimestamp(properties["updated"] / 1000, tz=UTC),
        "mag": properties["mag"],
        "mag_type": properties["magType"],
        "depth_km": depth,
        "ingested_at": GENERATED_AT,
        "adm0_a3": "N/A",
        "place": properties["place"],
        "geom_lon": longitude,
        "geom_lat": latitude,
        "source": "usgs_2025",
        "raw_payload": feature,
    }
    row.update(overrides)
    return row


def _snapshot(*features: dict) -> CacheSnapshot:
    return CacheSnapshot(
        features=list(features),
        monthly_feature_count=len(features),
        duplicate_feature_count=0,
        manifest={
            "generated_at": "2026-01-01T00:00:00Z",
            "query": {
                "format": "geojson",
                "minmagnitude": "4.0",
                "eventtype": "earthquake",
                "orderby": "time-asc",
            },
            "months": {},
            "unique_event_count": len(features),
        },
        manifest_sha256="a" * 64,
        month_sha256={},
    )


def _report(features: tuple[dict, ...], rows: list[dict] | None = None) -> dict:
    cache = _snapshot(*features)
    persisted = rows if rows is not None else [_row(item) for item in features]
    return build_report(
        cache,
        persisted,
        {"event_count": len(persisted), "imported_at": GENERATED_AT},
        [],
        0,
        generated_at=GENERATED_AT,
    )


class QualityReportTests(unittest.TestCase):
    def test_report_contains_exactly_six_dimensions_and_accuracy_limit(self):
        feature = _feature()
        report = _report((feature,))
        historical = report["populations"][0]
        results = {item["dimension"]: item["metrics"] for item in historical["results"]}

        self.assertEqual(
            set(results),
            {"completeness", "uniqueness", "validity", "consistency", "currency", "accuracy"},
        )
        accuracy = {item["metric_id"]: item for item in results["accuracy"]}
        self.assertFalse(accuracy["absolute_seismic_accuracy"]["reference_independent"])
        self.assertEqual(accuracy["absolute_seismic_accuracy"]["stage"], "not_verifiable")
        self.assertTrue(accuracy["payload_retention_proxy"]["proxy"])
        self.assertFalse(accuracy["payload_retention_proxy"]["reference_independent"])
        self.assertEqual(accuracy["canonical_column_fidelity_proxy"]["value"], 100)
        self.assertTrue(accuracy["canonical_column_fidelity_proxy"]["proxy"])

    def test_optional_null_fields_are_reported_without_rejecting_event(self):
        feature = _feature()
        report = _report((feature,))
        historical = report["populations"][0]
        metrics = {
            metric["metric_id"]: metric
            for result in historical["results"]
            if result["dimension"] == "completeness"
            for metric in result["metrics"]
        }

        self.assertEqual(metrics["source_place_present"]["numerator"], 0)
        self.assertEqual(metrics["source_place_present"]["denominator"], 1)
        validity = next(item for item in historical["results"] if item["dimension"] == "validity")
        self.assertEqual(validity["metrics"][0]["numerator"], 1)
        self.assertEqual(validity["metrics"][1]["numerator"], 1)
        self.assertEqual(_row(feature)["adm0_a3"], "N/A")

    def test_reconciles_matched_missing_and_unmatched_ids(self):
        first = _feature("source-only")
        second = _feature("matched")
        extra = _feature("database-only")
        report = _report((first, second), [_row(second), _row(extra)])
        historical = report["populations"][0]
        dispositions = {item["category"]: item["count"] for item in historical["dispositions"]}

        self.assertEqual(dispositions["matched"], 1)
        self.assertEqual(dispositions["missing_after"], 1)
        self.assertEqual(dispositions["unmatched_source"], 1)
        self.assertEqual(historical["after_count"], 1)

    def test_duplicate_source_ids_are_counted_and_conflicting_ids_rejected(self):
        feature = _feature()
        months = {
            f"2025-{month:02d}": {"features": []}
            for month in range(1, 13)
        }
        months["2025-01"]["features"] = [feature]
        months["2025-02"]["features"] = [feature]
        manifest_months = {
            key: {"sha256": "b" * 64}
            for key in months
        }
        loaded = {
            "manifest": {
                "unique_event_count": 1,
                "months": manifest_months,
            },
            "months": months,
        }
        snapshot = snapshot_from_loaded_cache(loaded, "c" * 64)
        self.assertEqual(snapshot.monthly_feature_count, 2)
        self.assertEqual(snapshot.duplicate_feature_count, 1)
        self.assertEqual(len(snapshot.features), 1)

        conflict = _feature(updated_ms=1735689602000)
        loaded["months"]["2025-02"]["features"] = [conflict]
        with self.assertRaises(ReportError):
            snapshot_from_loaded_cache(loaded, "c" * 64)

    def test_duplicate_database_event_ids_fail_instead_of_overwriting(self):
        feature = _feature()
        with self.assertRaises(ReportError):
            _report((feature,), [_row(feature), _row(feature)])

    def test_transformation_inventory_marks_unobserved_pre_cache_steps(self):
        feature = _feature()
        historical = _report((feature,))["populations"][0]
        transformations = {item["transformation_id"]: item for item in historical["transformations"]}

        self.assertEqual(transformations["cache_partition_deduplication"]["affected_count"], 0)
        self.assertEqual(transformations["pre_cache_magnitude_filter"]["status"], "not_verifiable")
        self.assertIsNone(transformations["pre_cache_magnitude_filter"]["denominator"])
        self.assertEqual(
            transformations["pre_cache_magnitude_filter"]["overlap_policy"],
            "not_applicable",
        )

    def test_missing_or_invalid_timestamps_produce_explicit_non_verifiable_metrics(self):
        feature = _feature(updated_ms="invalid")
        report = _report((feature,), [])
        metrics = next(
            item["metrics"]
            for item in report["populations"][0]["results"]
            if item["dimension"] == "currency"
        )
        source_delay = next(item for item in metrics if item["metric_id"] == "source_update_delay_p90")

        self.assertEqual(source_delay["stage"], "not_verifiable")
        self.assertIsNone(source_delay["value"])
        self.assertTrue(source_delay["limitations"])

    def test_audit_and_quarantine_populations_remain_separate(self):
        feature = _feature()
        audit = {
            "poll_id": "poll-1",
            "source": "usgs_live",
            "requested_at": GENERATED_AT,
            "completed_at": GENERATED_AT,
            "records_received": 3,
            "records_accepted": 2,
            "records_excluded": 1,
        }
        report = build_report(
            _snapshot(feature),
            [_row(feature)],
            {"event_count": 1, "imported_at": GENERATED_AT},
            [audit],
            4,
            generated_at=GENERATED_AT,
        )

        populations = {item["population_id"]: item for item in report["populations"]}
        self.assertEqual(
            set(populations),
            {"historical_2025_cache", "live_ingestion_audit", "live_quarantine"},
        )
        self.assertEqual(populations["live_ingestion_audit"]["input_count"], 1)
        self.assertEqual(populations["live_quarantine"]["input_count"], 4)
        audit_transformations = {
            item["transformation_id"]: item
            for item in populations["live_ingestion_audit"]["transformations"]
        }
        self.assertEqual(
            audit_transformations["live_poll_acceptance"]["overlap_policy"],
            "mutually_exclusive",
        )
        self.assertEqual(
            audit_transformations["live_poll_exclusion"]["affected_count"],
            1,
        )
        self.assertEqual(
            populations["historical_2025_cache"]["transformations"][1]["overlap_policy"],
            "may_overlap",
        )
        self.assertNotEqual(
            populations["historical_2025_cache"]["input_identity"],
            populations["live_ingestion_audit"]["input_identity"],
        )
        self.assertEqual(len(populations["live_quarantine"]["results"]), 6)
        self.assertEqual(populations["live_quarantine"]["input_count"], 4)

    def test_zero_quarantine_count_is_explicit_and_never_merged_with_audit(self):
        feature = _feature()
        report = build_report(
            _snapshot(feature),
            [_row(feature)],
            {"event_count": 1, "imported_at": GENERATED_AT},
            [],
            0,
            generated_at=GENERATED_AT,
        )
        quarantine = report["populations"][1]

        self.assertEqual(quarantine["population_id"], "live_quarantine")
        self.assertEqual(quarantine["input_count"], 0)
        self.assertEqual(quarantine["transformations"][0]["affected_count"], 0)
        self.assertEqual(quarantine["transformations"][0]["denominator"], 0)

    def test_deterministic_evaluation_id_and_measured_metric_shape(self):
        feature = _feature()
        first = _report((feature,))
        second = _report((feature,))

        self.assertEqual(first["evaluation_id"], second["evaluation_id"])
        for population in first["populations"]:
            self.assertEqual(
                {item["dimension"] for item in population["results"]},
                {
                    "completeness",
                    "uniqueness",
                    "validity",
                    "consistency",
                    "currency",
                    "accuracy",
                },
            )
            for result in population["results"]:
                for metric in result["metrics"]:
                    self.assertTrue(metric["formula"])
                    if metric["stage"] == "not_verifiable":
                        self.assertTrue(metric["limitations"])
                        self.assertIsNone(metric["value"])
                    else:
                        self.assertIsInstance(metric["numerator"], int)
                        self.assertIsInstance(metric["denominator"], int)
                        self.assertTrue(metric["evidence"])

    def test_contract_guard_rejects_missing_or_duplicate_dimensions(self):
        report = _report((_feature(),))
        missing = deepcopy(report)
        missing["populations"][0]["results"].pop()
        with self.assertRaises(ReportError):
            validate_report_structure(missing)

        duplicate = deepcopy(report)
        duplicate["populations"][0]["results"][-1]["dimension"] = "completeness"
        with self.assertRaises(ReportError):
            validate_report_structure(duplicate)

    def test_contract_guard_rejects_measured_metrics_without_required_fields(self):
        report = _report((_feature(),))
        measured = report["populations"][0]["results"][0]["metrics"][0]
        measured.pop("formula")

        with self.assertRaises(ReportError):
            validate_report_structure(report)


if __name__ == "__main__":
    unittest.main()
