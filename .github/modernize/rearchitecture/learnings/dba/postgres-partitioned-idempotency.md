# PostgreSQL Partitioning and Global Idempotency

Keep globally keyed live/current rows unpartitioned when consumers require `ON CONFLICT (event_id)`; partitioned PostgreSQL uniqueness must include the partition key.

## What Happened
For `001-observatorio-sismico` task t4, the fixed 2025 baseline needed monthly partitions while the application still required a globally unique USGS event ID. A monthly fact table can only enforce `(event_id, time_utc)` uniqueness. The schema therefore pairs the partitioned fact with an unpartitioned event-key registry and deferred foreign keys, preserving global identity without weakening the partition key constraint. Replay uses separate run-scoped tables with `(run_id, event_id)` as its conflict target. Docker was unavailable, so SQL grammar and contract assertions were used, not a PostgreSQL runtime test.

## Takeaway
Before partitioning a table with an idempotent UPSERT key, check whether the partition key can be included without changing semantics. If not, leave the current-state table unpartitioned or add a carefully constrained unpartitioned identity registry. Verify actual DDL execution and re-run behavior against the target PostgreSQL version before deployment; a parser-only pass is not equivalent to executing the migration.

## History
- 2026-11-02 (001-observatorio-sismico/t4): initial
