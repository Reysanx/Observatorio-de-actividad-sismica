from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from consumer.historical_bootstrap import bootstrap_historical_baseline


class _FakeConnection:
    def __init__(self, imported_count: int | None):
        self.imported_count = imported_count
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "SELECT 1"

    async def fetchval(self, query: str, *args: object) -> int | None:
        self.executed.append((query, args))
        return self.imported_count


class _AcquireContext:
    def __init__(self, connection: _FakeConnection):
        self.connection = connection

    async def __aenter__(self) -> _FakeConnection:
        return self.connection

    async def __aexit__(self, *_: object) -> None:
        return None


class _FakePool:
    def __init__(self, imported_count: int | None):
        self.connection = _FakeConnection(imported_count)

    def acquire(self) -> _AcquireContext:
        return _AcquireContext(self.connection)


class HistoricalBootstrapTests(unittest.IsolatedAsyncioTestCase):
    async def test_skips_download_when_baseline_is_already_registered(self):
        pool = _FakePool(imported_count=123)
        with (
            patch(
                "consumer.historical_bootstrap.download_historical_2025",
                new_callable=AsyncMock,
            ) as download,
            patch(
                "consumer.historical_bootstrap.import_historical_cache",
                new_callable=AsyncMock,
            ) as import_cache,
        ):
            result = await bootstrap_historical_baseline(
                pool, Path("cache"), Path("countries.geojson")
            )

        self.assertEqual(
            result,
            {"already_imported": True, "unique_event_count": 123},
        )
        download.assert_not_awaited()
        import_cache.assert_not_awaited()
        self.assertTrue(any("pg_advisory_unlock" in sql for sql, _ in pool.connection.executed))

    async def test_downloads_and_imports_when_baseline_is_missing(self):
        pool = _FakePool(imported_count=None)
        with (
            patch(
                "consumer.historical_bootstrap.download_historical_2025",
                new_callable=AsyncMock,
                return_value={"cache_hit": False, "unique_event_count": 456},
            ) as download,
            patch(
                "consumer.historical_bootstrap.import_historical_cache",
                new_callable=AsyncMock,
                return_value={"unique_event_count": 456},
            ) as import_cache,
        ):
            result = await bootstrap_historical_baseline(
                pool, Path("cache"), Path("countries.geojson")
            )

        self.assertEqual(
            result,
            {"already_imported": False, "unique_event_count": 456},
        )
        download.assert_awaited_once_with(Path("cache"))
        import_cache.assert_awaited_once_with(
            Path("cache"),
            Path("countries.geojson"),
            pool,
            dataset_key="usgs_2025_magnitude_4_v1",
        )
        self.assertTrue(any("pg_advisory_unlock" in sql for sql, _ in pool.connection.executed))


if __name__ == "__main__":
    unittest.main()
