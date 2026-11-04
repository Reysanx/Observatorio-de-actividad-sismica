from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiokafka.structs import OffsetAndMetadata, TopicPartition

from consumer.main import process_and_commit, process_message
from consumer.quality import QualityError, validate_event, validate_replay_control
from test_consumer_quality import event_record


def replay_event_record(run_id: str = "replay-test-1") -> dict:
    record = event_record()
    record.update(
        source="usgs_replay",
        mode="replay",
        run_id=run_id,
    )
    return record


class ReplayQualityTests(unittest.TestCase):
    def test_replay_event_requires_replay_topic_and_run_id(self):
        record = replay_event_record()

        validated = validate_event(record, topic="earthquakes.replay")

        self.assertEqual(validated.mode, "replay")
        self.assertEqual(validated.source, "usgs_replay")
        self.assertEqual(validated.run_id, "replay-test-1")

    def test_replay_event_without_run_id_is_rejected(self):
        record = replay_event_record()
        record["run_id"] = None

        with self.assertRaises(QualityError) as raised:
            validate_event(record, topic="earthquakes.replay")

        self.assertEqual(raised.exception.reason, "TOPIC_MODE_MISMATCH")

    def test_live_event_cannot_carry_replay_mode_or_run_id(self):
        record = replay_event_record()

        with self.assertRaises(QualityError) as raised:
            validate_event(record, topic="earthquakes.live")

        self.assertEqual(raised.exception.reason, "TOPIC_MODE_MISMATCH")

    def test_replay_start_and_finish_controls_are_validated(self):
        started = validate_replay_control(
            {
                "schema_version": 1,
                "record_type": "replay_started",
                "source": "usgs_replay",
                "run_id": "replay-test-1",
                "started_at": "2026-11-02T18:00:00Z",
            },
            topic="earthquakes.replay",
        )
        finished = validate_replay_control(
            {
                "schema_version": 1,
                "record_type": "replay_finished",
                "source": "usgs_replay",
                "run_id": "replay-test-1",
                "finished_at": "2026-11-02T18:01:00Z",
                "status": "completed",
            },
            topic="earthquakes.replay",
        )

        self.assertEqual(started.record_type, "replay_started")
        self.assertEqual(finished.status, "completed")


class ReplayConsumerPipelineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.pool = object()
        self.spatial_index = SimpleNamespace(
            find_country=unittest.mock.Mock(return_value=object())
        )
        self.message = SimpleNamespace(
            topic="earthquakes.replay",
            partition=0,
            offset=7,
            value=json.dumps(replay_event_record()).encode(),
        )

    async def test_event_uses_run_scoped_writer(self):
        with patch(
            "consumer.main.persist_replay_event",
            new_callable=AsyncMock,
            return_value=True,
        ) as writer, patch(
            "consumer.main.persist_live_event",
            new_callable=AsyncMock,
        ) as live_writer:
            result = await process_message(
                self.message,
                pool=self.pool,
                spatial_index=self.spatial_index,
            )

        self.assertEqual(result, "event")
        writer.assert_awaited_once()
        live_writer.assert_not_awaited()

    async def test_event_for_inactive_run_is_quarantined_in_replay_table(self):
        with patch(
            "consumer.main.persist_replay_event",
            new_callable=AsyncMock,
            return_value=False,
        ), patch(
            "consumer.main.persist_replay_quarantine",
            new_callable=AsyncMock,
        ) as quarantine:
            result = await process_message(
                self.message,
                pool=self.pool,
                spatial_index=self.spatial_index,
            )

        self.assertEqual(result, "quarantined")
        quarantine.assert_awaited_once()
        self.assertEqual(
            quarantine.await_args.kwargs["failure_reason"],
            "REPLAY_RUN_NOT_ACTIVE",
        )
        self.assertTrue(quarantine.await_args.kwargs["count_as_event"])

    async def test_bad_replay_record_never_uses_live_quarantine(self):
        invalid = replay_event_record()
        invalid["payload"]["geometry"]["coordinates"][1] = 95
        self.message.value = json.dumps(invalid).encode()
        with patch(
            "consumer.main.persist_replay_quarantine",
            new_callable=AsyncMock,
        ) as replay_quarantine, patch(
            "consumer.main.persist_quarantine",
            new_callable=AsyncMock,
        ) as live_quarantine:
            result = await process_message(
                self.message,
                pool=self.pool,
                spatial_index=self.spatial_index,
            )

        self.assertEqual(result, "quarantined")
        replay_quarantine.assert_awaited_once()
        live_quarantine.assert_not_awaited()

    async def test_offset_commit_follows_replay_database_write(self):
        consumer = SimpleNamespace(commit=AsyncMock())
        with patch(
            "consumer.main.persist_replay_event",
            new_callable=AsyncMock,
        ) as writer:
            async def commit_assertion(offsets):
                writer.assert_awaited_once()
                self.assertEqual(
                    offsets,
                    {
                        TopicPartition("earthquakes.replay", 0):
                        OffsetAndMetadata(8, "")
                    },
                )

            consumer.commit.side_effect = commit_assertion
            result = await process_and_commit(
                consumer,
                self.message,
                pool=self.pool,
                spatial_index=self.spatial_index,
            )

        self.assertEqual(result, "event")
        consumer.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
