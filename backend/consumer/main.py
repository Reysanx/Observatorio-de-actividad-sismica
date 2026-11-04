"""Consume live Kafka records, validate/enrich, and commit offsets after PostgreSQL."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress
from typing import Any

import asyncpg
from aiokafka import AIOKafkaConsumer
from aiokafka.structs import OffsetAndMetadata, TopicPartition

from scripts.worker_health import clear_heartbeat, maintain_heartbeat
from consumer.db_writer import (
    load_country_dimension,
    persist_live_event,
    persist_poll_audit,
    persist_quarantine,
    persist_replay_event,
    persist_replay_finished,
    persist_replay_quarantine,
    persist_replay_started,
)
from consumer.quality import (
    QualityError,
    decode_message,
    validate_event,
    validate_poll_audit,
    validate_replay_control,
)
from consumer.spatial import SpatialIndex

LOGGER = logging.getLogger(__name__)
LIVE_TOPIC = "earthquakes.live"
REPLAY_TOPIC = "earthquakes.replay"
CONSUMER_GROUP = "observatorio-consumer-group"


async def process_message(
    message: Any,
    *,
    pool: asyncpg.Pool,
    spatial_index: SpatialIndex,
) -> str:
    """Commit one record's durable outcome or raise before Kafka offset commit."""
    record: Any = None
    try:
        record = decode_message(message.value)
        if not isinstance(record, dict):
            raise QualityError(
                "INVALID_EVENT_SCHEMA",
                "Kafka JSON root must be an object",
                raw_payload=record,
            )
        record_type = record.get("record_type")
        if record_type == "event":
            event = validate_event(record, topic=message.topic)
            country = spatial_index.find_country(event.geom_lon, event.geom_lat)
            if event.mode == "live":
                await persist_live_event(pool, event, country)
            elif not await persist_replay_event(pool, event, country):
                raise QualityError(
                    "REPLAY_RUN_NOT_ACTIVE",
                    "replay event arrived before its run started or after it finished",
                    raw_payload=record,
                )
            return "event"
        if record_type == "poll_audit":
            audit = validate_poll_audit(record, topic=message.topic)
            await persist_poll_audit(pool, audit)
            return "poll_audit"
        if record_type in {"replay_started", "replay_finished"}:
            control = validate_replay_control(record, topic=message.topic)
            if control.record_type == "replay_started":
                await persist_replay_started(pool, control)
                return "replay_started"
            if not await persist_replay_finished(pool, control):
                raise QualityError(
                    "REPLAY_RUN_NOT_ACTIVE",
                    "replay finish arrived before its run started",
                    raw_payload=record,
                )
            return "replay_finished"
        raise QualityError(
            "UNSUPPORTED_RECORD_TYPE",
            "record_type is not supported on this Kafka topic",
            raw_payload=record,
        )
    except QualityError as exc:
        raw_payload = exc.raw_payload if exc.raw_payload is not None else record
        event_id = _source_event_id(record)
        if message.topic == REPLAY_TOPIC:
            run_id = record.get("run_id") if isinstance(record, dict) else None
            await persist_replay_quarantine(
                pool,
                source_partition=message.partition,
                source_offset=message.offset,
                raw_message=message.value,
                raw_payload=raw_payload,
                run_id=run_id,
                source_event_id=event_id,
                failure_reason=exc.reason,
                failure_detail=exc.detail,
                count_as_event=(
                    isinstance(record, dict) and record.get("record_type") == "event"
                ),
            )
        else:
            await persist_quarantine(
                pool,
                source_topic=message.topic,
                source_partition=message.partition,
                source_offset=message.offset,
                raw_message=message.value,
                raw_payload=raw_payload,
                source_event_id=event_id,
                failure_reason=exc.reason,
                failure_detail=exc.detail,
            )
        LOGGER.warning(
            "Kafka record quarantined topic=%s partition=%s offset=%s reason=%s",
            message.topic,
            message.partition,
            message.offset,
            exc.reason,
        )
        return "quarantined"


async def process_and_commit(
    consumer: AIOKafkaConsumer,
    message: Any,
    *,
    pool: asyncpg.Pool,
    spatial_index: SpatialIndex,
) -> str:
    """Persist a record first, then acknowledge only its next Kafka offset."""
    result = await process_message(
        message,
        pool=pool,
        spatial_index=spatial_index,
    )
    await consumer.commit(
        {
            TopicPartition(message.topic, message.partition): OffsetAndMetadata(
                message.offset + 1,
                "",
            )
        }
    )
    return result


def _source_event_id(record: Any) -> str | None:
    if not isinstance(record, dict):
        return None
    value = record.get("event_id")
    if not isinstance(value, str):
        payload = record.get("payload")
        value = payload.get("id") if isinstance(payload, dict) else None
    return value[:64] if isinstance(value, str) else None


async def _create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "almacenamiento"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "observatorio"),
        user=os.getenv("POSTGRES_USER", "observatorio"),
        password=os.environ["POSTGRES_PASSWORD"],
        min_size=int(os.getenv("POSTGRES_POOL_MIN_SIZE", "1")),
        max_size=int(os.getenv("POSTGRES_POOL_MAX_SIZE", "5")),
        command_timeout=30,
    )


async def run_consumer() -> None:
    """Process live and run-scoped replay records with manual offset commits."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    spatial_index = SpatialIndex.from_geojson(
        os.getenv("NATURAL_EARTH_GEOJSON", "/app/data/paises.geojson")
    )
    pool = await _create_pool()
    consumer = AIOKafkaConsumer(
        os.getenv("KAFKA_LIVE_TOPIC", LIVE_TOPIC),
        os.getenv("KAFKA_REPLAY_TOPIC", REPLAY_TOPIC),
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092"),
        group_id=os.getenv("KAFKA_GROUP_ID", CONSUMER_GROUP),
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        max_poll_records=1,
        value_deserializer=None,
    )
    heartbeat_task: asyncio.Task[None] | None = None
    try:
        await load_country_dimension(pool, spatial_index.countries)
        await consumer.start()
        heartbeat_task = asyncio.create_task(maintain_heartbeat("consumidor"))
        LOGGER.info(
            "consumer started topics=%s,%s group=%s countries=%s",
            os.getenv("KAFKA_LIVE_TOPIC", LIVE_TOPIC),
            os.getenv("KAFKA_REPLAY_TOPIC", REPLAY_TOPIC),
            os.getenv("KAFKA_GROUP_ID", CONSUMER_GROUP),
            len(spatial_index.countries),
        )
        async for message in consumer:
            result = await process_and_commit(
                consumer,
                message,
                pool=pool,
                spatial_index=spatial_index,
            )
            LOGGER.debug(
                "Kafka record committed topic=%s partition=%s offset=%s result=%s",
                message.topic,
                message.partition,
                message.offset,
                result,
            )
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task
            clear_heartbeat("consumidor")
        await consumer.stop()
        await pool.close()


def main() -> None:
    asyncio.run(run_consumer())


if __name__ == "__main__":
    main()
