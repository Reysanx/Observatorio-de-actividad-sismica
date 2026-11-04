# t20 — Backend Acceptance Tests

## Summary

Added a runnable backend acceptance suite that publishes isolated live and replay fixtures through Kafka, verifies durable PostgreSQL outcomes, and checks API visibility and replay isolation. All five Compose services were healthy during the final run.

## Deliverables

- [backend/tests/test_acceptance.py](../../../../backend/tests/test_acceptance.py) — six asynchronous integration tests covering TC-01–TC-08 backend behavior and TC-11 replay isolation.
- [t20-tester-runtime-validation-report.md](./t20-tester-runtime-validation-report.md) — environment evidence, executed commands, coverage limits, and verdict.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — Python 3.11/Docker readiness and activation evidence.
- `.github/modernize/rearchitecture/artifacts/t8-devops.md` — five-service Compose topology, topic setup, and internal network boundary.
- `.github/modernize/rearchitecture/artifacts/t9-backend.md` — live event-envelope and topic contract.
- `.github/modernize/rearchitecture/artifacts/t12-backend.md` — consumer quality/quarantine behavior and DB-before-offset persistence.
- `.github/modernize/rearchitecture/artifacts/t14-backend.md` — baseline remains separate from live data.
- `.github/modernize/rearchitecture/artifacts/t15-backend.md` — API paths, filters, UTC representation, and default live scope.
- `.github/modernize/rearchitecture/artifacts/t16-backend.md` — replay topic/control records and run-scoped persistence.
- `.github/modernize/rearchitecture/artifacts/t18-backend.md` — replay state contract.
- `.github/modernize/rearchitecture/artifacts/t2-pm.md` — local-only acceptance scope and TC-09/10 translation to controlled API outage tests.
- `.github/modernize/rearchitecture/artifacts/t6-teamlead-validation.md` — approved integration stack, user journeys, fixture isolation, and validation gaps.
- `specs/001-observatorio-sismico/{spec.md,plan.md,tasks.md,data-spec.md,acceptance-tests.md}` — approved API, event, quality, replay, and TC-01–TC-11 behavior.
- `.specify/memory/constitution.md`, `.agents/AGENTS.md`, `.agents/rules/{architecture_invariants.md,data_quality_rules.md}`, `.agents/subagents/04-backend-modeler/AGENT.md`, and `.agents/skills/{acceptance-testing,kafka-idempotent-consumer,spatial-strtree-pipeline,usgs-ingestion}/SKILL.md` — service boundaries, valid data semantics, API contracts, and acceptance procedure.

`.github/modernize/rearchitecture/context.md`, `decisions.md`, `team/tester/log.md`, and `team/tester/inbox.md` were not present at task start. The teamlead-owned board was read-only and not modified.

## Evidence Mapping

- `acceptance-tests.md#TC-01–TC-04` and `t6-teamlead-validation.md#Critical Journeys` → `test_tc01_to_tc04_live_insert_idempotency_and_revision_order`; real Kafka publication, PostgreSQL current/version counts, and API read-back verify insert, duplicate, newer, and stale event revisions.
- `acceptance-tests.md#TC-05` and `data_quality_rules.md#1` → `test_tc05_null_magnitude_is_persisted_as_null`; SQL and API preserve JSON `null`. The UI `ND` label is not asserted here.
- `acceptance-tests.md#TC-06` and `data_quality_rules.md#3` → `test_tc06_out_of_bounds_coordinates_are_quarantined`; verifies quarantine reason and raw latitude from PostgreSQL.
- `acceptance-tests.md#TC-07` and `data_quality_rules.md#2` → `test_tc07_ocean_event_is_not_assigned_to_nearest_country`; verifies `N/A` / `Sin país asignado` in the database and API.
- `acceptance-tests.md#TC-08` and `t12-backend.md#Processing and persistence` → `test_tc08_duplicate_redelivery_does_not_duplicate_current_state`; verifies identical redelivery idempotency. It does not itself stop/restart the Compose consumer.
- `acceptance-tests.md#TC-11`, `t16-backend.md#Naming and Behavior Decisions`, and `t18-backend.md#Contract Decisions` → `test_tc11_replay_run_is_visible_but_never_enters_live_state`; verifies replay lifecycle, run-scoped API read, and absence from the live table/API.

## Test Results

- Startup: `docker compose --env-file .env.example up --build -d` — exit 0; all five services reported `running/healthy`.
- Acceptance suite: `docker compose --env-file .env.example exec -T api pytest tests/test_acceptance.py -v` — exit 0; **6 passed, 0 failed, 0 skipped**.
- Full backend suite with PostgreSQL integration enabled: `docker compose --env-file .env.example exec -T -e RUN_DB_INTEGRATION=1 consumidor python -m pytest -q tests` — exit 0; **67 passed, 0 failed, 0 skipped**. One existing Starlette `BlockingPortal` deprecation warning.
- `git diff --check` — exit 0; acceptance test file has no trailing whitespace.
- Acceptance fixtures made no direct USGS requests; the Compose producer remained under its normal poll schedule. No public deployment, Netlify, or ngrok was used.

## Findings and Remaining Scope

- No HIGH or CRITICAL backend defects found by this task.
- The TC-08 test verifies duplicate redelivery, not an actual stop/start of the consumer container. A direct restart scenario remains unverified here.
- TC-05 UI rendering as `ND`, TC-09/10 browser outage/recovery, and the visible replay badge remain frontend/browser validation scope (t21/t28).
- No academic performance, Big-O, TCO, or grading deliverable is claimed.
