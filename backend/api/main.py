"""FastAPI application entry point for the local Compose API service."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.db import create_pool
from api.routes import comparison, earthquakes, health, replay, stats

LOGGER = logging.getLogger(__name__)


def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", "http://localhost:4200")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def create_app(*, pool: Any = None, pool_factory: Any = create_pool) -> FastAPI:
    """Build the ASGI app; optional pool injection keeps contract tests isolated."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if app.state.pool is None:
            app.state.pool = await pool_factory()
        try:
            yield
        finally:
            if app.state.owns_pool and app.state.pool is not None:
                await app.state.pool.close()

    app = FastAPI(
        title="Observatorio Sísmico API",
        version="1.0.0",
        description="Local read-only event and analytics API. All timestamps are UTC.",
        lifespan=lifespan,
    )
    app.state.pool = pool
    app.state.owns_pool = pool is None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Content-Type", "ngrok-skip-browser-warning"],
    )
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(earthquakes.router, prefix="/api/v1", tags=["earthquakes"])
    app.include_router(stats.router, prefix="/api/v1", tags=["statistics"])
    app.include_router(comparison.router, prefix="/api/v1", tags=["comparison"])
    app.include_router(replay.router, prefix="/api/v1", tags=["replay"])

    @app.exception_handler(asyncpg.PostgresError)
    async def postgres_error_handler(_: Any, exc: asyncpg.PostgresError) -> JSONResponse:
        LOGGER.warning("database request failed: %s", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"detail": "database query failed"},
        )

    return app


app = create_app()
