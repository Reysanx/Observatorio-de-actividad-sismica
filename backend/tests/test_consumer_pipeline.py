from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiokafka.structs import OffsetAndMetadata, TopicPartition

from consumer.main import process_and_commit, process_message
from consumer.spatial import Country
from test_consumer_quality import event_record


class ConsumerPipelineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.pool = object()
        self.country = Country(
            adm0_a3="CHL",
            name_es="Chile",
            admin_name="Chile",
            display_name="Chile",
            continent="South America",
            subregion="South America",
            source_props={},
        )
        self.spatial_index = SimpleNamespace(
            find_country=unittest.mock.Mock(return_value=self.country)
        )
        self.message = SimpleNamespace(
            topic="earthquakes.live",
            partition=2,
            offset=41,
            value=json.dumps(event_record()).encode(),
        )

    async def test_persists_enriched_event_on_expected_country(self):
        with patch("consumer.main.persist_live_event", new_callable=AsyncMock) as write:
            result = await process_message(
                self.message,
                pool=self.pool,
                spatial_index=self.spatial_index,
            )

        self.assertEqual(result, "event")
        write.assert_awaited_once()
        self.assertEqual(write.await_args.args[2].adm0_a3, "CHL")

    async def test_invalid_event_is_quarantined_with_original_bytes(self):
        record = event_record()
        record["payload"]["geometry"]["coordinates"][1] = 95
        self.message.value = json.dumps(record).encode()
        with patch("consumer.main.persist_quarantine", new_callable=AsyncMock) as quarantine:
            result = await process_message(
                self.message,
                pool=self.pool,
                spatial_index=self.spatial_index,
            )

        self.assertEqual(result, "quarantined")
        quarantine.assert_awaited_once()
        self.assertEqual(quarantine.await_args.kwargs["failure_reason"], "INVALID_COORDINATES_OUT_OF_BOUNDS")
        self.assertEqual(quarantine.await_args.kwargs["raw_message"], self.message.value)

    async def test_offset_is_not_committed_when_database_write_fails(self):
        consumer = SimpleNamespace(commit=AsyncMock())
        with patch(
            "consumer.main.persist_live_event",
            new_callable=AsyncMock,
            side_effect=RuntimeError("database unavailable"),
        ):
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                await process_and_commit(
                    consumer,
                    self.message,
                    pool=self.pool,
                    spatial_index=self.spatial_index,
                )

        consumer.commit.assert_not_awaited()

    async def test_success_commits_only_after_persistence(self):
        consumer = SimpleNamespace(commit=AsyncMock())
        with patch("consumer.main.persist_live_event", new_callable=AsyncMock) as write:
            async def commit_assertion(offsets):
                write.assert_awaited_once()
                self.assertEqual(
                    offsets,
                    {
                        TopicPartition("earthquakes.live", 2): OffsetAndMetadata(42, "")
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

    async def test_quarantine_write_failure_leaves_record_uncommitted(self):
        consumer = SimpleNamespace(commit=AsyncMock())
        record = event_record()
        record["payload"]["geometry"]["coordinates"][1] = 95
        self.message.value = json.dumps(record).encode()
        with patch(
            "consumer.main.persist_quarantine",
            new_callable=AsyncMock,
            side_effect=RuntimeError("database unavailable"),
        ):
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                await process_and_commit(
                    consumer,
                    self.message,
                    pool=self.pool,
                    spatial_index=self.spatial_index,
                )

        consumer.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
