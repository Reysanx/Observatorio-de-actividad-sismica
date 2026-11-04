"""PostgreSQL connection-pool lifecycle for the API container."""

from __future__ import annotations

import os
from typing import Any

import asyncpg


async def create_pool() -> asyncpg.Pool:
    """Create a small asynchronous pool using the Compose environment."""
    return await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "almacenamiento"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "observatorio"),
        user=os.getenv("POSTGRES_USER", "observatorio"),
        password=os.environ["POSTGRES_PASSWORD"],
        min_size=max(1, int(os.getenv("API_POOL_MIN_SIZE", "1"))),
        max_size=max(1, int(os.getenv("API_POOL_MAX_SIZE", "5"))),
        command_timeout=10,
    )


def connection_pool(app: Any) -> asyncpg.Pool:
    """Return the pool wired into application state."""
    pool = getattr(app.state, "pool", None)
    if pool is None:
        raise RuntimeError("API database pool is not initialized")
    return pool
