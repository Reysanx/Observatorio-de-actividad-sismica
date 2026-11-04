# t12 — Consumer quality and spatial event processing

## Summary

Implemented the live-event consumer pipeline: envelope and field validation, WGS84 Natural Earth indexing with Shapely STRtree, country-dimension seeding, offset-idempotent quarantine, strict-newer PostgreSQL UPSERT/versioning, poll-audit persistence, and manual Kafka commits after successful database transactions.

The consumer currently subscribes to `earthquakes.live`; replay-topic processing remains assigned to the later replay task. This task does not claim that the full local MVP, API, historical bootstrap, or replay is complete.

## Deliverables

- [t12-backend-batch-report.yaml](./t12-backend-batch-report.yaml) — task, changed-file, evidence, and test summary.
- [checkpoints/t12-tasks-to-impl.yaml](./checkpoints/t12-tasks-to-impl.yaml) — T005 traceability checkpoint.

## Source Files Changed

- `backend/consumer/__init__.py`
- `backend/consumer/quality.py`
- `backend/consumer/spatial.py`
- `backend/consumer/db_writer.py`
- `backend/consumer/main.py`
- `backend/requirements.txt`
- `backend/tests/test_consumer_quality.py`
- `backend/tests/test_consumer_spatial.py`
- `backend/tests/test_consumer_pipeline.py`
- `backend/tests/test_consumer_db.py`

## Processing and Naming Decisions

- Follow the canonical `earthquakes.live` topic and version-1 envelope (`event`, `poll_audit`, `payload`, `updated_ms`, `content_hash`); do not use older hyphenated topic examples.
- Match PostgreSQL's actual contract: use `raw_payload`, seed all Natural Earth countries into `dim_countries`, write accepted snapshots to `current_earthquakes` and `earthquake_versions`, and quarantine by `(source_topic, source_partition, source_offset)`.
- Preserve NULL and negative magnitudes/depths; quarantine malformed JSON, missing identifiers, invalid/non-finite/out-of-bounds coordinates, and inconsistent event metadata. Keep raw Kafka bytes for invalid JSON.
- Quarantine Kafka null-valued tombstones as JSON `null` so the schema's raw-data constraint is satisfied and the poison offset can be safely committed.
- Treat offshore coordinates as `N/A` / `Sin país asignado`; use strict polygon intersection and the lowest lexicographic `ADM0_A3` for shared-boundary matches. Use `NAME_ES` when present, otherwise `ADMIN`.
- Natural Earth contains an invalid USA polygon in this pinned dataset. The consumer repairs invalid polygon topology in memory with Shapely `make_valid` (discarding non-polygonal repair remnants); it does not modify the source GeoJSON or source properties.
- For a valid event, the database transaction first performs the strict-newer UPSERT; a version is appended only when `RETURNING` yields a row. Quarantine/audit writes are also transactional. The consumer commits only the current Kafka message's next offset after the database operation succeeds.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — Python 3.11/Docker readiness and activation assumptions.
- `.github/modernize/rearchitecture/artifacts/t8-devops.md` — consumer container command, environment, Natural Earth read-only mount, and service boundaries.
- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — canonical envelope/topic contract, country fallback/tie behavior, mode boundary, and DB-before-offset protocol.
- `.github/modernize/rearchitecture/artifacts/t10-dba.md` — actual SQL column names, foreign keys, versioning, and offset-keyed quarantine persistence contract.
- `.github/modernize/rearchitecture/artifacts/t11-frontend.md` — verified country asset path and Natural Earth source attributes.
- `.github/modernize/rearchitecture/artifacts/t6-teamlead-plan.md` — implementation task T005, requirement mapping, and test strategy.
- `specs/001-observatorio-sismico/{spec.md,plan.md,tasks.md,data-spec.md,acceptance-tests.md}` — FR-03–FR-06, data rules, plan item 2.2/T005, and TC-01–TC-08/TC-11.
- `.specify/memory/constitution.md`, `.agents/AGENTS.md`, `.agents/rules/{architecture_invariants.md,data_quality_rules.md}`, `.agents/subagents/03-geospatial-quality/AGENT.md`, and `.agents/skills/{implementing-code,kafka-idempotent-consumer,spatial-strtree-pipeline,sharing-learnings}/SKILL.md` — role, data, transaction, spatial, test, and handoff rules.

`context.md`, `decisions.md`, and `team/backend/inbox.md` were not present in the workflow directory. Canonical decisions were taken from t3/t8/t10 and the approved project specifications.

## Evidence Mapping

- `t3-architect.md#Versioned JSON envelope` → `backend/consumer/quality.py#validate_event` and `#validate_poll_audit`; producer envelope fixtures pass validation.
- `t3-architect.md#Processing and persistence boundaries` items 3–5 → `quality.py`, `spatial.py`, `db_writer.py`, and `main.py`; invalid coordinates quarantine, ocean/border lookups are deterministic, and the live smoke event is persisted before its Kafka offset advances.
- `t10-dba.md#Persistence Contract` → `db_writer.py#persist_live_event` and `#persist_quarantine`; PostgreSQL integration verifies equal/older revisions do not write versions and quarantine is idempotent by Kafka position.
- `t11-frontend.md#Summary` + `frontend/public/datos/ATTRIBUTION.md#Data notes` → `spatial.py` reads the supplied Natural Earth dataset, applies the `ADMIN` fallback, and preserves source properties.
- `spec.md#FR-03–FR-06`, `data-spec.md#2–4`, and `acceptance-tests.md#TC-02–TC-07` → unit, PostgreSQL, and Kafka-to-PostgreSQL smoke evidence below.
- `tasks.md#TASK-4.1–4.3` and `t6-teamlead-plan.md#T005` → this consumer implementation and the T005 checkpoint.

## Test Results

- Command: `docker compose -p t12-consumer-check --env-file .env.example run --build --rm --no-deps -e RUN_DB_INTEGRATION=1 consumidor python -m unittest discover -s tests -p "test_consumer_*.py" -v`
  - Passed: 22; Failed: 0; Skipped: 0.
  - Includes actual PostgreSQL 16.4 checks for strict-newer UPSERT/version count, quarantine idempotency, and null-tombstone persistence, plus validation, Natural Earth/STRtree, commit-order, and failure-path tests.
- Command: `docker compose --env-file .env.example run --build --rm --no-deps productor python -m unittest discover -s tests -p test_usgs_live_producer.py -v`
  - Passed: 9; Failed: 0; Skipped: 0. Producer regression check after extending the shared requirements.
- Runtime smoke: started an isolated `broker` + `almacenamiento` + latest `consumidor`; published a valid null-magnitude Chile event and an out-of-bounds event to `earthquakes.live`; queried PostgreSQL and verified `mag=NULL`, `adm0_a3=CHL` / `Chile`, and `INVALID_COORDINATES_OUT_OF_BOUNDS`. Kafka consumer-group offsets advanced to log-end with lag 0 on both used partitions.
- Command: `docker compose --env-file .env.example config --quiet` and an exact service-set assertion.
  - Passed: Compose configuration valid; exactly `productor`, `broker`, `consumidor`, `almacenamiento`, and `api`.
- Test aggregate: 31 passed, 0 failed, 0 skipped. The isolated test project and its containers/volumes were removed after verification.

## Handoff / Remaining Scope

- Replay-topic start/event/finish controls and run-scoped replay writes are not handled yet; the later replay task must add these routes without weakening the live boundary.
- Historical baseline download/import, FastAPI routes, frontend, and complete 11-case acceptance suite remain downstream work.
- The code stores `ingested_at`, source timestamps, hashes, and original payload for later freshness/audit analysis; it does not assert scientific ground truth or claim the non-runtime 6D exactness/academic analysis.
- No credentials, external publication, Netlify, or ngrok were used.
