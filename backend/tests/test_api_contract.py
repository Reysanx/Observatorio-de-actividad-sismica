"""Contract tests for FastAPI routes and safe query scoping."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from api.main import create_app


class FakeConnection:
    def __init__(self, owner: "FakePool") -> None:
        self.owner = owner

    async def __aenter__(self) -> "FakeConnection":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def fetchval(self, query: str, *args: object) -> int:
        self.owner.queries.append((query, args))
        return 0

    async def fetch(self, query: str, *args: object) -> list[dict[str, Any]]:
        self.owner.queries.append((query, args))
        return []

    async def fetchrow(self, query: str, *args: object) -> dict[str, Any]:
        self.owner.queries.append((query, args))
        if "FROM replay_runs" in query:
            return self.owner.replay_state
        if "magnitude_null_count" in query:
            return self.owner.depth_summary
        if "recent_event_count" in query:
            return self.owner.comparison_summary
        return {
            "api_time": datetime(2026, 11, 2, 12, tzinfo=timezone.utc),
            "last_successful_poll_at": None,
            "last_event_ingested_at": datetime(2026, 11, 2, 11, 59, 30, tzinfo=timezone.utc),
            "latest_event_updated_at": datetime(2026, 11, 2, 11, 59, tzinfo=timezone.utc),
        }


class FakePool:
    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[object, ...]]] = []
        self.replay_state: dict[str, Any] | None = None
        self.depth_summary: dict[str, Any] = {
            "magnitude_null_count": 0,
            "depth_null_count": 0,
            "depth_population_count": 2,
            "depth_p90_km": 20.0,
        }
        self.comparison_summary: dict[str, Any] = {
            "calculated_at": datetime(2026, 11, 2, tzinfo=timezone.utc),
            "recent_event_count": 2,
            "historical_2025_event_count": 730,
            "historical_days": 365,
            "historical_daily_average": 2.0,
            "historical_daily_population_stddev": 1.0,
            "stored_event_count": 1000,
            "imported_event_count": 1000,
        }

    def acquire(self) -> FakeConnection:
        return FakeConnection(self)

    async def fetchrow(
        self, query: str, *args: object
    ) -> dict[str, Any] | None:
        return await FakeConnection(self).fetchrow(query, *args)


class APIRouteContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pool = FakePool()
        self.client = TestClient(create_app(pool=self.pool))

    def tearDown(self) -> None:
        self.client.close()

    def test_health_reports_database_and_serializes_utc_with_z(self) -> None:
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database_status"], "ok")
        self.assertEqual(response.json()["api_time"], "2026-11-02T12:00:00Z")
        self.assertEqual(response.json()["last_event_ingested_at"], "2026-11-02T11:59:30Z")
        self.assertEqual(response.json()["ingestion_delay_seconds"], 60.0)

    def test_event_page_defaults_live_and_has_pagination_contract(self) -> None:
        response = self.client.get("/api/v1/earthquakes?limit=25&offset=10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"items": [], "total": 0, "limit": 25, "offset": 10,
             "scope": "live", "run_id": None},
        )
        query = self.pool.queries[0][0]
        self.assertIn("current_earthquakes", query)
        self.assertNotIn("replay_earthquakes", query)

    def test_replay_scope_requires_run_id_and_never_falls_back_to_live(self) -> None:
        missing_id = self.client.get("/api/v1/earthquakes?scope=replay")
        self.assertEqual(missing_id.status_code, 422)
        response = self.client.get(
            "/api/v1/earthquakes?scope=replay&run_id=run-123"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scope"], "replay")
        self.assertEqual(response.json()["run_id"], "run-123")
        self.assertIn("replay_earthquakes", self.pool.queries[0][0])

    def test_invalid_time_and_filter_ranges_return_422(self) -> None:
        naive = self.client.get(
            "/api/v1/earthquakes?start_utc=2026-11-02T10:00:00"
            "&end_utc=2026-11-02T11:00:00Z"
        )
        bad_range = self.client.get(
            "/api/v1/earthquakes?mag_min=5&mag_max=3"
        )
        self.assertEqual(naive.status_code, 422)
        self.assertEqual(bad_range.status_code, 422)

    def test_analytics_routes_include_scope_and_null_bins(self) -> None:
        for path in (
            "/api/v1/stats/geo",
            "/api/v1/stats/hourly",
            "/api/v1/stats/distributions",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["scope"], "live")
        distribution = self.client.get("/api/v1/stats/distributions")
        self.assertEqual(distribution.json()["magnitude_null_count"], 0)
        self.assertEqual(distribution.json()["depth_null_count"], 0)
        self.assertEqual(distribution.json()["depth_p90_km"], 20.0)
        self.assertEqual(distribution.json()["depth_population_count"], 2)
        self.assertEqual(
            distribution.json()["depth_percentile_method"],
            "hyndman_fan_type_7",
        )
        self.assertIn("depth_period_start_utc", distribution.json())
        self.assertIn("depth_period_end_utc", distribution.json())

    def test_comparison_uses_symmetric_45_threshold_and_bound_filters(self) -> None:
        response = self.client.get(
            "/api/v1/stats/historical-comparison?adm0_a3=CHL"
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["magnitude_threshold"], 4.5)
        self.assertEqual(result["historical_days"], 365)
        self.assertEqual(result["historical_daily_average"], 2.0)
        self.assertEqual(result["historical_daily_population_stddev"], 1.0)
        self.assertEqual(result["recent_standard_deviations_from_mean"], 0.0)
        self.assertEqual(result["deviation_band"], "within_1_sd")
        self.assertEqual(response.json()["ratio_to_historical_daily_average"], 1.0)
        queries = [query for query, _ in self.pool.queries]
        comparison_query = next(query for query in queries if "recent_event_count" in query)
        daily_query = next(query for query in queries if "generate_series" in query)
        self.assertIn("live.mag >= 4.5", comparison_query)
        self.assertIn("baseline.mag >= 4.5", daily_query)
        self.assertIn("generate_series", daily_query)
        self.assertIn("live.adm0_a3 = $3", comparison_query)
        self.assertIn("baseline.adm0_a3 = $1", daily_query)
        self.assertEqual(self.pool.queries[0][1][2:], ("CHL",))
        self.assertEqual(self.pool.queries[1][1], ("CHL",))

    def test_comparison_marks_zero_variance_and_invalid_baseline_unavailable(self) -> None:
        self.pool.comparison_summary["historical_daily_population_stddev"] = 0.0
        response = self.client.get("/api/v1/stats/historical-comparison")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["recent_standard_deviations_from_mean"])
        self.assertEqual(response.json()["deviation_band"], "unavailable")

        self.pool.comparison_summary["stored_event_count"] = 999
        invalid = self.client.get("/api/v1/stats/historical-comparison")
        self.assertEqual(invalid.status_code, 503)

    def test_depth_percentile_excludes_invalid_values_and_isolated_by_scope(self) -> None:
        live = self.client.get(
            "/api/v1/stats/distributions?start_utc=2026-11-02T00:00:00Z"
            "&end_utc=2026-11-03T00:00:00Z"
        )
        self.assertEqual(live.status_code, 200)
        query = self.pool.queries[0][0]
        self.assertIn("percentile_cont(0.9)", query)
        self.assertIn("depth_km::TEXT NOT IN", query)
        self.assertIn("current_earthquakes", query)
        self.assertEqual(live.json()["depth_period_start_utc"], "2026-11-02T00:00:00Z")
        self.assertEqual(live.json()["depth_period_end_utc"], "2026-11-03T00:00:00Z")

        self.pool.depth_summary["depth_population_count"] = 0
        self.pool.depth_summary["depth_p90_km"] = None
        replay = self.client.get(
            "/api/v1/stats/distributions?scope=replay&run_id=run-123"
        )
        self.assertEqual(replay.status_code, 200)
        self.assertIsNone(replay.json()["depth_p90_km"])
        self.assertEqual(replay.json()["depth_population_count"], 0)
        self.assertEqual(replay.json()["scope"], "replay")
        self.assertEqual(replay.json()["run_id"], "run-123")
        self.assertIn("replay_earthquakes", self.pool.queries[-1][0])

    def test_replay_state_returns_explicit_idle_state_without_a_run(self) -> None:
        response = self.client.get("/api/v1/replay/state")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "run_id": None,
                "active": False,
                "status": "idle",
                "started_at": None,
                "finished_at": None,
                "events_received": 0,
                "events_processed": 0,
                "events_quarantined": 0,
            },
        )
        query = self.pool.queries[-1][0]
        self.assertIn("FROM replay_runs", query)
        self.assertIn("ORDER BY started_at DESC, run_id DESC", query)
        self.assertNotIn("current_earthquakes", query)

    def test_replay_state_returns_newest_active_run_and_utc_timestamps(self) -> None:
        self.pool.replay_state = {
            "run_id": "run-2026-11",
            "status": "running",
            "started_at": datetime(
                2026, 11, 2, 14, tzinfo=timezone.utc
            ),
            "finished_at": None,
            "events_received": 11,
            "events_processed": 9,
            "events_quarantined": 2,
        }
        response = self.client.get("/api/v1/replay/state")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "run_id": "run-2026-11",
                "active": True,
                "status": "running",
                "started_at": "2026-11-02T14:00:00Z",
                "finished_at": None,
                "events_received": 11,
                "events_processed": 9,
                "events_quarantined": 2,
            },
        )

    def test_completed_replay_run_is_not_active(self) -> None:
        self.pool.replay_state = {
            "run_id": "run-complete",
            "status": "completed",
            "started_at": datetime(2026, 11, 2, 14, tzinfo=timezone.utc),
            "finished_at": datetime(2026, 11, 2, 14, 5, tzinfo=timezone.utc),
            "events_received": 3,
            "events_processed": 3,
            "events_quarantined": 0,
        }
        response = self.client.get("/api/v1/replay/state")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["active"])
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(response.json()["finished_at"], "2026-11-02T14:05:00Z")

    def test_local_frontend_cors_allows_ngrok_header(self) -> None:
        response = self.client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:4200",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "ngrok-skip-browser-warning",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:4200",
        )
        self.assertIn(
            "ngrok-skip-browser-warning",
            response.headers["access-control-allow-headers"],
        )


if __name__ == "__main__":
    unittest.main()
