# Canonical Compose and Replay Names

When project documents disagree, use the constitution's Compose service IDs and the plan/task dotted Kafka topic names as the implementation vocabulary.

## What Happened

For `001-observatorio-sismico` task t1, the constitution and project rules named the five services `productor`, `broker`, `consumidor`, `almacenamiento`, and `api`, while some plan examples used `kafka` and `postgres` as network names. The functional spec also used `earthquakes-replay`, while the plan and task breakdown used `earthquakes.replay`. The canonical decisions recorded in `.github/modernize/rearchitecture/artifacts/t1-teamlead.md` retain the constitution's service IDs and dotted topic style. This aligns interfaces instead of creating aliases that could drift.

## Takeaway

Use the five constitution service IDs consistently as Compose DNS names and use `earthquakes.live` / `earthquakes.replay` as topic names. Keep replay isolated from live persistence and queries. Record any deliberate exception as an architecture decision before implementation.

## History
- 2026-11-02 (Observatorio-de-actividad-s-smica/t1): initial
