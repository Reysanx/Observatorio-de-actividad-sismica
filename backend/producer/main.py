"""Poll USGS every minute and publish live event/audit records to Kafka."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import httpx
from aiokafka import AIOKafkaProducer

from scripts.worker_health import clear_heartbeat, maintain_heartbeat
from producer.usgs_client import USGSFeedError, fetch_live_feed

LOGGER = logging.getLogger(__name__)
LIVE_TOPIC = "earthquakes.live"
SCHEMA_VERSION = 1
SOURCE = "usgs_live"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp(value: datetime) -> str:
    """Serialize a timezone-aware instant as RFC 3339 UTC with ``Z``."""
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _content_hash(value: Any) -> str:
    digest = hashlib.sha256(_canonical_json(value)).hexdigest()
    return f"sha256:{digest}"


def _updated_ms(feature: dict[str, Any]) -> int | None:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None
    updated = properties.get("updated")
    if isinstance(updated, bool) or not isinstance(updated, int):
        return None
    return updated


def _event_id(feature: dict[str, Any]) -> str | None:
    value = feature.get("id")
    return value if isinstance(value, str) and value else None


@dataclass
class _SeenVersion:
    updated_ms: int | None
    content_hash: str


class LiveEventDeduplicator:
    """Suppress identical/older feed snapshots while allowing newer revisions."""

    def __init__(self) -> None:
        self._seen: dict[str, _SeenVersion] = {}

    def should_publish(
        self,
        event_id: str | None,
        updated_ms: int | None,
        content_hash: str,
    ) -> bool:
        # Bad/missing IDs are still sent for downstream quarantine. Use their
        # payload hash as a local key to avoid re-sending the same bad record
        # on each complete-feed poll.
        state_key = event_id or f"__invalid__:{content_hash}"
        previous = self._seen.get(state_key)
        if previous is None:
            return True
        if updated_ms is not None:
            return previous.updated_ms is None or updated_ms > previous.updated_ms
        return previous.updated_ms is None and content_hash != previous.content_hash

    def mark_published(
        self,
        event_id: str | None,
        updated_ms: int | None,
        content_hash: str,
    ) -> None:
        state_key = event_id or f"__invalid__:{content_hash}"
        self._seen[state_key] = _SeenVersion(updated_ms, content_hash)


def _encode(record: dict[str, Any]) -> bytes:
    return json.dumps(
        record,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


async def _publish(
    producer: AIOKafkaProducer,
    record: dict[str, Any],
    key: str | None,
) -> None:
    await producer.send_and_wait(
        LIVE_TOPIC,
        key=key.encode("utf-8") if key is not None else None,
        value=_encode(record),
    )


def _event_envelope(
    feature: dict[str, Any],
    ingested_at: datetime,
) -> tuple[dict[str, Any], str | None, int | None, str]:
    event_id = _event_id(feature)
    updated_ms = _updated_ms(feature)
    digest = _content_hash(feature)
    return (
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "event",
            "source": SOURCE,
            "ingested_at": utc_timestamp(ingested_at),
            "mode": "live",
            "event_id": event_id,
            "updated_ms": updated_ms,
            "content_hash": digest,
            "run_id": None,
            "payload": feature,
        },
        event_id,
        updated_ms,
        digest,
    )


async def poll_once(
    producer: AIOKafkaProducer,
    http_client: httpx.AsyncClient,
    url: str,
    deduplicator: LiveEventDeduplicator,
    *,
    now: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """Perform one source poll, publish new events, then a poll-audit record."""
    requested_at = now()
    poll_id = str(uuid.uuid4())
    received = accepted = excluded = published = 0
    excluded_reasons: dict[str, int] = {}
    http_status: int | None = None
    content_hash: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    try:
        feed = await fetch_live_feed(http_client, url)
    except USGSFeedError as exc:
        http_status = exc.http_status
        error_code = exc.code
        error_message = exc.code
        LOGGER.warning(
            "USGS poll failed poll_id=%s error_code=%s http_status=%s",
            poll_id,
            error_code,
            http_status,
        )
    else:
        http_status = feed.http_status
        content_hash = feed.content_hash
        features = feed.feature_collection["features"]
        received = len(features)
        ingested_at = now()
        for feature in features:
            if not isinstance(feature, dict):
                excluded += 1
                excluded_reasons["invalid_feature"] = (
                    excluded_reasons.get("invalid_feature", 0) + 1
                )
                continue
            properties = feature.get("properties")
            event_type = properties.get("type") if isinstance(properties, dict) else None
            if event_type != "earthquake":
                excluded += 1
                reason = "excluded_event_type"
                excluded_reasons[reason] = excluded_reasons.get(reason, 0) + 1
                continue

            accepted += 1
            envelope, event_id, updated_ms, feature_hash = _event_envelope(
                feature, ingested_at
            )
            if not deduplicator.should_publish(event_id, updated_ms, feature_hash):
                continue
            await _publish(producer, envelope, event_id)
            # Change local state only after the broker confirms delivery.
            deduplicator.mark_published(event_id, updated_ms, feature_hash)
            published += 1

    completed_at = now()
    audit = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "poll_audit",
        "poll_id": poll_id,
        "source": SOURCE,
        "requested_at": utc_timestamp(requested_at),
        "completed_at": utc_timestamp(completed_at),
        "http_status": http_status,
        "content_hash": content_hash,
        "records_received": received,
        "records_accepted": accepted,
        "records_excluded": excluded,
        "events_published": published,
        "excluded_reasons": excluded_reasons,
        "error_code": error_code,
        "error_message": error_message,
    }
    await _publish(producer, audit, poll_id)
    LOGGER.info(
        "USGS poll completed poll_id=%s status=%s received=%s accepted=%s "
        "excluded=%s published=%s error=%s",
        poll_id,
        http_status,
        received,
        accepted,
        excluded,
        published,
        error_code or "none",
    )
    return audit


@dataclass(frozen=True)
class Settings:
    bootstrap_servers: str
    live_url: str
    poll_interval_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        interval = float(os.getenv("USGS_POLL_INTERVAL_SECONDS", "60"))
        if interval <= 0:
            raise ValueError("USGS_POLL_INTERVAL_SECONDS must be positive")
        return cls(
            bootstrap_servers=os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS", "broker:9092"
            ),
            live_url=os.getenv(
                "USGS_LIVE_URL",
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
            ),
            poll_interval_seconds=interval,
        )


async def run() -> None:
    settings = Settings.from_env()
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.bootstrap_servers,
        acks="all",
        enable_idempotence=True,
        request_timeout_ms=30_000,
    )
    await producer.start()
    heartbeat_task = asyncio.create_task(maintain_heartbeat("productor"))
    deduplicator = LiveEventDeduplicator()
    timeout = httpx.Timeout(20.0, connect=5.0)
    headers = {"User-Agent": "observatorio-sismico/1.0 (USGS feed client)"}
    LOGGER.info(
        "Live producer started topic=%s poll_interval_seconds=%s",
        LIVE_TOPIC,
        settings.poll_interval_seconds,
    )
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            while True:
                poll_started = time.monotonic()
                try:
                    await poll_once(
                        producer,
                        client,
                        settings.live_url,
                        deduplicator,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # Preserve the last successful in-memory dedupe state and
                    # let the next poll recover from transient Kafka failures.
                    LOGGER.exception("Live poll processing failed")
                elapsed = time.monotonic() - poll_started
                await asyncio.sleep(
                    max(0.0, settings.poll_interval_seconds - elapsed)
                )
    finally:
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task
        clear_heartbeat("productor")
        await producer.stop()


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run())


if __name__ == "__main__":
    main()
