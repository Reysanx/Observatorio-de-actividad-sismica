from __future__ import annotations

import os
import unittest
import uuid
from pathlib import Path

import asyncpg

from consumer.db_writer import (
    load_country_dimension,
    persist_live_event,
    persist_quarantine,
    persist_replay_event,
    persist_replay_finished,
    persist_replay_quarantine,
    persist_replay_started,
)
from consumer.quality import validate_event, validate_replay_control
from consumer.spatial import SpatialIndex
from test_consumer_quality import event_record

RUN_DB_INTEGRATION = os.getenv("RUN_DB_INTEGRATION") == "1"


@unittest.skipUnless(RUN_DB_INTEGRATION, "set RUN_DB_INTEGRATION=1 with Compose PostgreSQL ready")
class ConsumerDatabaseIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "almacenamiento"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "observatorio"),
            user=os.getenv("POSTGRES_USER", "observatorio"),
            password=os.environ["POSTGRES_PASSWORD"],
        )
        geojson_path = Path(os.getenv("NATURAL_EARTH_GEOJSON", "/app/data/paises.geojson"))
        self.spatial_index = SpatialIndex.from_geojson(geojson_path)
        await load_country_dimension(self.pool, self.spatial_index.countries)
        self.country = self.spatial_index.find_country(-70.0, -30.0)
        self.event_id = "t12_" + uuid.uuid4().hex[:12]
        self.replay_run_id = "replay_" + uuid.uuid4().hex[:12]
        self.replay_event_id = "rpl_" + uuid.uuid4().hex[:12]

    async def asyncTearDown(self):
        async with self.pool.acquire() as connection:
            await connection.execute(
                "DELETE FROM earthquake_versions WHERE event_id = $1",
                self.event_id,
            )
            await connection.execute(
                "DELETE FROM current_earthquakes WHERE event_id = $1",
                self.event_id,
            )
            await connection.execute(
                "DELETE FROM replay_versions WHERE run_id = $1",
                self.replay_run_id,
            )
            await connection.execute(
                "DELETE FROM replay_earthquakes WHERE run_id = $1",
                self.replay_run_id,
            )
            await connection.execute(
                "DELETE FROM replay_quarantine_events WHERE run_id = $1",
                self.replay_run_id,
            )
            await connection.execute(
                "DELETE FROM replay_runs WHERE run_id = $1",
                self.replay_run_id,
            )
        await self.pool.close()

    def _event(self, updated_ms: int, magnitude: float):
        record = event_record()
        record["event_id"] = self.event_id
        record["payload"]["id"] = self.event_id
        record["payload"]["properties"]["updated"] = updated_ms
        record["payload"]["properties"]["mag"] = magnitude
        record["updated_ms"] = updated_ms
        validated = validate_event(record, topic="earthquakes.live")
        return validated

    def _replay_event(self, updated_ms: int, magnitude: float):
        record = event_record()
        record["event_id"] = self.replay_event_id
        record["payload"]["id"] = self.replay_event_id
        record["payload"]["properties"]["updated"] = updated_ms
        record["payload"]["properties"]["mag"] = magnitude
        record["updated_ms"] = updated_ms
        record["source"] = "usgs_replay"
        record["mode"] = "replay"
        record["run_id"] = self.replay_run_id
        return validate_event(record, topic="earthquakes.replay")

    def _start_control(self):
        return validate_replay_control(
            {
                "schema_version": 1,
                "record_type": "replay_started",
                "source": "usgs_replay",
                "run_id": self.replay_run_id,
                "started_at": "2026-11-02T18:00:00Z",
            },
            topic="earthquakes.replay",
        )

    async def test_upsert_is_strictly_newer_and_versions_only_accepted_state(self):
        original_updated = 1762128005000
        self.assertTrue(
            await persist_live_event(
                self.pool,
                self._event(original_updated, 4.2),
                self.country,
            )
        )
        self.assertFalse(
            await persist_live_event(
                self.pool,
                self._event(original_updated, 5.0),
                self.country,
            )
        )
        self.assertFalse(
            await persist_live_event(
                self.pool,
                self._event(original_updated - 1000, 3.0),
                self.country,
            )
        )
        self.assertTrue(
            await persist_live_event(
                self.pool,
                self._event(original_updated + 1000, 4.8),
                self.country,
            )
        )

        async with self.pool.acquire() as connection:
            current = await connection.fetchrow(
                "SELECT mag, updated_utc FROM current_earthquakes WHERE event_id = $1",
                self.event_id,
            )
            versions = await connection.fetchval(
                "SELECT count(*) FROM earthquake_versions WHERE event_id = $1",
                self.event_id,
            )
        self.assertEqual(current["mag"], 4.8)
        self.assertEqual(versions, 2)

    async def test_quarantine_is_idempotent_by_kafka_position(self):
        partition = 700
        offset = int(uuid.uuid4().int % 2_000_000_000)
        args = {
            "source_topic": "earthquakes.live",
            "source_partition": partition,
            "source_offset": offset,
            "raw_message": b"{bad-json",
            "raw_payload": None,
            "source_event_id": None,
            "failure_reason": "CORRUPT_JSON_SYNTAX",
            "failure_detail": "invalid JSON",
        }
        try:
            await persist_quarantine(self.pool, **args)
            await persist_quarantine(self.pool, **args)
            async with self.pool.acquire() as connection:
                count = await connection.fetchval(
                    """
                    SELECT count(*) FROM quarantine_events
                    WHERE source_topic = 'earthquakes.live'
                      AND source_partition = $1 AND source_offset = $2
                    """,
                    partition,
                    offset,
                )
            self.assertEqual(count, 1)
        finally:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    DELETE FROM quarantine_events
                    WHERE source_topic = 'earthquakes.live'
                      AND source_partition = $1 AND source_offset = $2
                    """,
                    partition,
                    offset,
                )

    async def test_null_kafka_tombstone_is_stored_as_json_null(self):
        partition = 700
        offset = int(uuid.uuid4().int % 2_000_000_000)
        await persist_quarantine(
            self.pool,
            source_topic="earthquakes.live",
            source_partition=partition,
            source_offset=offset,
            raw_message=None,
            raw_payload=None,
            source_event_id=None,
            failure_reason="CORRUPT_JSON_SYNTAX",
            failure_detail="Kafka tombstone has no payload bytes",
        )
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(
                    """
                    SELECT raw_payload IS NOT NULL AS has_json,
                           raw_message IS NULL AS has_no_message
                    FROM quarantine_events
                    WHERE source_topic = 'earthquakes.live'
                      AND source_partition = $1 AND source_offset = $2
                    """,
                    partition,
                    offset,
                )
            self.assertTrue(row["has_json"])
            self.assertTrue(row["has_no_message"])
        finally:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    DELETE FROM quarantine_events
                    WHERE source_topic = 'earthquakes.live'
                      AND source_partition = $1 AND source_offset = $2
                    """,
                    partition,
                    offset,
                )

    async def test_replay_is_run_scoped_idempotent_and_versions_only_newer_state(self):
        await persist_replay_started(self.pool, self._start_control())
        original_updated = 1762128005000

        self.assertTrue(
            await persist_replay_event(
                self.pool,
                self._replay_event(original_updated, 4.2),
                self.country,
            )
        )
        self.assertTrue(
            await persist_replay_event(
                self.pool,
                self._replay_event(original_updated, 5.0),
                self.country,
            )
        )
        self.assertTrue(
            await persist_replay_event(
                self.pool,
                self._replay_event(original_updated - 1000, 3.0),
                self.country,
            )
        )
        self.assertTrue(
            await persist_replay_event(
                self.pool,
                self._replay_event(original_updated + 1000, 4.8),
                self.country,
            )
        )

        async with self.pool.acquire() as connection:
            replay = await connection.fetchrow(
                """
                SELECT mag FROM replay_earthquakes
                WHERE run_id = $1 AND event_id = $2
                """,
                self.replay_run_id,
                self.replay_event_id,
            )
            versions = await connection.fetchval(
                "SELECT count(*) FROM replay_versions WHERE run_id = $1 AND event_id = $2",
                self.replay_run_id,
                self.replay_event_id,
            )
            counts = await connection.fetchrow(
                "SELECT events_received, events_processed FROM replay_runs WHERE run_id = $1",
                self.replay_run_id,
            )
            live_count = await connection.fetchval(
                "SELECT count(*) FROM current_earthquakes WHERE event_id = $1",
                self.replay_event_id,
            )
        self.assertEqual(replay["mag"], 4.8)
        self.assertEqual(versions, 2)
        self.assertEqual(counts["events_received"], 4)
        self.assertEqual(counts["events_processed"], 4)
        self.assertEqual(live_count, 0)

        finished = validate_replay_control(
            {
                "schema_version": 1,
                "record_type": "replay_finished",
                "source": "usgs_replay",
                "run_id": self.replay_run_id,
                "finished_at": "2026-11-02T18:01:00Z",
                "status": "completed",
            },
            topic="earthquakes.replay",
        )
        self.assertTrue(await persist_replay_finished(self.pool, finished))
        self.assertFalse(
            await persist_replay_event(
                self.pool,
                self._replay_event(original_updated + 2000, 4.9),
                self.country,
            )
        )

    async def test_replay_quarantine_is_offset_idempotent_and_separate_from_live(self):
        await persist_replay_started(self.pool, self._start_control())
        partition = 700
        offset = int(uuid.uuid4().int % 2_000_000_000)
        args = {
            "source_partition": partition,
            "source_offset": offset,
            "raw_message": b'{"bad":"event"}',
            "raw_payload": {"bad": "event"},
            "run_id": self.replay_run_id,
            "source_event_id": self.replay_event_id,
            "failure_reason": "INVALID_EVENT_SCHEMA",
            "failure_detail": "invalid replay event",
            "count_as_event": True,
        }
        try:
            await persist_replay_quarantine(self.pool, **args)
            await persist_replay_quarantine(self.pool, **args)
            async with self.pool.acquire() as connection:
                replay_count = await connection.fetchval(
                    """
                    SELECT count(*) FROM replay_quarantine_events
                    WHERE source_topic = 'earthquakes.replay'
                      AND source_partition = $1 AND source_offset = $2
                    """,
                    partition,
                    offset,
                )
                live_count = await connection.fetchval(
                    "SELECT count(*) FROM quarantine_events WHERE source_event_id = $1",
                    self.replay_event_id,
                )
                counters = await connection.fetchrow(
                    """
                    SELECT events_received, events_quarantined
                    FROM replay_runs WHERE run_id = $1
                    """,
                    self.replay_run_id,
                )
            self.assertEqual(replay_count, 1)
            self.assertEqual(live_count, 0)
            self.assertEqual(counters["events_received"], 1)
            self.assertEqual(counters["events_quarantined"], 1)
        finally:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    DELETE FROM replay_quarantine_events
                    WHERE source_topic = 'earthquakes.replay'
                      AND source_partition = $1 AND source_offset = $2
                    """,
                    partition,
                    offset,
                )


if __name__ == "__main__":
    unittest.main()
