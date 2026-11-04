# t18 — Run-Scoped Replay API State

## Summary

Added `GET /api/v1/replay/state`, which reads only `replay_runs` and returns the newest replay lifecycle state. With no persisted run, the endpoint responds with an explicit idle state; starting/running runs are active, and completed/failed runs are inactive. Response timestamps use the API's UTC `Z` serialization.

## Deliverables

- [t18-backend-batch-report.yaml](./t18-backend-batch-report.yaml) — task traceability, test summary, and changed-file list.
- [checkpoints/t18-tasks-to-impl.yaml](./checkpoints/t18-tasks-to-impl.yaml) — implementation checkpoint and upstream traceability.

## Source Files Changed

- `backend/api/models.py` — added immutable `ReplayStateResponse`.
- `backend/api/routes/replay.py` — added the latest-run query and idle fallback.
- `backend/api/main.py` — registered the replay router.
- `backend/tests/test_api_contract.py` — covered idle, active, completed, and UTC response behavior.

## Contract Decisions

- Query ordering is deterministic: `started_at DESC, run_id DESC`; the endpoint exposes one newest run, not a run list.
- `active` is true only for `starting` and `running`. Persisted DB statuses remain `starting`, `running`, `completed`, and `failed`; `idle` is a response-only state used when no row exists.
- When no run exists, the response has a null `run_id` and timestamps, false `active`, status `idle`, and zero counters.
- The endpoint does not read or mutate `current_earthquakes`, `historical_2025`, or replay event data.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — verified Python 3.11 and Docker environment for container-based verification.
- `.github/modernize/rearchitecture/artifacts/t15-backend.md` — API model, asyncpg, route registration, and UTC serialization conventions.
- `.github/modernize/rearchitecture/artifacts/t16-backend.md` — replay persistence handoff and existing run lifecycle behavior.
- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — `/api/v1/replay/state` route and newest-run/active/status/timestamp response contract.
- `specs/001-observatorio-sismico/plan.md#6` and `acceptance-tests.md#TC-11` — replay UI/API behavior and isolated replay requirement.
- `backend/db/init.sql#replay_runs` — persisted run status, UTC timestamps, and event counters.
- `.github/modernize/rearchitecture/learnings/backend/{fastapi-utc-filtered-analytics.md,replay-run-scoped-persistence.md}` — UTC/scope-safe API practices and replay isolation.

`context.md`, `decisions.md`, and `team/backend/inbox.md` were not present. Existing architecture, schema, and task-dependency artifacts supplied the applicable decisions.

## Evidence Mapping

- `t3-architect.md#API Endpoints Inventory` and `#DTOs & Contracts` → the new router/DTO registered in `backend/api/main.py`; contract tests pass and a DB-backed HTTP probe returned 200 with the documented idle response.
- `t16-backend.md#Handoff / Remaining Scope` and `init.sql#replay_runs` → the route reads lifecycle state from the run registry only; tests cover running and completed status-to-active mapping.
- `t15-backend.md#API Contract and Naming Decisions` → immutable DTO and UTC `Z` timestamps; the focused tests assert exact JSON serialization.
- `plan.md#6` and `acceptance-tests.md#TC-11` → replay state is exposed without crossing into live event tables.

## Test Results

- Command: `docker compose --env-file .env.example run --build --rm --no-deps api python -m pytest -q tests/test_api_contract.py`
  - Passed: 10; Failed: 0; Skipped: 0.
  - One existing Starlette `BlockingPortal` deprecation warning was emitted.
- Command: `docker compose --env-file .env.example config --quiet`
  - Passed: exit 0.
- Command: `git diff --check`
  - Passed: exit 0.
- Runtime probe: `Invoke-WebRequest http://127.0.0.1:8000/api/v1/replay/state`
  - Passed: HTTP 200; PostgreSQL-backed empty registry returned `{"run_id":null,"active":false,"status":"idle","started_at":null,"finished_at":null,"events_received":0,"events_processed":0,"events_quarantined":0}`.

## Issues / Handoff

- The project task breakdown covers replay publishing in `TASK-7.2`; this assigned t18 API endpoint is additionally specified by the architect's endpoint inventory and plan §6.
- The complete acceptance suite and frontend replay badge remain assigned to downstream tasks.
