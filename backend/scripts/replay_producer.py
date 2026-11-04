"""Publish a checksum-verified 2025 catalog run on the isolated replay topic."""

from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import logging
import math
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from aiokafka import AIOKafkaProducer

from consumer.historical import normalize_historical_feature
from scripts.download_historical_2025 import (
    HistoricalDownloadError,
    build_month_intervals,
    load_complete_cache,
    month_key,
)

LOGGER = logging.getLogger(__name__)
REPLAY_TOPIC = "earthquakes.replay"
SCHEMA_VERSION = 1
SOURCE = "usgs_replay"
RUN_KEY_PREFIX = "__run__:"
Sleep = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class ReplayResult:
    run_id: str
    events_published: int


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
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


def _content_hash(feature: dict[str, Any]) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(feature)).hexdigest()}"


def _encode(record: dict[str, Any]) -> bytes:
    return json.dumps(
        record,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or re.fullmatch(r"[A-Za-z0-9._:-]{1,64}", run_id) is None:
        raise ValueError("run_id must contain 1-64 letters, digits, dot, underscore, colon or hyphen")
    return run_id


def load_replay_features(
    cache_dir: str | Path,
    *,
    month: str | None = None,
) -> list[dict[str, Any]]:
    """Load selected 2025 features only from the verified completed cache."""
    if month is not None and month not in {
        month_key(start) for start, _ in build_month_intervals()
    }:
        raise ValueError("month must be a calendar month in 2025 (YYYY-MM)")
    try:
        cache = load_complete_cache(Path(cache_dir))
    except HistoricalDownloadError:
        raise

    selected: dict[str, tuple[datetime, dict[str, Any]]] = {}
    for start, end in build_month_intervals():
        key = month_key(start)
        if month is not None and key != month:
            continue
        month_data = cache["months"].get(key)
        if not isinstance(month_data, dict) or not isinstance(month_data.get("features"), list):
            raise HistoricalDownloadError(f"verified cache is missing the {key} feature list")
        for feature in month_data["features"]:
            event = normalize_historical_feature(feature)
            if not start <= event.time_utc < end:
                raise HistoricalDownloadError(
                    f"event {event.event_id} is outside cache partition {key}"
                )
            selected.setdefault(event.event_id, (event.time_utc, event.payload))
    if not selected:
        raise HistoricalDownloadError("selected replay range contains no valid 2025 events")
    return [
        payload
        for _, payload in sorted(
            selected.values(),
            key=lambda item: (item[0], str(item[1].get("id", ""))),
        )
    ]


def _event_envelope(
    feature: dict[str, Any],
    *,
    run_id: str,
    ingested_at: datetime,
) -> dict[str, Any]:
    updated_ms = feature["properties"]["updated"]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "event",
        "source": SOURCE,
        "ingested_at": utc_timestamp(ingested_at),
        "mode": "replay",
        "event_id": feature["id"],
        "updated_ms": updated_ms,
        "content_hash": _content_hash(feature),
        "run_id": run_id,
        "payload": feature,
    }


def _ocean_demo_feature(template: dict[str, Any], run_id: str) -> dict[str, Any]:
    properties = template["properties"]
    event_time = properties["time"]
    updated = max(event_time, properties["updated"]) + 1000
    return {
        "type": "Feature",
        "id": f"replay-ocean-{run_id[-16:]}",
        "properties": {
            "type": "earthquake",
            "mag": 4.2,
            "magType": "mww",
            "time": event_time,
            "updated": updated,
            "place": "Synthetic replay-only ocean fixture",
        },
        "geometry": {"type": "Point", "coordinates": [-30.0, 0.0, 10.0]},
    }


def build_replay_event_records(
    features: list[dict[str, Any]],
    *,
    run_id: str,
    ingested_at: datetime,
    include_demo_cases: bool = True,
) -> list[dict[str, Any]]:
    """Build ordered envelopes and optionally inject one duplicate/revision/ocean set."""
    run_id = _validate_run_id(run_id)
    if not features:
        raise ValueError("replay requires at least one source feature")
    ordered = sorted(
        features,
        key=lambda feature: (
            feature["properties"]["time"],
            feature["id"],
        ),
    )
    records: list[dict[str, Any]] = []
    for index, feature in enumerate(ordered):
        normalized = normalize_historical_feature(feature, ingested_at=ingested_at)
        base_feature = copy.deepcopy(normalized.payload)
        records.append(
            _event_envelope(base_feature, run_id=run_id, ingested_at=ingested_at)
        )
        if index != 0 or not include_demo_cases:
            continue

        # Re-delivery of the same version is an idempotency case.
        records.append(
            _event_envelope(
                copy.deepcopy(base_feature),
                run_id=run_id,
                ingested_at=ingested_at,
            )
        )

        # A strictly newer source update exercises replay-only version history.
        revised = copy.deepcopy(base_feature)
        revised_properties = revised["properties"]
        revised_properties["updated"] += 1000
        revised_properties["mag"] = round(float(revised_properties["mag"]) + 0.1, 1)
        records.append(
            _event_envelope(revised, run_id=run_id, ingested_at=ingested_at)
        )

        # Explicit replay-only fixture keeps ocean handling demonstrable even
        # when the selected catalog month happens to contain no ocean event.
        records.append(
            _event_envelope(
                _ocean_demo_feature(base_feature, run_id),
                run_id=run_id,
                ingested_at=ingested_at,
            )
        )
    return records


async def _send(
    producer: AIOKafkaProducer,
    record: dict[str, Any],
    key: str,
) -> None:
    await producer.send_and_wait(
        REPLAY_TOPIC,
        key=key.encode("utf-8"),
        value=_encode(record),
    )


async def publish_replay_run(
    producer: AIOKafkaProducer,
    *,
    cache_dir: str | Path,
    run_id: str,
    month: str | None = None,
    speed: float = 120.0,
    max_delay_seconds: float = 0.05,
    include_demo_cases: bool = True,
    now: Callable[[], datetime] = utc_now,
    sleep: Sleep = asyncio.sleep,
) -> ReplayResult:
    """Publish run control, events and finish in order, waiting for each broker ack."""
    run_id = _validate_run_id(run_id)
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError("speed must be greater than zero")
    if not math.isfinite(max_delay_seconds) or max_delay_seconds < 0:
        raise ValueError("max_delay_seconds must be finite and non-negative")
    features = load_replay_features(cache_dir, month=month)
    started_at = now()
    await _send(
        producer,
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "replay_started",
            "source": SOURCE,
            "run_id": run_id,
            "started_at": utc_timestamp(started_at),
        },
        f"{RUN_KEY_PREFIX}{run_id}",
    )

    try:
        ingested_at = now()
        records = build_replay_event_records(
            features,
            run_id=run_id,
            ingested_at=ingested_at,
            include_demo_cases=include_demo_cases,
        )
        previous_time_ms: int | None = None
        for record in records:
            occurred_ms = record["payload"]["properties"]["time"]
            if previous_time_ms is not None:
                scaled_delay = max(0.0, (occurred_ms - previous_time_ms) / 1000 / speed)
                delay = min(scaled_delay, max_delay_seconds)
                if delay:
                    await sleep(delay)
            await _send(producer, record, record["event_id"])
            previous_time_ms = occurred_ms
    except Exception as exc:
        failed_at = now()
        failed_record = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "replay_finished",
            "source": SOURCE,
            "run_id": run_id,
            "finished_at": utc_timestamp(failed_at),
            "status": "failed",
            "error_message": f"publisher failed: {type(exc).__name__}",
        }
        try:
            await _send(producer, failed_record, f"{RUN_KEY_PREFIX}{run_id}")
        except Exception:
            LOGGER.exception("failed to publish replay failure control run_id=%s", run_id)
        raise

    await _send(
        producer,
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "replay_finished",
            "source": SOURCE,
            "run_id": run_id,
            "finished_at": utc_timestamp(now()),
            "status": "completed",
        },
        f"{RUN_KEY_PREFIX}{run_id}",
    )
    return ReplayResult(run_id=run_id, events_published=len(records))


async def _run(args: argparse.Namespace) -> ReplayResult:
    producer = AIOKafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092"),
        acks="all",
        enable_idempotence=True,
    )
    await producer.start()
    try:
        return await publish_replay_run(
            producer,
            cache_dir=args.cache_dir,
            run_id=args.run_id or f"replay-{uuid.uuid4().hex}",
            month=args.month,
            speed=args.speed,
            include_demo_cases=not args.no_demo_cases,
        )
    finally:
        await producer.stop()


def main() -> None:
    cache_root = Path(os.getenv("USGS_CACHE_DIR", "/var/lib/observatorio/cache"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=cache_root / "historical",
        help="directory containing the verified 2025 monthly cache and manifest",
    )
    parser.add_argument("--month", help="limit this run to one month, e.g. 2025-06")
    parser.add_argument("--speed", type=float, default=120.0, help="historical time acceleration")
    parser.add_argument("--run-id", help="optional run identifier (generated when omitted)")
    parser.add_argument(
        "--no-demo-cases",
        action="store_true",
        help="omit the synthetic duplicate, revision, and ocean fixtures",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    result = asyncio.run(_run(args))
    LOGGER.info(
        "replay published run_id=%s events=%s topic=%s",
        result.run_id,
        result.events_published,
        REPLAY_TOPIC,
    )


if __name__ == "__main__":
    main()
