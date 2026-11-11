from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

import httpx

from producer.main import LiveEventDeduplicator, poll_once, utc_timestamp
from producer.usgs_client import USGSFeedError, fetch_live_feed


class FakeProducer:
    def __init__(self) -> None:
        self.records: list[tuple[str, bytes | None, dict]] = []

    async def send_and_wait(
        self,
        topic: str,
        *,
        key: bytes | None,
        value: bytes,
    ) -> None:
        self.records.append((topic, key, json.loads(value)))


class TimestampSerializationTests(unittest.TestCase):
    def test_utc_timestamp_preserves_microseconds(self) -> None:
        instant = datetime(2026, 11, 11, 12, 0, 0, 123456, tzinfo=timezone.utc)

        self.assertEqual(utc_timestamp(instant), "2026-11-11T12:00:00.123456Z")

    def test_utc_timestamp_keeps_whole_seconds_compact(self) -> None:
        instant = datetime(2026, 11, 11, 12, 0, 0, tzinfo=timezone.utc)

        self.assertEqual(utc_timestamp(instant), "2026-11-11T12:00:00Z")


def _feature(event_id: str, updated: int, event_type: str = "earthquake") -> dict:
    return {
        "type": "Feature",
        "id": event_id,
        "properties": {
            "type": event_type,
            "updated": updated,
            "mag": None,
        },
        "geometry": {"type": "Point", "coordinates": [10.0, 20.0, -1.0]},
    }


class USGSClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_hashes_raw_response_and_returns_valid_collection(self) -> None:
        body = b'{"type":"FeatureCollection","features":[]}'

        async def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=body)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            feed = await fetch_live_feed(client, "https://usgs.test/feed")

        self.assertEqual(feed.http_status, 200)
        self.assertEqual(feed.feature_collection["features"], [])
        self.assertTrue(feed.content_hash.startswith("sha256:"))

    async def test_preserves_nonstandard_nan_for_downstream_quarantine(self) -> None:
        body = (
            b'{"type":"FeatureCollection","features":['
            b'{"type":"Feature","id":"bad-coord","properties":{"type":"earthquake",'
            b'"updated":100,"mag":1e999},"geometry":{"type":"Point",'
            b'"coordinates":[NaN,20,1]}}]}'
        )

        async def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=body)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            fake = FakeProducer()
            audit = await poll_once(
                fake,
                client,
                "https://usgs.test/feed",
                LiveEventDeduplicator(),
            )

        event = next(
            record
            for _, _, record in fake.records
            if record["record_type"] == "event"
        )
        self.assertEqual(event["payload"]["geometry"]["coordinates"][0], "NaN")
        self.assertEqual(event["payload"]["properties"]["mag"], "1e999")
        self.assertEqual(audit["http_status"], 200)
        self.assertEqual(audit["events_published"], 1)

    async def test_invalid_json_audit_keeps_http_status(self) -> None:
        async def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"not-json")

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            with self.assertRaises(USGSFeedError) as raised:
                await fetch_live_feed(client, "https://usgs.test/feed")

        self.assertEqual(raised.exception.code, "invalid_json")
        self.assertEqual(raised.exception.http_status, 200)

    async def test_retries_429_with_bounded_exponential_backoff(self) -> None:
        statuses = iter((429, 503, 200))
        waits: list[float] = []

        async def handler(_: httpx.Request) -> httpx.Response:
            status = next(statuses)
            return httpx.Response(
                status,
                json={"type": "FeatureCollection", "features": []},
            )

        async def fake_sleep(seconds: float) -> None:
            waits.append(seconds)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            feed = await fetch_live_feed(
                client,
                "https://usgs.test/feed",
                backoff_seconds=0.25,
                sleep=fake_sleep,
            )

        self.assertEqual(feed.http_status, 200)
        self.assertEqual(waits, [0.25, 0.5])

    async def test_does_not_retry_permanent_http_error(self) -> None:
        calls = 0

        async def handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(404)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            with self.assertRaises(USGSFeedError) as raised:
                await fetch_live_feed(client, "https://usgs.test/feed")

        self.assertEqual(raised.exception.http_status, 404)
        self.assertEqual(calls, 1)


class LiveProducerTests(unittest.IsolatedAsyncioTestCase):
    async def test_filters_envelopes_keys_and_deduplicates_older_versions(self) -> None:
        features = [
            _feature("us1", 100),
            _feature("blast1", 100, event_type="quarry blast"),
        ]
        body = json.dumps(
            {"type": "FeatureCollection", "features": features}
        ).encode()

        async def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=body)

        fixed_time = datetime(2026, 11, 2, 17, 0, tzinfo=timezone.utc)
        now = lambda: fixed_time
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            fake = FakeProducer()
            deduplicator = LiveEventDeduplicator()
            first = await poll_once(
                fake, client, "https://usgs.test/feed", deduplicator, now=now
            )
            second = await poll_once(
                fake, client, "https://usgs.test/feed", deduplicator, now=now
            )

        event_records = [
            (key, value)
            for _, key, value in fake.records
            if value["record_type"] == "event"
        ]
        audits = [
            value
            for _, _, value in fake.records
            if value["record_type"] == "poll_audit"
        ]
        self.assertEqual(len(event_records), 1)
        self.assertEqual(event_records[0][0], b"us1")
        envelope = event_records[0][1]
        self.assertEqual(envelope["mode"], "live")
        self.assertEqual(envelope["source"], "usgs_live")
        self.assertEqual(envelope["updated_ms"], 100)
        self.assertIsNone(envelope["payload"]["properties"]["mag"])
        self.assertEqual((first["records_received"], first["records_accepted"]), (2, 1))
        self.assertEqual(first["records_excluded"], 1)
        self.assertEqual(first["events_published"], 1)
        self.assertEqual(second["events_published"], 0)
        self.assertEqual(len(audits), 2)

    async def test_newer_revision_is_published_after_ack(self) -> None:
        fixed_time = datetime(2026, 11, 2, 17, 0, tzinfo=timezone.utc)
        versions = iter((100, 101))

        async def handler(_: httpx.Request) -> httpx.Response:
            feature = _feature("us-revision", next(versions))
            return httpx.Response(
                200,
                json={"type": "FeatureCollection", "features": [feature]},
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            fake = FakeProducer()
            deduplicator = LiveEventDeduplicator()
            for _ in range(2):
                await poll_once(
                    fake,
                    client,
                    "https://usgs.test/feed",
                    deduplicator,
                    now=lambda: fixed_time,
                )

        events = [
            record
            for _, _, record in fake.records
            if record["record_type"] == "event"
        ]
        self.assertEqual([event["updated_ms"] for event in events], [100, 101])

    async def test_unacknowledged_event_is_retried_on_next_poll(self) -> None:
        feature = _feature("us-unacked", 100)

        async def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"type": "FeatureCollection", "features": [feature]},
            )

        class FailFirstEventProducer(FakeProducer):
            fail_once = True

            async def send_and_wait(
                self,
                topic: str,
                *,
                key: bytes | None,
                value: bytes,
            ) -> None:
                record = json.loads(value)
                if record["record_type"] == "event" and self.fail_once:
                    self.fail_once = False
                    raise OSError("broker acknowledgement unavailable")
                await super().send_and_wait(topic, key=key, value=value)

        fixed_time = datetime(2026, 11, 2, 17, 0, tzinfo=timezone.utc)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            fake = FailFirstEventProducer()
            deduplicator = LiveEventDeduplicator()
            with self.assertRaises(OSError):
                await poll_once(
                    fake,
                    client,
                    "https://usgs.test/feed",
                    deduplicator,
                    now=lambda: fixed_time,
                )
            audit = await poll_once(
                fake,
                client,
                "https://usgs.test/feed",
                deduplicator,
                now=lambda: fixed_time,
            )

        self.assertEqual(audit["events_published"], 1)
        self.assertEqual(
            [record[2]["record_type"] for record in fake.records],
            ["event", "poll_audit"],
        )

    async def test_failed_http_poll_emits_audit_without_event_records(self) -> None:
        async def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        async def no_wait(_: float) -> None:
            return None

        fixed_time = datetime(2026, 11, 2, 17, 0, tzinfo=timezone.utc)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            fake = FakeProducer()
            # Use an injected fetch wrapper to keep this failure-path test fast.
            async def fail_fast(*args: object, **kwargs: object) -> object:
                return await fetch_live_feed(
                    args[0],  # type: ignore[arg-type]
                    args[1],  # type: ignore[arg-type]
                    max_attempts=1,
                    sleep=no_wait,
                )

            from unittest.mock import patch

            with patch("producer.main.fetch_live_feed", fail_fast):
                audit = await poll_once(
                    fake,
                    client,
                    "https://usgs.test/feed",
                    LiveEventDeduplicator(),
                    now=lambda: fixed_time,
                )

        self.assertEqual(audit["error_code"], "upstream_http_error")
        self.assertEqual(audit["http_status"], 503)
        self.assertEqual(audit["records_received"], 0)
        self.assertEqual(len(fake.records), 1)
        self.assertEqual(fake.records[0][2]["record_type"], "poll_audit")


if __name__ == "__main__":
    unittest.main()
