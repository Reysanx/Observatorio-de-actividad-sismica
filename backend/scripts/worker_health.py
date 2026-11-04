"""Heartbeat and dependency probes for Compose-managed background workers."""

from __future__ import annotations

import asyncio
import os
import socket
import time
from contextlib import closing
from pathlib import Path
from typing import Callable

HEARTBEAT_INTERVAL_SECONDS = 10
HEARTBEAT_MAX_AGE_SECONDS = 45
HEARTBEAT_DIRECTORY = Path(os.getenv("WORKER_HEALTH_DIR", "/tmp"))


def heartbeat_path(service: str) -> Path:
    if service not in {"productor", "consumidor"}:
        raise ValueError(f"unsupported worker service: {service}")
    return HEARTBEAT_DIRECTORY / f"observatorio-{service}.heartbeat"


def record_heartbeat(service: str, *, now: float | None = None) -> None:
    """Write an epoch timestamp after the worker event loop makes progress."""
    path = heartbeat_path(service)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        f"{time.time() if now is None else now:.6f}\n",
        encoding="ascii",
    )
    temporary_path.replace(path)


def clear_heartbeat(service: str) -> None:
    heartbeat_path(service).unlink(missing_ok=True)


async def maintain_heartbeat(service: str) -> None:
    """Keep the worker liveness timestamp fresh while its event loop is alive."""
    while True:
        record_heartbeat(service)
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


def _parse_endpoint(value: str, default_port: int) -> tuple[str, int]:
    host, separator, raw_port = value.rpartition(":")
    if not separator:
        return value, default_port
    return host, int(raw_port)


def _dependencies(service: str) -> list[tuple[str, int]]:
    brokers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")
    endpoints = [
        _parse_endpoint(item.strip(), 9092)
        for item in brokers.split(",")
        if item.strip()
    ]
    if service == "consumidor":
        endpoints.append(
            (
                os.getenv("POSTGRES_HOST", "almacenamiento"),
                int(os.getenv("POSTGRES_PORT", "5432")),
            )
        )
    return endpoints


def check_worker_health(
    service: str,
    *,
    now: float | None = None,
    connect: Callable[..., socket.socket] = socket.create_connection,
) -> tuple[bool, str]:
    """Require a fresh application heartbeat and reachable runtime dependencies."""
    if service not in {"productor", "consumidor"}:
        return False, f"unsupported worker service: {service}"

    path = heartbeat_path(service)
    try:
        last_heartbeat = float(path.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return False, f"missing or invalid heartbeat: {path.name}"

    age = (time.time() if now is None else now) - last_heartbeat
    if age < -5 or age > HEARTBEAT_MAX_AGE_SECONDS:
        return False, f"worker heartbeat is stale ({age:.1f}s)"

    for host, port in _dependencies(service):
        try:
            with closing(connect((host, port), timeout=2)):
                pass
        except OSError as exc:
            return False, f"dependency {host}:{port} unavailable: {exc}"
    return True, "worker heartbeat and dependencies are ready"
