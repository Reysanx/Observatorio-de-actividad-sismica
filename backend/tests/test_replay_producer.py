from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from scripts.replay_producer import (
    build_replay_event_records,
    publish_replay_run,
)


def historical_feature(event_id: str = "us-test-1") -> dict:
    return {
        "type": "Feature",
        "id": event_id,
        "properties": {
            "type": "earthquake",
            "mag": 4.2,
            "magType": "mww",
            "time": 1750000000000,
            "updated": 1750000005000,
            "place": "USGS catalog fixture",
        },
        "geometry": {"type": "Point", "coordinates": [-70.0, -30.0, 12.0]},
    }


class ReplayProducerTests(unittest.TestCase):
    def test_demo_cases_are_run_scoped_and_include_duplicate_revision_and_ocean(self):
        records = build_replay_event_records(
            [historical_feature()],
            run_id="replay-test-1",
            ingested_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
        )

        self.assertEqual(len(records), 4)
        self.assertTrue(all(record["mode"] == "replay" for record in records))
        self.assertTrue(all(record["run_id"] == "replay-test-1" for record in records))
        first, duplicate, revision, ocean = records
        self.assertEqual(first["event_id"], duplicate["event_id"])
        self.assertEqual(first["updated_ms"], duplicate["updated_ms"])
        self.assertGreater(revision["updated_ms"], first["updated_ms"])
        self.assertEqual(revision["event_id"], first["event_id"])
        self.assertTrue(ocean["event_id"].startswith("replay-ocean-"))
        self.assertEqual(ocean["payload"]["geometry"]["coordinates"][:2], [-30.0, 0.0])

    def test_replay_sequence_can_omit_synthetic_demo_records(self):
        records = build_replay_event_records(
            [historical_feature()],
            run_id="replay-test-1",
            ingested_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
            include_demo_cases=False,
        )

        self.assertEqual([record["event_id"] for record in records], ["us-test-1"])
        self.assertEqual(records[0]["source"], "usgs_replay")


class ReplayPublisherTests(unittest.IsolatedAsyncioTestCase):
    async def test_publish_sends_start_events_and_finish_to_isolated_topic(self):
        producer = type("FakeProducer", (), {"send_and_wait": AsyncMock()})()
        timestamp = datetime(2026, 11, 2, 18, 0, tzinfo=timezone.utc)
        with patch(
            "scripts.replay_producer.load_replay_features",
            return_value=[historical_feature()],
        ), patch(
            "scripts.replay_producer.utc_now",
            return_value=timestamp,
        ):
            result = await publish_replay_run(
                producer,
                cache_dir="unused",
                run_id="replay-test-1",
                speed=120,
                include_demo_cases=True,
                max_delay_seconds=0,
                sleep=AsyncMock(),
            )

        self.assertEqual(result.events_published, 4)
        sends = producer.send_and_wait.await_args_list
        self.assertEqual(len(sends), 6)
        self.assertTrue(all(call.args[0] == "earthquakes.replay" for call in sends))
        self.assertEqual(sends[0].kwargs["key"], b"__run__:replay-test-1")
        self.assertEqual(
            json.loads(sends[0].kwargs["value"])["record_type"],
            "replay_started",
        )
        self.assertEqual(sends[-1].kwargs["key"], b"__run__:replay-test-1")
        self.assertEqual(
            json.loads(sends[-1].kwargs["value"])["record_type"],
            "replay_finished",
        )

    async def test_publish_failure_emits_safe_failed_control(self):
        producer = type("FakeProducer", (), {"send_and_wait": AsyncMock()})()
        producer.send_and_wait.side_effect = [
            None,
            RuntimeError("secret-bearing broker detail"),
            None,
        ]
        timestamp = datetime(2026, 11, 2, 18, 0, tzinfo=timezone.utc)
        with patch(
            "scripts.replay_producer.load_replay_features",
            return_value=[historical_feature()],
        ), patch(
            "scripts.replay_producer.utc_now",
            return_value=timestamp,
        ):
            with self.assertRaisesRegex(RuntimeError, "secret-bearing"):
                await publish_replay_run(
                    producer,
                    cache_dir="unused",
                    run_id="replay-failed-test",
                    include_demo_cases=False,
                    max_delay_seconds=0,
                    sleep=AsyncMock(),
                )

        self.assertEqual(producer.send_and_wait.await_count, 3)
        failure_control = json.loads(
            producer.send_and_wait.await_args_list[-1].kwargs["value"]
        )
        self.assertEqual(failure_control["status"], "failed")
        self.assertEqual(
            failure_control["error_message"],
            "publisher failed: RuntimeError",
        )


if __name__ == "__main__":
    unittest.main()
