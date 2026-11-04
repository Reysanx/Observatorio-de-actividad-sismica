# Replay State API Contract

Expose only the newest persisted replay run with explicit idle and active semantics, keeping the route isolated from live event relations.

## What Happened

In `Observatorio-de-actividad-s-smica` task `t18`, the architecture required a latest-run API state but the DTO fields were not fully enumerated. The `replay_runs` schema already provided run ID, constrained status, lifecycle timestamps, and counters. The endpoint therefore returns those fields, derives `active` only from `starting`/`running`, and emits `status=idle` with null ID/timestamps and zero counters when the registry is empty. The query has deterministic newest-first ordering and does not read event tables.

## Takeaway

- Keep the UI state endpoint separate from event/analytics filters; it returns one newest run.
- Treat `idle` as response-only; persisted statuses are `starting`, `running`, `completed`, or `failed`.
- Define active as `starting` or `running`, and serialize lifecycle timestamps with the shared UTC `Z` DTO behavior.
- Select state exclusively from `replay_runs`; never infer replay activity from live rows.

## History

- 2026-11-02 (`Observatorio-de-actividad-s-smica/t18`): initial
