# Runtime Validation Report

**Generated**: 2026-11-02T19:23:36Z
**Target**: `C:\Users\jasam\Desktop\BD&IA\Observatorio-de-actividad-s-smica`

## Summary

| Step | Status | Exit Code | Details |
|---|---:|---:|---|
| Startup | PASS | 0 | `docker compose --env-file .env.example up --build -d`; all five canonical services reported healthy. |
| Backend acceptance tests | PASS | 0 | 1 acceptance file; 6 passed, 0 failed, 0 skipped; real Kafka, PostgreSQL, and HTTP API. |
| Backend regression/integration suite | PASS | 0 | `RUN_DB_INTEGRATION=1`; 67 passed, 0 failed, 0 skipped; includes PostgreSQL integration tests. |
| Browser E2E | UNVERIFIED | n/a | Not part of t20 backend test scope; browser acceptance is assigned to t21 and final runtime validation to t28. |

**Overall**: NEEDS_SIGNOFF — backend acceptance and regression checks pass; actual consumer stop/start and browser journeys remain unverified in this task.

## Environment and Per-Capability Evidence

```text
environment:
  docker: AVAILABLE — `docker info` exited 0; Compose v5.6.1 / Engine 29.9.2 per t7.
  node: AVAILABLE — Node 22.15.0 per t7 environment preparation.
  playwright: AVAILABLE — Playwright 1.64.1 with Chromium per t7 environment preparation.
  infra-tier: PRIMARY(Docker-based) — real Compose Kafka and PostgreSQL; all five services healthy.
  browser-tier: SKIPPED — no fallback was used; browser scope remains assigned to t21/t28.
startup: PASS — `docker compose --env-file .env.example up --build -d`; readiness signal: all five Compose health checks healthy.
integration: PASS — exit_code: 0, passed: 67, failed: 0, skipped: 0; full backend suite, including PostgreSQL integration and Kafka-to-database acceptance flows.
e2e: UNVERIFIED — exit_code: n/a; TC-05 display, TC-09/10 outage/recovery, and TC-11 badge require the separate browser suite.
overall: NEEDS_SIGNOFF — backend scope is verified; browser and actual container-restart journeys are not claimed.
```

## Test Results

### Acceptance suite

- Command: `docker compose --env-file .env.example exec -T api pytest tests/test_acceptance.py -v`
- Exit code: `0`
- Passed: `6`
- Failed: `0`
- Skipped: `0`
- Scenarios: TC-01–TC-04 insert/idempotency/revision order; TC-05 nullable magnitude persistence/API response; TC-06 coordinate quarantine; TC-07 maritime assignment; TC-08 duplicate redelivery; TC-11 replay isolation and API scope.

### Complete backend test suite

- Command: `docker compose --env-file .env.example exec -T -e RUN_DB_INTEGRATION=1 consumidor python -m pytest -q tests`
- Exit code: `0`
- Passed: `67`
- Failed: `0`
- Skipped: `0`
- Warning: one existing Starlette `BlockingPortal` deprecation warning.

### Other checks

- `docker compose --env-file .env.example up --build -d` — exit `0`; `almacenamiento`, `api`, `broker`, `consumidor`, and `productor` all `running/healthy`.
- `git diff --check` — exit `0`; acceptance file contains no trailing-whitespace lines.

## Corrections During Test Development

- Initial acceptance run exposed a test synchronization issue: replay polling returned on the first `running` row before the finish control was processed. The wait condition was changed to require `status=completed` and the expected event count; the acceptance suite then passed.
- One exploratory full-suite invocation via the `pytest` executable did not resolve repository imports inside the container. The approved `python -m pytest` invocation was used instead and passed with all integration tests enabled.

## Coverage Gaps

- TC-08: verified same-message redelivery idempotency, but did not stop/start the consumer container as part of the test.
- TC-05 frontend label `ND`, TC-09/10 API-disconnection banner and automatic recovery, and TC-11 visual replay badge are browser responsibilities and were not exercised in this backend task.
- Acceptance fixtures did not call USGS; the Compose producer remained under its normal poll schedule. No Netlify/ngrok publication, external credentials, or academic deliverables were used.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — runtime/toolchain evidence.
- `.github/modernize/rearchitecture/artifacts/t8-devops.md` — Compose and network boundaries.
- `.github/modernize/rearchitecture/artifacts/t9-backend.md`, `t12-backend.md`, `t14-backend.md`, `t15-backend.md`, `t16-backend.md`, and `t18-backend.md` — event, persistence, API, and replay contracts.
- `.github/modernize/rearchitecture/artifacts/t2-pm.md` — approved local MVP scope.
- `.github/modernize/rearchitecture/artifacts/t6-teamlead-validation.md` — test strategy and isolation rules.
- `specs/001-observatorio-sismico/{spec.md,plan.md,tasks.md,data-spec.md,acceptance-tests.md}`, `.specify/memory/constitution.md`, and relevant `.agents/` rules, role, and skill files — acceptance behavior and architecture/data invariants.
- No workflow `context.md` or `decisions.md` existed.

## Evidence Mapping

- `t6-teamlead-validation.md#Critical Journeys` and `acceptance-tests.md#TC-01–TC-04` → live integration/revision/API test evidence above.
- `acceptance-tests.md#TC-05–TC-07` and `.agents/rules/data_quality_rules.md#1–3` → null preservation, quarantine, and ocean classification test evidence above.
- `acceptance-tests.md#TC-08` and `t12-backend.md#Processing and persistence` → idempotent redelivery evidence; restart itself remains a recorded gap.
- `acceptance-tests.md#TC-11` and `t16-backend.md#Naming and Behavior Decisions` → run-scoped persistence and API isolation evidence above.
- `t6-teamlead-validation.md#Fallback Matrix` → primary Docker infrastructure tier used; browser axis is deferred to its separately assigned task, not substituted with a fallback.
