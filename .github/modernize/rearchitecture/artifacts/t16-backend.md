# t16 — Isolated replay production and persistence

## Summary

Implemented replay publishing from the checksum-verified 2025 cache and wired the consumer to process replay controls/events from `earthquakes.replay`. Event state and revisions are persisted only to run-scoped replay tables; invalid replay records use replay quarantine. Kafka offsets remain manually committed only after the PostgreSQL transaction succeeds.

## Deliverables

- [t16-backend-batch-report.yaml](./t16-backend-batch-report.yaml) — task traceability and test evidence.
- [checkpoints/t16-tasks-to-impl.yaml](./checkpoints/t16-tasks-to-impl.yaml) — implementation checkpoint.

## Source Files Changed

- `backend/scripts/replay_producer.py` — checksum-verified cache selection, replay envelope/control production, accelerated ordered send, and replay-only duplicate/revision/ocean demo cases.
- `backend/consumer/quality.py` — validates live-vs-replay topic/mode/source boundaries and replay controls.
- `backend/consumer/main.py` — subscribes to both canonical topics, routes controls and replay events, quarantines replay independently, and commits only after persistence.
- `backend/consumer/db_writer.py` — idempotent run creation/finish, strict-newer `(run_id, event_id)` upsert/versioning, run counters, and offset-idempotent replay quarantine.
- `backend/tests/test_replay_producer.py`
- `backend/tests/test_consumer_replay.py`
- `backend/tests/test_consumer_db.py`

## Naming and Behavior Decisions

- Use only `earthquakes.replay`; run control messages use key `__run__:<run_id>`, and event messages use the source `event_id`.
- The producer publishes `replay_started`, chronological version-1 `mode=replay` events, then `replay_finished`. Each send waits for Kafka acknowledgement. The existing single-partition replay topic preserves control/event order.
- Replay IDs are generated per run or accepted from `--run-id`; all event rows and versions are scoped by `(run_id, event_id)`.
- The producer reads only the completed, checksum-verified cache. `--month 2025-06` selects one month; a full-year replay is supported.
- By default each replay injects a single duplicate delivery, one later revision, and a clearly labeled synthetic ocean event. Use `--no-demo-cases` to omit the synthetic cases.
- A run is created once and not reset on control redelivery. Equal/stale event versions are successful no-ops; only strictly newer revisions append a version. Run state never writes live or baseline tables.
- Replay state API and the visible `REPRODUCCIÓN` badge remain assigned to downstream t18/t19.

## Local Replay Command

After the Compose services and the 2025 cache are ready:

```powershell
docker compose --env-file .env up --build -d broker almacenamiento consumidor
docker compose --env-file .env run --build --rm --no-deps productor python -m scripts.replay_producer --month 2025-06 --speed 120
```

The script generates a run ID when `--run-id` is omitted. No public ports, credentials, Netlify, or ngrok are needed for replay.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — verified Docker/Python toolchain and Compose execution assumptions.
- `.github/modernize/rearchitecture/artifacts/t8-devops.md` — canonical five-service Compose topology, topic setup, and persistent USGS cache volume.
- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — replay topic, envelope/control contracts, one-partition ordering, and run-scoped processing boundary.
- `.github/modernize/rearchitecture/artifacts/t10-dba.md` — replay relations, strict-newer persistence semantics, and database-before-offset invariant.
- `.github/modernize/rearchitecture/artifacts/t12-backend.md` — existing live consumer quality, spatial enrichment, quarantine, and manual offset-commit behavior.
- `.github/modernize/rearchitecture/artifacts/t14-backend.md` — completed historical cache/manifest contract and consumer-owned baseline handling.
- `specs/001-observatorio-sismico/{spec.md,plan.md,tasks.md,data-spec.md,acceptance-tests.md}` and `.specify/memory/constitution.md` — FR-09, TASK-7.2, TC-11, replay isolation, and UTC/data invariants.
- `.agents/AGENTS.md`, `.agents/rules/{architecture_invariants.md,data_quality_rules.md}`, `.agents/subagents/04-backend-modeler/AGENT.md`, and `.agents/skills/kafka-idempotent-consumer/SKILL.md` — service boundaries, persistence naming, and transactional commit behavior.

`context.md`, `decisions.md`, and `team/backend/inbox.md` were not present. Canonical decisions were taken from the listed architecture/schema artifacts and project specifications.

## Evidence Mapping

- `t3-architect.md#Kafka topics and delivery` and `#Versioned JSON envelope` → `backend/scripts/replay_producer.py`, `consumer/quality.py`, and `consumer/main.py`; replay integration published ordered controls/events to the canonical topic and the consumer committed the replay partition only after processing.
- `t3-architect.md#Processing and persistence boundaries` → `consumer/db_writer.py`; the active-run UPSERT, revision write, counter update, and offset-idempotent quarantine stay within replay relations and their PostgreSQL transaction.
- `t10-dba.md#Contract Verified` → `persist_replay_event` and replay integration tests; run-scoped rows/version counts were verified without a live-current row.
- `t12-backend.md#Handoff / Remaining Scope` → live-only consumer subscription was extended to replay while preserving the previous live path and quarantine writer.
- `t14-backend.md#Naming and Design Resolution` → replay inputs are read from the verified cached USGS baseline and are not written as baseline/live records.
- `spec.md#FR-09`, `plan.md#6`, `tasks.md#TASK-7.2`, and `acceptance-tests.md#TC-11` → controlled duplicate, revision, and ocean replay cases; separate tables and the dedicated topic were verified by tests and database queries.

## Test Results

- Command: `docker compose --env-file .env.example run --build --rm --no-deps consumidor python -m unittest discover -s tests -v`
  - Passed: 53; Failed: 0; Skipped: 5 (database integration tests, run separately).
- Command: `docker compose --env-file .env.example run --build --rm --no-deps -e RUN_DB_INTEGRATION=1 consumidor python -m unittest discover -s tests -p test_consumer_db.py -v`
  - Passed: 5; Failed: 0; Skipped: 0. Includes run-scoped replay isolation, strict-newer revision history, finished-run rejection, and replay quarantine idempotency.
- Runtime replay command: `docker compose --env-file .env.example run --build --rm --no-deps productor python -m scripts.replay_producer --run-id t16-smoke-2025-06 --month 2025-06 --speed 10000`
  - Passed: published 1,159 event messages (including the controlled demo cases) from the verified 2025 cache.
- Runtime SQL verification: `docker compose --env-file .env.example exec -T almacenamiento psql -U observatorio -d observatorio -v ON_ERROR_STOP=1 -Atc "SELECT status || '|' || events_received || '|' || events_processed || '|' || events_quarantined || '|' || (SELECT count(*) FROM replay_earthquakes WHERE run_id = 't16-smoke-2025-06') || '|' || (SELECT count(*) FROM replay_versions WHERE run_id = 't16-smoke-2025-06') || '|' || (SELECT count(*) FROM replay_quarantine_events WHERE run_id = 't16-smoke-2025-06') || '|' || (SELECT count(*) FROM current_earthquakes WHERE event_id = 'replay-ocean-t16-smoke-2025-06') FROM replay_runs WHERE run_id = 't16-smoke-2025-06'"`
  - Passed: `completed|1159|1159|0|1157|1158|0|0` for run status, received, processed, quarantined, replay rows, versions, replay quarantine rows, and matching live synthetic-ocean rows. Replay offset `1161/1161`, lag `0`. The smoke run rows were removed after verification.
- Command: `docker compose --env-file .env.example config --format json`
  - Passed: exactly `productor`, `broker`, `consumidor`, `almacenamiento`, and `api`; PostgreSQL/Kafka remain internal-only.
- Command: `git diff --check`
  - Passed: no whitespace errors.

## Handoff / Remaining Scope

- t18 should expose `replay_runs` state and require `run_id` for replay queries; t19 should render the explicit replay badge. Neither API nor UI behavior is claimed by t16.
- The replay demo producer uses the existing persistent USGS cache and does not fetch external data during replay.
- The complete 11-case acceptance suite, full-stack build, frontend behavior, and academic/TCO deliverables remain pending their assigned tasks.
