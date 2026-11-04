from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import httpx

from consumer.historical_import import HistoricalImportError, normalize_historical_feature
from scripts.download_historical_2025 import (
    HistoricalDownloadError,
    build_month_intervals,
    download_historical_2025,
    load_complete_cache,
)


def _feature(event_id: str, occurred_ms: int) -> dict:
    return {
        "type": "Feature",
        "id": event_id,
        "properties": {
            "type": "earthquake",
            "time": occurred_ms,
            "updated": occurred_ms + 1000,
            "mag": 4.2,
            "magType": "mb",
            "place": "test fixture",
        },
        "geometry": {"type": "Point", "coordinates": [-70.0, -30.0, -1.5]},
    }


class HistoricalDownloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_monthly_requests_split_dedupe_cache_and_resume(self):
        requests: list[dict[str, str]] = []
        january_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        february_start = datetime(2025, 2, 1, tzinfo=timezone.utc)
        january_mid = january_start + (february_start - january_start) / 2
        jan5 = int(datetime(2025, 1, 5, tzinfo=timezone.utc).timestamp() * 1000)
        jan20 = int(datetime(2025, 1, 20, tzinfo=timezone.utc).timestamp() * 1000)
        mid = int(january_mid.timestamp() * 1000)
        feb1 = int(february_start.timestamp() * 1000)

        def handler(request: httpx.Request) -> httpx.Response:
            params = dict(request.url.params)
            requests.append(params)
            start = datetime.fromisoformat(params["starttime"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(params["endtime"].replace("Z", "+00:00"))
            if start == january_start and end == february_start:
                body = {"type": "FeatureCollection", "metadata": {"count": 18001}, "features": []}
            elif start == january_start and end == january_mid:
                body = {
                    "type": "FeatureCollection",
                    "metadata": {"count": 2},
                    "features": [_feature("jan5", jan5), _feature("boundary", mid)],
                }
            elif start == january_mid and end == february_start:
                body = {
                    "type": "FeatureCollection",
                    "metadata": {"count": 3},
                    "features": [
                        _feature("boundary", mid),
                        _feature("jan20", jan20),
                        _feature("feb1", feb1),
                    ],
                }
            else:
                body = {"type": "FeatureCollection", "metadata": {"count": 0}, "features": []}
            return httpx.Response(200, json=body)

        with tempfile.TemporaryDirectory() as temporary:
            async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            try:
                result = await download_historical_2025(
                    Path(temporary),
                    client=async_client,
                    sleep=lambda _delay: asyncio.sleep(0),
                )
                cache = load_complete_cache(Path(temporary))
                january = cache["months"]["2025-01"]["features"]
                self.assertEqual(
                    [feature["id"] for feature in january],
                    ["jan5", "boundary", "jan20"],
                )
                self.assertEqual(result["unique_event_count"], 3)
                self.assertEqual(len(cache["manifest"]["months"]), 12)
                self.assertTrue(cache["manifest"]["complete"])
                self.assertTrue(
                    all(
                        request["format"] == "geojson"
                        and request["minmagnitude"] == "4.0"
                        and request["eventtype"] == "earthquake"
                        and request["orderby"] == "time-asc"
                        for request in requests
                    )
                )
                calls_before_cache_hit = len(requests)
                second = await download_historical_2025(
                    Path(temporary),
                    client=async_client,
                    sleep=lambda _delay: asyncio.sleep(0),
                )
                self.assertTrue(second["cache_hit"])
                self.assertEqual(len(requests), calls_before_cache_hit)
                (Path(temporary) / "2025_m01.geojson").write_text(
                    "tampered", encoding="utf-8"
                )
                with self.assertRaises(HistoricalDownloadError):
                    load_complete_cache(Path(temporary))
                repaired = await download_historical_2025(
                    Path(temporary),
                    client=async_client,
                    sleep=lambda _delay: asyncio.sleep(0),
                )
                self.assertFalse(repaired["cache_hit"])
                self.assertTrue(load_complete_cache(Path(temporary))["manifest"]["complete"])
            finally:
                await async_client.aclose()

    async def test_retryable_http_status_is_retried(self):
        statuses = iter((503, 200))
        attempts = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            status = next(statuses)
            return httpx.Response(
                status,
                json={"type": "FeatureCollection", "metadata": {"count": 0}, "features": []},
            )

        delays: list[float] = []

        async def record_delay(seconds: float) -> None:
            delays.append(seconds)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            from scripts.download_historical_2025 import fetch_interval

            features = await fetch_interval(
                client,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                datetime(2025, 2, 1, tzinfo=timezone.utc),
                base_url="https://usgs.example/query",
                sleep=record_delay,
            )
        self.assertEqual(features, [])
        self.assertEqual(attempts, 2)
        self.assertEqual(delays, [2.0])

    def test_builds_all_utc_monthly_half_open_intervals(self):
        intervals = build_month_intervals()
        self.assertEqual(len(intervals), 12)
        self.assertEqual(intervals[0][0].isoformat(), "2025-01-01T00:00:00+00:00")
        self.assertEqual(intervals[-1][1].isoformat(), "2026-01-01T00:00:00+00:00")
        for (_, end), (next_start, _) in zip(intervals, intervals[1:]):
            self.assertEqual(end, next_start)


class HistoricalValidationTests(unittest.TestCase):
    def test_preserves_negative_depth_and_builds_utc_event(self):
        occurred = int(datetime(2025, 6, 1, tzinfo=timezone.utc).timestamp() * 1000)
        event = normalize_historical_feature(
            _feature("us_test", occurred),
            ingested_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(event.event_id, "us_test")
        self.assertEqual(event.depth_km, -1.5)
        self.assertEqual(event.time_utc.tzinfo, timezone.utc)
        self.assertEqual(event.source, "usgs_2025")
        self.assertTrue(event.content_hash.startswith("sha256:"))

    def test_rejects_features_outside_historical_contract(self):
        occurred = int(datetime(2025, 6, 1, tzinfo=timezone.utc).timestamp() * 1000)
        invalid = _feature("us_test", occurred)
        invalid["properties"]["mag"] = 3.9
        with self.assertRaises(HistoricalImportError):
            normalize_historical_feature(invalid)

        invalid = _feature("us_test", occurred)
        invalid["geometry"]["coordinates"][1] = 95
        with self.assertRaises(HistoricalImportError):
            normalize_historical_feature(invalid)

    def test_json_cache_is_plain_geojson_not_a_live_or_replay_envelope(self):
        feature = _feature("us_test", 1748736000000)
        self.assertEqual(feature["type"], "Feature")
        self.assertNotIn("mode", feature)
        self.assertEqual(json.loads(json.dumps(feature))["id"], "us_test")


if __name__ == "__main__":
    unittest.main()
