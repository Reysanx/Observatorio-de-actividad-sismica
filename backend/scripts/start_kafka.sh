#!/usr/bin/env bash
set -Eeuo pipefail

/etc/kafka/docker/run &
broker_pid=$!

shutdown() {
  trap - TERM INT
  kill -TERM "${broker_pid}" 2>/dev/null || true
  wait "${broker_pid}" || true
}
trap shutdown TERM INT

ready=false
for attempt in {1..60}; do
  if ! kill -0 "${broker_pid}" 2>/dev/null; then
    wait "${broker_pid}"
    exit 1
  fi

  if /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --list >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 2
done

if [[ "${ready}" != true ]]; then
  echo "Kafka did not become ready within 120 seconds." >&2
  exit 1
fi

/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists \
  --topic earthquakes.live \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=172800000

/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists \
  --topic earthquakes.replay \
  --partitions 1 \
  --replication-factor 1 \
  --config retention.ms=172800000

wait "${broker_pid}"
