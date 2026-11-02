# Replay Storage and API Contract

For this project's local MVP, isolate replay in separate run-scoped persistence and API queries rather than relying only on a Kafka topic or a shared-table mode flag.

## What Happened

In t3 (`Observatorio-de-actividad-s-smica`), the PM handoff showed that a dedicated replay topic alone did not guarantee isolation from live counts or analytics. The architecture therefore defines `replay_runs`, `replay_earthquakes`, `replay_versions`, and `replay_quarantine_events`, plus a required `run_id` for replay API reads. Replay controls and events share a single-partition topic to preserve run start/event/finish order in the local MVP.

## Takeaway

Treat isolation as an end-to-end storage/query invariant: route by both topic and envelope mode, persist replay revisions/quarantine separately, scope each replay query to one run, and make live APIs default to live-only data. Keep the historical comparison baseline separate from both live and replay data.

## History
- 2026-11-02 (Observatorio-de-actividad-s-smica/t3): initial
