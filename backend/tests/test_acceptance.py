"""Backend acceptance tests against the live Compose Kafka/PostgreSQL services.

Run inside the API container after the five Compose services are healthy:
``docker compose exec api pytest tests/test_acceptance.py -v``.

The tests publish uniquely keyed fixtures to the real runtime topics and wait
for durable database outcomes; they never call USGS or mutate existing events.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
import httpx
from aiokafka import AIOKafkaProducer


LIVE_TOPIC = "earthquakes.live"
REPLAY_TOPIC = "earthquakes.replay"
WAIT_SECONDS = 30


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


class BackendAcceptanceTests(unittest.IsolatedAsyncioTestCase):
    """Exercise accepted, quarantined, revised, and replay events end to end."""

    async def asyncSetUp(self) -> None:
        self.event_id = f"t20_{uuid.uuid4().hex[:16]}"
        self.run_id = f"t20-run-{uuid.uuid4().hex[:12]}"
        self.audit_ids: list[str] = []
        self.quarantine_positions: list[tuple[int, int]] = []

        self.pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "almacenamiento"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "observatorio"),
            user=os.getenv("POSTGRES_USER", "observatorio"),
            password=os.environ["POSTGRES_PASSWORD"],
            min_size=1,
            max_size=2,
            command_timeout=10,
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092"),
            acks="all",
            request_timeout_ms=10000,
        )
        await self.producer.start()
        self.api = httpx.AsyncClient(
            base_url=os.getenv("ACCEPTANCE_API_URL", "http://api:8000"),
            timeout=10,
        )

    async def asyncTearDown(self) -> None:
        if hasattr(self, "api"):
            await self.api.aclose()
        if hasattr(self, "producer"):
            await self.producer.stop()
        if hasattr(self, "pool"):
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    DELETE FROM ingestion_audit
                    WHERE poll_id = ANY($1::text[])
                    """,
                    self.audit_ids,
                )
                for partition, offset in self.quarantine_positions:
                    await connection.execute(
                        """
                        DELETE FROM quarantine_events
                        WHERE source_topic = 'earthquakes.live'
                          AND source_partition = $1 AND source_offset = $2
                        """,
                        partition,
                        offset,
                    )
                await connection.execute(
                    "DELETE FROM quarantine_events WHERE source_event_id = $1",
                    self.event_id,
                )
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
                    self.run_id,
                )
                await connection.execute(
                    "DELETE FROM replay_earthquakes WHERE run_id = $1",
                    self.run_id,
                )
                await connection.execute(
                    "DELETE FROM replay_quarantine_events WHERE run_id = $1",
                    self.run_id,
                )
                await connection.execute(
                    "DELETE FROM replay_runs WHERE run_id = $1",
                    self.run_id,
                )
            await self.pool.close()

    def _event(
        self,
        event_id: str | None = None,
        *,
        magnitude: float | None = 4.2,
        longitude: float = -70.0,
        latitude: float = -30.0,
        updated_ms: int | None = None,
    ) -> dict[str, Any]:
        identifier = event_id or self.event_id
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        occurred_ms = now_ms - 10_000
        revision_ms = updated_ms if updated_ms is not None else now_ms
        payload = {
            "type": "Feature",
            "id": identifier,
            "properties": {
                "type": "earthquake",
                "mag": magnitude,
                "magType": "mww",
                "time": occurred_ms,
                "updated": revision_ms,
                "place": "acceptance fixture; country must come from geometry",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [longitude, latitude, 10.0],
            },
        }
        digest = hashlib.sha256(
            f"{identifier}:{revision_ms}:{magnitude}".encode("utf-8")
        ).hexdigest()
        return {
            "schema_version": 1,
            "record_type": "event",
            "source": "usgs_live",
            "ingested_at": _utc_iso(datetime.now(timezone.utc)),
            "mode": "live",
            "event_id": identifier,
            "updated_ms": revision_ms,
            "content_hash": f"sha256:{digest}",
            "run_id": None,
            "payload": payload,
        }

    async def _send(
        self,
        topic: str,
        record: dict[str, Any],
        *,
        key: str | None = None,
    ) -> Any:
        return await self.producer.send_and_wait(
            topic,
            key=(key or record["event_id"]).encode("utf-8"),
            value=json.dumps(record, separators=(",", ":"), allow_nan=False).encode(
                "utf-8"
            ),
        )

    async def _send_audit_barrier(self) -> None:
        """Persist a same-partition control record to prove preceding sends ran."""
        poll_id = f"t20-poll-{uuid.uuid4().hex[:16]}"
        self.audit_ids.append(poll_id)
        requested = datetime.now(timezone.utc) - timedelta(seconds=1)
        completed = datetime.now(timezone.utc)
        barrier = {
            "schema_version": 1,
            "record_type": "poll_audit",
            "source": "usgs_live",
            "poll_id": poll_id,
            "requested_at": _utc_iso(requested),
            "completed_at": _utc_iso(completed),
            "http_status": 200,
            "content_hash": None,
            "records_received": 0,
            "records_accepted": 0,
            "records_excluded": 0,
            "error_code": None,
            "error_message": None,
        }
        await self._send(LIVE_TOPIC, barrier, key=self.event_id)
        await self._wait_for(
            "poll-audit barrier",
            lambda: self.pool.fetchval(
                "SELECT EXISTS(SELECT 1 FROM ingestion_audit WHERE poll_id = $1)",
                poll_id,
            ),
        )

    async def _wait_for(self, label: str, query) -> Any:
        deadline = asyncio.get_running_loop().time() + WAIT_SECONDS
        while asyncio.get_running_loop().time() < deadline:
            result = await query()
            if result:
                return result
            await asyncio.sleep(0.1)
        self.fail(f"Timed out waiting for {label} after {WAIT_SECONDS}s")

    async def _wait_current(self, updated_ms: int | None = None) -> asyncpg.Record:
        async def query():
            row = await self.pool.fetchrow(
                """
                SELECT event_id, mag, updated_utc, adm0_a3, country_name
                FROM (
                    SELECT e.event_id, e.mag, e.updated_utc, e.adm0_a3,
                           c.display_name AS country_name
                    FROM current_earthquakes e
                    JOIN dim_countries c USING (adm0_a3)
                    WHERE e.event_id = $1
                ) AS event
                """,
                self.event_id,
            )
            if row is None:
                return None
            if updated_ms is not None:
                expected = datetime.fromtimestamp(
                    updated_ms / 1000, tz=timezone.utc
                )
                if row["updated_utc"] != expected:
                    return None
            return row

        return await self._wait_for("current earthquake row", query)

    async def _api_events(self, event_time_ms: int) -> list[dict[str, Any]]:
        occurred = datetime.fromtimestamp(event_time_ms / 1000, tz=timezone.utc)
        response = await self.api.get(
            "/api/v1/earthquakes",
            params={
                "start_utc": _utc_iso(occurred - timedelta(seconds=1)),
                "end_utc": _utc_iso(occurred + timedelta(minutes=1)),
                "limit": 500,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["items"]

    async def test_tc01_to_tc04_live_insert_idempotency_and_revision_order(self) -> None:
        """A new event is API-visible; duplicates/stale updates cannot win."""
        initial = self._event(magnitude=5.2)
        initial_ms = initial["updated_ms"]
        event_time_ms = initial["payload"]["properties"]["time"]
        await self._send(LIVE_TOPIC, initial)
        await self._wait_current(initial_ms)

        visible = await self._api_events(event_time_ms)
        self.assertIn(self.event_id, {item["event_id"] for item in visible})
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT count(*) FROM current_earthquakes WHERE event_id = $1",
                self.event_id,
            ),
            1,
        )

        duplicate = self._event(magnitude=9.9, updated_ms=initial_ms)
        await self._send(LIVE_TOPIC, duplicate)
        await self._send_audit_barrier()
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT count(*) FROM earthquake_versions WHERE event_id = $1",
                self.event_id,
            ),
            1,
        )

        newer_ms = initial_ms + 2_000
        await self._send(
            LIVE_TOPIC, self._event(magnitude=5.6, updated_ms=newer_ms)
        )
        newer = await self._wait_current(newer_ms)
        self.assertEqual(newer["mag"], 5.6)

        stale = self._event(magnitude=3.1, updated_ms=initial_ms + 1_000)
        await self._send(LIVE_TOPIC, stale)
        await self._send_audit_barrier()
        final = await self._wait_current(newer_ms)
        self.assertEqual(final["mag"], 5.6)
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT count(*) FROM earthquake_versions WHERE event_id = $1",
                self.event_id,
            ),
            2,
        )
        api_events = await self._api_events(event_time_ms)
        api_event = next(item for item in api_events if item["event_id"] == self.event_id)
        self.assertEqual(api_event["mag"], 5.6)

    async def test_tc05_null_magnitude_is_persisted_as_null(self) -> None:
        record = self._event(magnitude=None)
        await self._send(LIVE_TOPIC, record)
        row = await self._wait_current(record["updated_ms"])
        self.assertIsNone(row["mag"])

        visible = await self._api_events(record["payload"]["properties"]["time"])
        api_event = next(item for item in visible if item["event_id"] == self.event_id)
        self.assertIsNone(api_event["mag"])

    async def test_tc06_out_of_bounds_coordinates_are_quarantined(self) -> None:
        record = self._event(latitude=120.0)
        metadata = await self._send(LIVE_TOPIC, record)
        self.quarantine_positions.append((metadata.partition, metadata.offset))

        row = await self._wait_for(
            "out-of-bounds quarantine",
            lambda: self.pool.fetchrow(
                """
                SELECT failure_reason,
                       raw_payload #>> '{payload,geometry,coordinates,1}' AS latitude
                FROM quarantine_events
                WHERE source_topic = $1 AND source_partition = $2
                  AND source_offset = $3
                """,
                LIVE_TOPIC,
                metadata.partition,
                metadata.offset,
            ),
        )
        self.assertEqual(row["failure_reason"], "INVALID_COORDINATES_OUT_OF_BOUNDS")
        self.assertEqual(float(row["latitude"]), 120.0)
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT count(*) FROM current_earthquakes WHERE event_id = $1",
                self.event_id,
            ),
            0,
        )

    async def test_tc07_ocean_event_is_not_assigned_to_nearest_country(self) -> None:
        record = self._event(longitude=-30.0, latitude=0.0)
        await self._send(LIVE_TOPIC, record)
        row = await self._wait_current(record["updated_ms"])
        self.assertEqual(row["adm0_a3"], "N/A")
        self.assertEqual(row["country_name"], "Sin país asignado")

        visible = await self._api_events(record["payload"]["properties"]["time"])
        api_event = next(item for item in visible if item["event_id"] == self.event_id)
        self.assertEqual(api_event["adm0_a3"], "N/A")
        self.assertEqual(api_event["country_name"], "Sin país asignado")

    async def test_tc08_duplicate_redelivery_does_not_duplicate_current_state(self) -> None:
        """Verify the idempotent redelivery contract used after a restart."""
        record = self._event(magnitude=4.4)
        await self._send(LIVE_TOPIC, record)
        await self._wait_current(record["updated_ms"])
        await self._send(LIVE_TOPIC, record)
        await self._send_audit_barrier()

        self.assertEqual(
            await self.pool.fetchval(
                "SELECT count(*) FROM current_earthquakes WHERE event_id = $1",
                self.event_id,
            ),
            1,
        )
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT count(*) FROM earthquake_versions WHERE event_id = $1",
                self.event_id,
            ),
            1,
        )

    async def test_tc11_replay_run_is_visible_but_never_enters_live_state(self) -> None:
        started = datetime.now(timezone.utc)
        await self._send(
            REPLAY_TOPIC,
            {
                "schema_version": 1,
                "record_type": "replay_started",
                "source": "usgs_replay",
                "run_id": self.run_id,
                "started_at": _utc_iso(started),
            },
            key=f"__run__:{self.run_id}",
        )

        replay_id = f"rpl_{uuid.uuid4().hex[:16]}"
        replay_record = self._event(replay_id, magnitude=4.8)
        replay_record.update(
            source="usgs_replay",
            mode="replay",
            run_id=self.run_id,
        )
        await self._send(REPLAY_TOPIC, replay_record)
        await self._send(
            REPLAY_TOPIC,
            {
                "schema_version": 1,
                "record_type": "replay_finished",
                "source": "usgs_replay",
                "run_id": self.run_id,
                "finished_at": _utc_iso(datetime.now(timezone.utc) + timedelta(seconds=1)),
                "status": "completed",
            },
            key=f"__run__:{self.run_id}",
        )

        async def completed_run():
            row = await self.pool.fetchrow(
                """
                SELECT status, events_received, events_processed
                FROM replay_runs WHERE run_id = $1
                """,
                self.run_id,
            )
            if (
                row is not None
                and row["status"] == "completed"
                and row["events_received"] == 1
            ):
                return row
            return None

        state = await self._wait_for("completed replay run", completed_run)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["events_received"], 1)
        self.assertEqual(state["events_processed"], 1)
        self.assertEqual(
            await self.pool.fetchval(
                """
                SELECT count(*) FROM replay_earthquakes
                WHERE run_id = $1 AND event_id = $2
                """,
                self.run_id,
                replay_id,
            ),
            1,
        )
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT count(*) FROM current_earthquakes WHERE event_id = $1",
                replay_id,
            ),
            0,
        )

        replay_response = await self.api.get(
            "/api/v1/earthquakes",
            params={"scope": "replay", "run_id": self.run_id, "limit": 500},
        )
        self.assertEqual(replay_response.status_code, 200, replay_response.text)
        self.assertEqual(replay_response.json()["scope"], "replay")
        self.assertEqual(
            {item["event_id"] for item in replay_response.json()["items"]},
            {replay_id},
        )
        live_response = await self.api.get(
            "/api/v1/earthquakes",
            params={"start_utc": "2026-01-01T00:00:00Z", "limit": 500},
        )
        self.assertEqual(live_response.status_code, 200, live_response.text)
        self.assertNotIn(
            replay_id, {item["event_id"] for item in live_response.json()["items"]}
        )


if __name__ == "__main__":
    unittest.main()
