# t15 — FastAPI Contracts and Analytics

## Status

API implementation is complete. Focused API tests, the complete backend suite in the consumer image, and DB-backed runtime probes pass.

## Deliverables

- `backend/api/` — asynchronous FastAPI application, pool lifecycle, immutable DTOs, filters, and health/event/statistics/comparison routes.
- `backend/tests/test_api_contract.py` — focused API contract tests.
- `backend/requirements.txt` — exact FastAPI/Pydantic/Uvicorn/Pytest dependency pins added to the shared backend image.
- [t15-backend-batch-report.yaml](./t15-backend-batch-report.yaml) — machine-readable traceability and test record.
- [checkpoints/t15-tasks-to-impl.yaml](./checkpoints/t15-tasks-to-impl.yaml) — T007 implementation checkpoint.

## API Contract and Naming Decisions

- Follow the canonical API paths: `/api/v1/health`, `/api/v1/earthquakes`, `/api/v1/stats/geo`, `/api/v1/stats/hourly`, `/api/v1/stats/distributions`, and `/api/v1/stats/historical-comparison`.
- Use the schema names `current_earthquakes`, `historical_2025`, `replay_earthquakes`, `dim_countries`, and `ingestion_audit`. Do not use the older `postgres` / `kafka` service aliases or the legacy hyphenated replay topic name.
- Default event and analytics reads to live data. Replay reads require both `scope=replay` and a non-empty `run_id`; a missing run is an empty replay result and never falls back to live data. The separate replay-state endpoint remains assigned to t18.
- Common filters are timezone-aware, UTC-normalized, and use inclusive `start_utc` / exclusive `end_utc`; omitted date filters default to the preceding 24 hours. Filter values are bound SQL parameters, and database relations are selected only from a fixed live/replay allowlist.
- Magnitude and depth nulls are not imputed. Histogram responses include explicit null counts; negative magnitude/depth bins use mathematical floor boundaries.
- The health freshness delay is calculated from `now - latest updated_utc`, matching the data-quality `Delta_pipe` definition; the latest persisted `ingested_at` is returned separately.
- Hourly aggregation truncates event occurrence time in UTC. Historical comparison is fixed to the latest 24 hours of live M4+ events versus all 2025 baseline M4+ rows divided by 365, returning a null ratio when the mean is zero.
- UTC response timestamps serialize with a `Z` suffix. CORS is restricted to configured origins and supports the `ngrok-skip-browser-warning` header; this task did not configure or use public ingress.

## Source Files Changed

- `backend/api/__init__.py`
- `backend/api/db.py`
- `backend/api/filters.py`
- `backend/api/main.py`
- `backend/api/models.py`
- `backend/api/routes/__init__.py`
- `backend/api/routes/comparison.py`
- `backend/api/routes/earthquakes.py`
- `backend/api/routes/health.py`
- `backend/api/routes/stats.py`
- `backend/requirements.txt`
- `backend/tests/test_api_contract.py`

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — canonical endpoint, DTO, filter, UTC, live/replay isolation, and historical-comparison contract.
- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — verified Python 3.11 and Docker environment.
- `.github/modernize/rearchitecture/artifacts/t8-devops.md` — API container, loopback binding, CORS environment, and five-service runtime.
- `.github/modernize/rearchitecture/artifacts/t10-dba.md` — actual PostgreSQL relation names, columns, country dimension, and baseline partition contract.
- `.github/modernize/rearchitecture/artifacts/t12-backend.md` — normalized live field names, country labels, and DB persistence semantics.
- `.github/modernize/rearchitecture/artifacts/t14-backend.md` — immutable baseline import and evidence of 18,302 2025 records.
- `specs/001-observatorio-sismico/{spec.md,plan.md,tasks.md,data-spec.md,acceptance-tests.md}` — FR-07, API filter/analytics requirements, Task 5 breakdown, UTC, null, and comparison rules.
- `.specify/memory/constitution.md` and `.agents/{AGENTS.md,rules/architecture_invariants.md,rules/data_quality_rules.md,subagents/04-backend-modeler/AGENT.md}` — service boundaries, API ownership, data integrity, and local-only scope.
- `.github/modernize/rearchitecture/learnings/backend/{consumer-quality-spatial-persistence.md,historical-2025-baseline.md,usgs-live-envelope-and-dedupe.md}` — persisted schema names, baseline/live distinction, and event field semantics.

`context.md`, `decisions.md`, and `team/backend/inbox.md` were not present in the workflow directory. Canonical decisions were taken from the architect and implementation dependency artifacts.

## Evidence Mapping

- `t3-architect.md#API Endpoints Inventory` and `#Common filters` → `backend/api/routes/*.py` and `backend/api/filters.py`; route probes returned 200, invalid date/range tests return 422, and replay queries require a run ID.
- `t3-architect.md#DTOs & Contracts` and `#Communication Patterns` → immutable Pydantic response models, UTC `Z` serialization, DB health/freshness fields, and local-origin CORS in `backend/api/models.py` / `main.py`; focused health and CORS tests pass.
- `t10-dba.md#Contract Verified` → API queries use the schema's actual `current_earthquakes`, `historical_2025`, `dim_countries`, and `ingestion_audit` columns; live PostgreSQL probes succeeded.
- `t14-backend.md#Test Results` → live historical comparison returned 18,302 baseline events and 365 comparison days using the preserved database volume.
- `spec.md#FR-07`, `tasks.md#TASK-5.1–5.5`, and `t6-teamlead-plan.md#T007` → health, filter/pagination, geographic/hourly/distribution analytics, comparison, and CORS were implemented and focused API tests pass.

## Test Results

- Command: `docker compose --env-file .env.example run --build --rm --no-deps api python -m pytest -q tests/test_api_contract.py`
  - Passed: 7; Failed: 0; Skipped: 0.
- Command: `docker compose --env-file .env.example run --build --rm --no-deps consumidor python -m pytest -q tests`
  - Passed: 52; Failed: 0; Skipped: 5.
  - The consumer image supplies the Natural Earth mount needed by the existing spatial unit tests. One Starlette deprecation warning from its TestClient was reported.
- Command: `docker compose --env-file .env.example run --build --rm --no-deps api python -m pytest -q tests`
  - Initial attempt: 48 passed; 4 setup errors; 5 skipped. The API-only image does not mount `frontend/public/datos/paises.geojson`, which the existing spatial tests require. This was an environment-selection issue; rerunning the whole suite in the consumer image passed as listed above.
  - Affected tests: `test_loads_natural_earth_and_finds_chile`, `test_ocean_point_is_not_assigned_to_nearest_country`, `test_rejects_non_wgs84_points`, and `test_shared_boundary_uses_lexicographically_smallest_code`; each failed during `SpatialIndex` setup because the GeoJSON path was absent.
- Runtime: started only `almacenamiento` and `api` using `docker compose --env-file .env.example up --build -d almacenamiento api`; both became healthy.
  - `GET /api/v1/health`, `/api/v1/earthquakes`, `/api/v1/stats/geo`, `/api/v1/stats/hourly`, `/api/v1/stats/distributions`, `/api/v1/stats/historical-comparison`, and `/openapi.json`: HTTP 200.
  - Filtered Chile geographic/hourly/replay reads and multi-filter historical comparison: HTTP 200.
  - CORS preflight from `http://localhost:4200` allowing `ngrok-skip-browser-warning`: passed.
  - Historical comparison observed 18,302 baseline rows and the fixed 365-day denominator; replay scope for an unknown run returned no live rows.
  - Measured runtime probes were 0.011–0.112 seconds in this local run.
  - The live current table had no event rows during this task's local validation, so health correctly returned null latest-live-event freshness fields; the producer was outside this task's runtime scope.
- Command: `docker compose --env-file .env.example config --quiet`; `git diff --check`; `python -m compileall -q /app/api /app/tests/test_api_contract.py` inside the API container.
  - Passed: all three checks.

## Handoff

Replay run-state exposure remains assigned to t18. This task implements run-scoped query behavior and intentionally does not add `/api/v1/replay/state`.

The local API and PostgreSQL services used for probes are running and healthy for downstream verification. No external credentials were used; Compose used only the local placeholder in `.env.example`. No Netlify/ngrok publication or academic deliverables are claimed.
