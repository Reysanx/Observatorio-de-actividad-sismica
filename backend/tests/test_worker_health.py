from __future__ import annotations

import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import worker_health


class WorkerHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.directory = Path(self.temp_dir.name)
        self.directory_patch = patch.object(
            worker_health,
            "HEARTBEAT_DIRECTORY",
            self.directory,
        )
        self.directory_patch.start()
        self.addCleanup(self.directory_patch.stop)

    def test_fresh_heartbeat_and_reachable_dependencies_are_healthy(self) -> None:
        worker_health.record_heartbeat("productor", now=100.0)
        connections: list[tuple[str, int]] = []

        def connect(endpoint: tuple[str, int], timeout: float) -> socket.socket:
            connections.append(endpoint)
            return _FakeSocket()

        with patch.dict(
            "os.environ",
            {"KAFKA_BOOTSTRAP_SERVERS": "broker:9092"},
            clear=True,
        ):
            healthy, message = worker_health.check_worker_health(
                "productor",
                now=110.0,
                connect=connect,
            )

        self.assertTrue(healthy, message)
        self.assertEqual(connections, [("broker", 9092)])

    def test_missing_or_stale_heartbeat_is_unhealthy(self) -> None:
        healthy, message = worker_health.check_worker_health(
            "consumidor",
            now=100.0,
            connect=lambda *_args, **_kwargs: self.fail(
                "dependencies must not be probed without a fresh heartbeat"
            ),
        )
        self.assertFalse(healthy)
        self.assertIn("heartbeat", message)

        worker_health.record_heartbeat("consumidor", now=1.0)
        healthy, message = worker_health.check_worker_health(
            "consumidor",
            now=100.0,
            connect=lambda *_args, **_kwargs: self.fail(
                "dependencies must not be probed after a stale heartbeat"
            ),
        )
        self.assertFalse(healthy)
        self.assertIn("stale", message)

    def test_database_dependency_failure_is_unhealthy(self) -> None:
        worker_health.record_heartbeat("consumidor", now=100.0)

        def connect(endpoint: tuple[str, int], timeout: float) -> socket.socket:
            if endpoint == ("almacenamiento", 5432):
                raise OSError("connection refused")
            return _FakeSocket()

        with patch.dict(
            "os.environ",
            {
                "KAFKA_BOOTSTRAP_SERVERS": "broker:9092",
                "POSTGRES_HOST": "almacenamiento",
                "POSTGRES_PORT": "5432",
            },
            clear=True,
        ):
            healthy, message = worker_health.check_worker_health(
                "consumidor",
                now=110.0,
                connect=connect,
            )

        self.assertFalse(healthy)
        self.assertIn("almacenamiento:5432", message)


class _FakeSocket:
    def close(self) -> None:
        pass


if __name__ == "__main__":
    unittest.main()
