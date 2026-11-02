# t6 — Focused Validation Strategy and Environment Evidence

## Validation Scope

Validate behavior required by the bounded local MVP and make every pass claim traceable to an executable command/report. Do not attempt Netlify/ngrok publication or infer academic completeness. Keep browser validation and container/infrastructure validation as separate capability axes.

## Critical Journeys and Acceptance Coverage

| Journey | Main cases | Required evidence |
|---|---|---|
| Live event arrives and becomes visible | TC-01 | Publish fixture with a new `event_id`; observe one live row, API event, map/table entry, and aggregates. |
| Idempotent current state and revisions | TC-02/03/04/08 | Re-send identical version, newer version, then stale version; verify one current event, newer data retained, versions traceable, and restart/replay does not duplicate. |
| Quality and geographic behavior | TC-05/06/07 | Null magnitude persists as SQL null and displays `ND`; invalid/non-finite coordinates persist with explicit reason/raw payload in quarantine; ocean event remains visible as `N/A` / `Sin país asignado`; valid negative measurements remain unchanged. |
| Historical comparison | FR-02/FR-07 | Exercise all 12 monthly UTC intervals, subdivision threshold, cache reuse, deduplication, import to monthly PostgreSQL partitions, and comparison denominator of 365 days. |
| Replay is isolated and observable | TC-11 | Publish a unique replay run; show `REPRODUCCIÓN`; query only its `run_id`; assert live rows, aggregates, and baseline are unchanged. |
| UI survives local API interruption | TC-09/10 adapted | Simulate API network failure after a successful load; preserve last values/time and show stale/disconnected state; restore response; verify automatic refresh and banner removal without reload. No ngrok process is started. |

## Test Tiers and Commands

1. **Static/config gate**
   - `docker compose config --services` must output exactly `productor`, `broker`, `consumidor`, `almacenamiento`, `api`.
   - `docker compose config` must show no host port mappings for 5432/9092 and API bound only to `127.0.0.1:8000`.
   - Inspect Compose graph and confirm five healthchecks; only actual edges use `condition: service_healthy`.

2. **Container startup and integration**
   - `docker compose up --build -d`; `docker compose ps`.
   - Require all five services healthy before acceptance tests. Run `docker compose exec -T api pytest -q tests/test_ingestion.py tests/test_api_contract.py tests/test_pipeline_acceptance.py`.
   - Use real PostgreSQL 16 and Kafka/KRaft. Validate DDL/partitions, consumer commit ordering, event/revision/quarantine writes, API reads, and replay isolation. Use mocked USGS responses to avoid rate limits and unstable external behavior.

3. **Browser E2E**
   - `npm --prefix frontend ci`; `npm --prefix frontend run build`; `npm --prefix frontend test`; `npm --prefix frontend run e2e`.
   - Use Playwright with Chromium against the local Angular app and API. Add Playwright tests for TC-01/05/07/09/10/11, including map/table detail, badge, filter state, stale-data banner, and automatic recovery.
   - On the outage journey, use a controllable network route/test fixture to fail and restore the local API request. This validates client behavior without stopping an external tunnel or using credentials.

4. **Per-module startup/health**
   - Compose healthchecks must verify PostgreSQL readiness, Kafka metadata/topic access, producer/consumer process plus their required connection, and API/DB readiness.
   - `GET http://127.0.0.1:8000/api/v1/health` must return the specified ready/freshness DTO. Probe each API route/validation path in the Python contract suite.

## Test Infrastructure and Data Rules

- `pytest` fixtures provide async DB connections, Kafka producer helpers, generated event IDs/run IDs, stubbed USGS HTTP, and cleanup. The Python acceptance suite must not rely on pre-existing live or historical data.
- Use actual PostgreSQL/Kafka for integration, not in-memory substitutes, when Docker is available. Tests should exercise the same topic routing and `updated_utc` conditions used by runtime code.
- Isolate writes with UUID/prefixed IDs and unique replay `run_id`; delete only those test rows in teardown. For tests that insert historical rows, use a fixture year/month and clean up its event-key registry and fact row consistently.
- Natural Earth is a deterministic checked-in public GeoJSON input with license/source attribution; tests use known interior, border, and ocean coordinates.
- Stub USGS HTTP in tests, including 429/5xx, timeout, malformed GeoJSON, and monthly boundary behavior; do not make test success depend on USGS uptime.
- The approved API is unauthenticated and local-only. Do not invent auth; test negative query validation and service-unavailable handling instead.
- Python modules require module-level unit tests in addition to the integration suite. At least three runnable test files should cover distinct flows: `tests/test_ingestion.py` for producer/history unit cases, `tests/test_pipeline_acceptance.py` for consumer/persistence integration, `tests/test_api_contract.py` for HTTP contracts; Playwright browser journeys live in `frontend/e2e/dashboard.spec.ts`.

## Fallback Matrix (Independent Capabilities)

| Axis | Primary | Prerequisite | If unavailable | Coverage gap |
|---|---|---|---|---|
| Infrastructure | Docker Compose with real PostgreSQL/Kafka | Functional Docker daemon | Keep unit/contract tests runnable with isolated substitutes, but escalate and do not claim end-to-end pipeline/database behavior. Restore Docker before final acceptance. | PostgreSQL DDL, monthly partitions, SQL upsert behavior, Kafka delivery/restarts, and DB-before-offset are not proven by substitute tests. |
| Browser | Playwright + Chromium | Node.js and browser installation | Framework/unit/HTTP tests may supplement only after a reproducible browser-install failure; escalate the specific prerequisite error. | No real browser rendering, navigation, or interaction evidence. |

Docker and browser tiers are independent. If Docker is down but Node/Playwright are available, still execute browser tests against a local or controlled API fixture. If Node/Playwright is unavailable but Docker is working, retain real backend integration tests. A failure in one axis never justifies skipping the other.

## Environment Evidence Captured for t6

- `Get-Command docker` found Docker CLI version `29.9.2`; Docker Compose plugin reports `v5.6.1`.
- `docker info` (exit code 1) reported: `failed to connect to the docker API at npipe:////./pipe/docker_engine ... The system cannot find the file specified.` **Docker daemon unavailable.**
- `node --version` → `v22.15.0` (available).
- `python --version` → `Python 3.15.0` (available on host; project backend target remains Python 3.11 container).
- Existing source/test baseline: no root or frontend `package.json`, no backend requirements manifest, and no test files beyond the acceptance-test specification. `backend/db/init.sql` is present from t4.
- Playwright/Chromium installation was not attempted because no Angular package has been scaffolded. Recheck and attempt it independently during browser-test execution.

## Validation Review and Handoff

The validation owner must record exact commands, exit codes, pass/fail/skip counts, test names on failure, container status, and any per-axis fallback evidence. A failed primary command is a failed tier regardless of partial test counts. If Docker remains unavailable, report the exact daemon error and leave PostgreSQL/Kafka integration unverified. If browser installation fails, report its exact command/output and the specific browser gap.

For the execution phase, route Docker/Compose to platform/devops; USGS downloader/live publisher to data-ingestion; quality/STRtree/transaction consumer to geospatial-quality; API/schema integration to backend-modeler; Angular dashboard to frontend-cartographer; acceptance tests to the designated tester/acceptance owner. Do not assign implementation to teamlead.
