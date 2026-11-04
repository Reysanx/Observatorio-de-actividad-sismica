from __future__ import annotations

import json
import unittest
from datetime import timezone

from consumer.quality import (
    QualityError,
    decode_message,
    validate_event,
    validate_poll_audit,
)


def event_record(**overrides):
    properties = {
        "type": "earthquake",
        "mag": 4.2,
        "magType": "mww",
        "time": 1762128000000,
        "updated": 1762128005000,
        "place": "Chile",
    }
    payload = {
        "type": "Feature",
        "id": "test-event-1",
        "properties": properties,
        "geometry": {"type": "Point", "coordinates": [-70.0, -30.0, 12.0]},
    }
    record = {
        "schema_version": 1,
        "record_type": "event",
        "source": "usgs_live",
        "ingested_at": "2026-11-02T17:00:00Z",
        "mode": "live",
        "event_id": "test-event-1",
        "updated_ms": 1762128005000,
        "content_hash": "sha256:" + ("a" * 64),
        "run_id": None,
        "payload": payload,
    }
    record.update(overrides)
    return record


class ConsumerQualityTests(unittest.TestCase):
    def test_valid_event_preserves_null_magnitude_and_negative_measurements(self):
        record = event_record()
        record["payload"]["properties"]["mag"] = None
        record["payload"]["geometry"]["coordinates"][2] = -1.5

        validated = validate_event(record, topic="earthquakes.live")

        self.assertIsNone(validated.mag)
        self.assertEqual(validated.depth_km, -1.5)
        self.assertEqual(validated.geom_lon, -70.0)
        self.assertEqual(validated.time_utc.tzinfo, timezone.utc)

    def test_valid_negative_magnitude_is_not_rejected(self):
        record = event_record()
        record["payload"]["properties"]["mag"] = -0.5

        validated = validate_event(record, topic="earthquakes.live")

        self.assertEqual(validated.mag, -0.5)

    def test_out_of_bounds_coordinates_have_explicit_reason(self):
        record = event_record()
        record["payload"]["geometry"]["coordinates"][1] = 95.0

        with self.assertRaises(QualityError) as raised:
            validate_event(record, topic="earthquakes.live")

        self.assertEqual(raised.exception.reason, "INVALID_COORDINATES_OUT_OF_BOUNDS")

    def test_non_finite_coordinates_are_quarantinable(self):
        record = event_record()
        record["payload"]["geometry"]["coordinates"][0] = "NaN"

        with self.assertRaises(QualityError) as raised:
            validate_event(record, topic="earthquakes.live")

        self.assertEqual(raised.exception.reason, "NON_FINITE_COORDINATES")

    def test_missing_identifier_is_rejected(self):
        record = event_record()
        record["payload"].pop("id")

        with self.assertRaises(QualityError) as raised:
            validate_event(record, topic="earthquakes.live")

        self.assertEqual(raised.exception.reason, "MISSING_MANDATORY_IDENTIFIER")

    def test_envelope_and_feature_updated_timestamp_must_match(self):
        record = event_record(updated_ms=1762128006000)

        with self.assertRaises(QualityError) as raised:
            validate_event(record, topic="earthquakes.live")

        self.assertEqual(raised.exception.reason, "INCONSISTENT_UPDATED_TIMESTAMP")

    def test_corrupt_json_is_classified_for_quarantine(self):
        with self.assertRaises(QualityError) as raised:
            decode_message(b"\xff{not-json")

        self.assertEqual(raised.exception.reason, "CORRUPT_JSON_SYNTAX")

    def test_poll_audit_maps_failed_fetch_to_failed_status(self):
        audit = {
            "schema_version": 1,
            "record_type": "poll_audit",
            "poll_id": "poll-1",
            "source": "usgs_live",
            "requested_at": "2026-11-02T17:00:00Z",
            "completed_at": "2026-11-02T17:00:01Z",
            "http_status": None,
            "content_hash": None,
            "records_received": 0,
            "records_accepted": 0,
            "records_excluded": 0,
            "error_code": "request_timeout",
            "error_message": "request_timeout",
        }

        validated = validate_poll_audit(audit, topic="earthquakes.live")

        self.assertEqual(validated.status, "failed")
        self.assertEqual(validated.error_code, "request_timeout")

    def test_event_on_unexpected_topic_is_rejected(self):
        with self.assertRaises(QualityError) as raised:
            validate_event(event_record(), topic="earthquakes.replay")

        self.assertEqual(raised.exception.reason, "TOPIC_MODE_MISMATCH")

    def test_valid_json_non_object_is_preserved_in_error(self):
        value = decode_message(json.dumps(["raw", 1]).encode())
        with self.assertRaises(QualityError):
            validate_event(value, topic="earthquakes.live")


if __name__ == "__main__":
    unittest.main()
