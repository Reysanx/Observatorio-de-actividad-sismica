# Run-Scoped Replay Persistence

Publish replay lifecycle controls and events in order on the dedicated single-partition topic, and persist event state only under `(run_id, event_id)`.

## What Happened

In `Observatorio-de-actividad-s-smica` task `t16`, the database schema already provided separate replay run, event, version, and quarantine relations. The producer reused the checksum-verified 2025 cache, sends start/events/finish sequentially with acknowledgements, and uses `usgs_replay` envelopes. The consumer handles both topics with manual offsets and dispatches replay to run-scoped SQL. A stale/equal revision is still a successfully consumed event even though its UPSERT returns no row; treating that result as a failed run would incorrectly quarantine duplicates. A real June 2025 replay completed with zero quarantine and zero Kafka lag.

## Takeaway

- Do not route replay through live/current or historical baseline persistence.
- Require a replay `run_id`; use `(run_id, event_id)` for state and revisions.
- Keep run controls and events ordered on `earthquakes.replay`; await broker acknowledgements.
- Commit each Kafka offset only after the database transaction has persisted the event/control/quarantine result.
- Distinguish “valid message in an active run” from “newer revision changed current state”; equal/older deliveries are valid idempotent no-ops.
- Quarantine replay failures in `replay_quarantine_events`, deduplicated by topic/partition/offset.

## History

- 2026-11-02 (`Observatorio-de-actividad-s-smica/t16`): initial
