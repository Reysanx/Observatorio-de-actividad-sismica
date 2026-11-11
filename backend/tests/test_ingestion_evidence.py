from datetime import datetime, timezone
import unittest

from scripts.ingestion_evidence import summarize_live_polls


class LivePollSummaryTests(unittest.TestCase):
    def test_summarizes_counts_errors_and_precise_durations(self) -> None:
        start = datetime(2026, 11, 11, 12, 0, 0, 125000, tzinfo=timezone.utc)
        rows = [
            {
                "status": "succeeded",
                "http_status": 200,
                "requested_at": start,
                "completed_at": start.replace(microsecond=625000),
                "records_received": 8,
                "records_accepted": 6,
                "records_excluded": 2,
                "records_quarantined": 0,
                "error_code": None,
                "error_message": None,
            },
            {
                "status": "failed",
                "http_status": None,
                "requested_at": start.replace(second=1, microsecond=0),
                "completed_at": start.replace(second=2, microsecond=0),
                "records_received": 0,
                "records_accepted": 0,
                "records_excluded": 0,
                "records_quarantined": 0,
                "error_code": "request_timeout",
                "error_message": "request_timeout",
            },
        ]

        result = summarize_live_polls(rows)

        self.assertEqual(result["poll_count"], 2)
        self.assertEqual(result["status_counts"]["succeeded"], 1)
        self.assertEqual(result["status_counts"]["failed"], 1)
        self.assertEqual(result["http_status_counts"], {"200": 1, "none": 1})
        self.assertEqual(result["records_received"], 8)
        self.assertEqual(result["records_accepted"], 6)
        self.assertEqual(result["records_excluded"], 2)
        self.assertEqual(result["error_count"], 1)
        self.assertEqual(result["errors_by_code"], {"request_timeout": 1})
        self.assertEqual(result["stored_duration_median_ms"], 750.0)
        self.assertEqual(result["subsecond_precision_poll_count"], 1)
        self.assertEqual(result["subsecond_duration_median_ms"], 500.0)
        self.assertFalse(result["timestamps_have_whole_second_precision"])

    def test_marks_second_precision_as_a_duration_limitation(self) -> None:
        instant = datetime(2026, 11, 11, 12, 0, 0, tzinfo=timezone.utc)
        row = {
            "status": "succeeded",
            "http_status": 200,
            "requested_at": instant,
            "completed_at": instant,
            "records_received": 1,
            "records_accepted": 1,
            "records_excluded": 0,
            "records_quarantined": 0,
            "error_code": None,
            "error_message": None,
        }

        result = summarize_live_polls([row])

        self.assertTrue(result["timestamps_have_whole_second_precision"])
        self.assertEqual(result["stored_duration_median_ms"], 0.0)
        self.assertEqual(result["subsecond_precision_poll_count"], 0)
        self.assertIn("Whole-second rows are quantized", result["duration_note"])

    def test_empty_audit_has_zero_counts_and_null_timings(self) -> None:
        result = summarize_live_polls([])

        self.assertEqual(result["poll_count"], 0)
        self.assertEqual(result["error_count"], 0)
        self.assertIsNone(result["stored_duration_median_ms"])
        self.assertIsNone(result["poll_interval_median_seconds"])


if __name__ == "__main__":
    unittest.main()
