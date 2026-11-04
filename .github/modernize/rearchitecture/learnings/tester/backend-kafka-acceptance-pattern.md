# Backend Kafka Acceptance Pattern

Use real Kafka/PostgreSQL, per-test IDs, and a persisted same-partition audit barrier to verify asynchronous consumer outcomes without timing-only sleeps.

## What Happened

For Observatorio task t20, backend acceptance tests ran inside the Compose API service and published fixtures to the consumer's live/replay topics. A unique `poll_audit` record keyed to the same live Kafka partition was persisted as a barrier, proving that earlier duplicate/stale records had been processed before checking no-op counts. Quarantine assertions used the returned Kafka partition/offset. Replay assertions used one run ID and verified absence from live state.

## Takeaway

- Follow the repository's existing `unittest.IsolatedAsyncioTestCase` pattern rather than adding pytest-asyncio.
- Use a unique event ID and a bounded database polling loop for asynchronous writes.
- For no-op messages, produce a valid observable control record to the same partition and wait for its database row; do not rely on arbitrary sleeps.
- Always cleanup only test-owned rows, in FK-safe order.
- A duplicate redelivery test is not evidence that a container restart was tested; report those as separate coverage claims.

## History
- 2026-11-02 (Observatorio-de-actividad-s-smica/t20): initial
