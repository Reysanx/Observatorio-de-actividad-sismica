"""Resilient asynchronous client for the USGS GeoJSON live feed."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Awaitable, Callable

import httpx

LOGGER = logging.getLogger(__name__)


def _parse_finite_float(token: str) -> float | str:
    """Keep JSON number tokens representable as finite floats; preserve others."""
    value = float(token)
    return value if math.isfinite(value) else token


class USGSFeedError(Exception):
    """A safe-to-log USGS request or response failure."""

    def __init__(
        self,
        code: str,
        *,
        http_status: int | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.http_status = http_status


@dataclass(frozen=True)
class LiveFeed:
    """Validated USGS feed response plus source-response metadata."""

    feature_collection: dict
    http_status: int
    content_hash: str


Sleep = Callable[[float], Awaitable[None]]


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(
                0.0,
                (retry_at - datetime.now(timezone.utc)).total_seconds(),
            )
        except (TypeError, ValueError, OverflowError):
            return None


async def fetch_live_feed(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_attempts: int = 4,
    backoff_seconds: float = 2.0,
    sleep: Sleep = asyncio.sleep,
) -> LiveFeed:
    """Fetch and validate a FeatureCollection with bounded exponential backoff.

    Retries transport errors and HTTP 429/5xx responses only. Other 4xx
    responses are permanent configuration/request failures and fail quickly.
    No response body or URL is included in exceptions or logs.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least one")

    for attempt in range(max_attempts):
        response: httpx.Response | None = None
        retry_delay: float | None = None
        failure: USGSFeedError | None = None
        try:
            response = await client.get(url)
        except httpx.TimeoutException as exc:
            failure = USGSFeedError("request_timeout")
            LOGGER.warning(
                "USGS request timed out (attempt %s/%s)",
                attempt + 1,
                max_attempts,
            )
        except httpx.RequestError as exc:
            failure = USGSFeedError("request_error")
            LOGGER.warning(
                "USGS request failed (%s; attempt %s/%s)",
                type(exc).__name__,
                attempt + 1,
                max_attempts,
            )

        if response is not None:
            if response.status_code == 429 or response.status_code >= 500:
                failure = USGSFeedError(
                    "upstream_http_error",
                    http_status=response.status_code,
                )
                retry_delay = _retry_after_seconds(
                    response.headers.get("Retry-After")
                )
                LOGGER.warning(
                    "USGS returned retryable HTTP status %s (attempt %s/%s)",
                    response.status_code,
                    attempt + 1,
                    max_attempts,
                )
            elif response.is_error:
                raise USGSFeedError(
                    "upstream_http_error",
                    http_status=response.status_code,
                )
            else:
                try:
                    # Preserve non-standard JSON numeric tokens as strings.
                    # Kafka records must remain valid JSON while downstream
                    # quality checks still need to see and quarantine values
                    # such as NaN rather than silently dropping the feature.
                    collection = json.loads(
                        response.content,
                        parse_constant=lambda token: token,
                        parse_float=_parse_finite_float,
                    )
                except (json.JSONDecodeError, ValueError) as exc:
                    raise USGSFeedError(
                        "invalid_json",
                        http_status=response.status_code,
                    ) from exc

                if (
                    not isinstance(collection, dict)
                    or collection.get("type") != "FeatureCollection"
                    or not isinstance(collection.get("features"), list)
                ):
                    raise USGSFeedError(
                        "invalid_feature_collection",
                        http_status=response.status_code,
                    )

                digest = hashlib.sha256(response.content).hexdigest()
                return LiveFeed(
                    feature_collection=collection,
                    http_status=response.status_code,
                    content_hash=f"sha256:{digest}",
                )

        if failure is None:
            raise USGSFeedError("request_error")
        if attempt + 1 == max_attempts:
            raise failure

        if retry_delay is None:
            retry_delay = backoff_seconds * (2**attempt)
        # Bound a server-provided Retry-After so an upstream cannot stall the
        # producer indefinitely; the next scheduled poll is independent.
        await sleep(min(retry_delay, 60.0))

    raise USGSFeedError("request_error")
