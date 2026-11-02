# t6 — Implementation Plan and Task Breakdown

**Date:** 2026-11-02  
**Feature:** `001-observatorio-sismico`  
**Mode:** Brownfield rewrite from a specification-only workspace  
**Scope:** Bounded, local, end-to-end MVP

## Summary

Build and validate a local seismic-observatory MVP from the approved contracts. The backend consists of exactly five Compose services: `productor`, `broker`, `consumidor`, `almacenamiento`, and `api`. The frontend is a minimal Angular + Leaflet SPA run on the host for local use, not a sixth Compose service. Live and 2025 USGS data flow through Kafka; the consumer validates, quarantines, enriches with Natural Earth, and writes idempotently to PostgreSQL. FastAPI provides the live/replay-scoped data and analytics contracts; the dashboard presents map, statistics, connection status, and replay badge.

This plan does **not** publish to Netlify, use ngrok or credentials, or claim Big-O/benchmark/TCO/notebook/academic evidence. Those are outside the user's bounded MVP request.

## Technical Context

- **Backend:** Python 3.11 container images, `aiokafka`, `httpx`, Shapely STRtree, FastAPI/Uvicorn, `asyncpg`.
- **Persistence/messaging:** PostgreSQL 16 and Kafka/KRaft in the five-service Compose topology.
- **Frontend:** Minimal Angular starter + Leaflet. Select and pin an Angular release compatible with the available Node toolchain during scaffold; no UI library/design system is prescribed.
- **Data:** USGS live `all_day.geojson` every 60s; complete 2025 catalog with `mag >= 4`, twelve monthly half-open UTC requests and recursive half-month subdivision over 18,000 records. The existing DBA artifact provides monthly 2025 PostgreSQL partitions in `backend/db/init.sql`.
- **Country map:** Natural Earth Admin-0 GeoJSON at `https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson`; public-domain terms at `https://www.naturalearthdata.com/about/terms-of-use/`. Preserve source attributes and add the approved attribution. Use `NAME_ES` only if present; otherwise use `ADMIN` without claiming it is Spanish.
- **Canonical names:** Compose IDs/DNS are `productor`, `broker`, `consumidor`, `almacenamiento`, `api`; topics are `earthquakes.live` and `earthquakes.replay`; database identifiers are snake_case. Replay persists only in run-scoped replay relations and never contributes to live/baseline reads.
- **Timestamps and missing values:** UTC end-to-end; preserve absent magnitude as SQL/JSON null and show `ND`; negative magnitude/depth remain valid.
- **Networking/secrets:** Do not publish broker or PostgreSQL ports. Bind only the API to host loopback `127.0.0.1:8000`. Keep secrets out of Git; provide placeholders in `.env.example`.
- **Performance:** Preserve the specified `<250 ms` aggregate-response target as a measured acceptance goal; the plan is not evidence that it is met.

## Constitution Check

| Principle | Plan decision | Result |
|---|---|---|
| Exactly five isolated backend services | The Compose graph has only the five canonical service IDs; Angular runs on the host | PASS |
| Private Kafka/PostgreSQL and local API boundary | No host port for `broker`/`almacenamiento`; API binds to `127.0.0.1:8000`; no ngrok/Netlify | PASS |
| Health and dependency ordering | Healthcheck each service; use `service_healthy` only for `productor→broker`, `consumidor→broker+almacenamiento`, `api→almacenamiento`; no artificial root dependencies | PASS |
| Idempotency and at-least-once processing | Key events by `event_id`; write newer-only UPSERT and versions in a PostgreSQL transaction; commit Kafka offset only after DB commit | PASS |
| Sismological data integrity | Preserve NULL/`ND`, negative measurements, maritime `N/A`/`Sin país asignado`, and quarantine invalid coordinates/raw payloads | PASS |
| Replay separation | Separate topic, relations, `run_id` scope, API query scope, and persistent `REPRODUCCIÓN` UI indicator | PASS |
| Reproducibility/secrets | Pin dependencies; document local commands; `.env.example` contains placeholders; ignore `.env` | PASS |

## Applied Guidelines

- No matching technology-to-technology migration guideline applies: this is a specification-led first implementation, not a framework migration. Follow the project-specific architecture, data-quality, USGS, STRtree, consumer-idempotency, and acceptance-testing guidance listed in the consumed artifacts.

## Implementation Steps

### Phase 1 — Setup and foundational infrastructure

#### Plan 1.1 — Secure five-service local runtime
- **Requirements:** NFR-02, NFR-03, NFR-04
- **Design inputs:** `t1-teamlead.md#Canonical Decisions`, `t2-pm.md#Scope Baseline`, `t3-architect.md#Service Catalog`, `t3.1-teamlead.md#Decision`, `.agents/rules/architecture_invariants.md`
- **Description:** Build one Compose file with exactly the five canonical services, private service networking, healthchecks, genuine health-gated dependencies, restart policies, and local API loopback binding. Include service Dockerfiles, `.env.example`, and `.gitignore`; keep frontend outside Compose.

#### Plan 1.2 — Use the PostgreSQL 16 schema and verify partition/idempotency contracts
- **Requirements:** FR-04, FR-05, FR-06, FR-09, NFR-04
- **Design inputs:** `t4-dba.md#Schema and Naming Decisions`, `#Persistence Contract`, `t3-architect.md#Processing and persistence boundaries`
- **Description:** Preserve and integrate the already-produced `backend/db/init.sql`. Verify its live/current, version, quarantine, audit, country, baseline, and replay relations; 2025 monthly baseline partitions; UTC/null/negative-value constraints; replay relations; and strict-newer persistence contract. Do not recreate the DDL or add a sixth service.

#### Plan 1.3 — Source and attribute Natural Earth countries
- **Requirements:** FR-03, FR-08, FR-09
- **Design inputs:** `t1-teamlead.md#Country boundaries and attribution`, `t3-architect.md#Decisions and Naming` item 7, `data-spec.md#1.3`
- **Description:** Download the approved public Natural Earth Admin-0 GeoJSON to `frontend/public/datos/paises.geojson`; record the exact source URL, public-domain terms URL, and suggested attribution in `frontend/public/datos/README.md`. Preserve source fields; make the display-name fallback explicit and do not invent `NAME_ES`.

### Phase 2 — User Story 1: Correct ingestion and persistence

#### Plan 2.1 — Ingest and publish the rolling USGS live feed
- **Requirements:** FR-01, FR-06, NFR-01, NFR-02
- **Design inputs:** `data-spec.md#1.1`, `.agents/skills/usgs-ingestion/SKILL.md`, `t3-architect.md#Event record`
- **Description:** Poll USGS every 60 seconds, retain only `earthquake` events, attach the versioned UTC envelope and poll audit record, retry boundedly on 429/5xx/network errors, and publish keyed/acknowledged messages to `earthquakes.live`.

#### Plan 2.2 — Validate, quarantine, spatially enrich, and persist events
- **Requirements:** FR-03, FR-04, FR-05, FR-06, NFR-02
- **Design inputs:** `t3-architect.md#Processing and persistence boundaries`, `t4-dba.md#Persistence Contract`, `.agents/skills/{spatial-strtree-pipeline,kafka-idempotent-consumer}/SKILL.md`, `data_quality_rules.md`
- **Description:** Consume with manual offset commits; validate envelope, finite/ranged coordinates and timestamps; preserve null/negative measurements; quarantine malformed or invalid source payloads; use WGS84 STRtree matching with deterministic boundary tie-break and maritime fallback; write live event, accepted version, and audit/quarantine outcome transactionally; commit Kafka only after PostgreSQL commits.

### Phase 3 — User Story 2: Historical baseline and queryable analytics

#### Plan 3.1 — Cache, partition, and import the 2025 catalog
- **Requirements:** FR-02, FR-03, FR-05, FR-07, NFR-04
- **Design inputs:** `data-spec.md#1.2`, `.agents/skills/usgs-ingestion/SKILL.md`, `t4-dba.md#Schema and Naming Decisions`, `t3-architect.md#Processing and persistence boundaries`
- **Description:** Download 2025 `mag >= 4` events using twelve half-open monthly UTC intervals, split intervals above 18,000 records, deduplicate boundary event IDs, cache reusable month files on a named volume, and import idempotently into the existing monthly `historical_2025` partitions through consumer-owned code. Never add baseline rows to live current state.

#### Plan 3.2 — Implement the FastAPI contracts and analytics
- **Requirements:** FR-07, NFR-01, NFR-03
- **Design inputs:** `t3-architect.md#API Endpoints Inventory`, `#DTOs & Contracts`, `t4-dba.md#Schema and Naming Decisions`
- **Description:** Implement health/freshness, filtered and paginated earthquakes, geo, hourly UTC, distributions, and 2025 comparison endpoints with documented DTOs, validation, CORS for local Angular, and live-only comparison. Preserve null counts and include unassigned-country results. Return errors for invalid ranges rather than silently relaxing filters.

### Phase 4 — User Story 3: Map and analysis dashboard

#### Plan 4.1 — Create the minimal Angular/Leaflet map shell
- **Requirements:** FR-03, FR-08, NFR-03, NFR-04
- **Design inputs:** `t5-ux.md#Product Decisions`, `#Map and Event Selection`, `t3-architect.md#Decisions and Naming` items 1, 7, 8
- **Description:** Scaffold a minimal Angular app; load `apiUrl` from runtime config for local API access; render the Natural Earth country context, credited source, event circles and accessible event detail; display null values as `ND` and maritime events as `Sin país asignado`.

#### Plan 4.2 — Build synchronized dashboard views and failure retention
- **Requirements:** FR-07, FR-08, NFR-01, NFR-02
- **Design inputs:** `t5-ux.md#Screen and Information Hierarchy`, `#Shared filters`, `#Connection, Loading, and Empty States`
- **Description:** Add the shared UTC/date/magnitude/depth/country filters; event count, table, geo/hourly/distribution charts, live-only historical comparison card, refresh/freshness status, accessible responsive states, and stale-data retention/automatic recovery on API failure.

### Phase 5 — User Story 4: Isolated historical replay

#### Plan 5.1 — Publish and persist run-scoped replay events
- **Requirements:** FR-04, FR-06, FR-09
- **Design inputs:** `t3-architect.md#Decisions and Naming` items 2–6, `#Processing and persistence boundaries`, `t4-dba.md#Schema and Naming Decisions`, `acceptance-tests.md#TC-11`
- **Description:** Replay cached 2025 events in deterministic time order through `earthquakes.replay`, emit start/finish controls and controlled duplicate/revision/maritime examples, and persist solely to run-scoped replay tables. Every event/revision is keyed by `run_id`; live/current and historical baseline remain unchanged.

#### Plan 5.2 — Expose and visualize replay state safely
- **Requirements:** FR-07, FR-08, FR-09
- **Design inputs:** `t3-architect.md#API Endpoints Inventory`, `t5-ux.md#Header and status`, `#Product Decisions`
- **Description:** Expose replay-state and explicit replay query scope requiring `run_id`; keep missing/failed replay-state distinct from “no replay”; show the persistent `REPRODUCCIÓN` badge and never mix replay with live filters, counts, or historical comparison.

### Phase 6 — Acceptance, local run guide, and completion evidence

#### Plan 6.1 — Add deterministic integration and browser acceptance tests
- **Requirements:** FR-01–FR-09, NFR-01–NFR-04
- **Design inputs:** `acceptance-tests.md#TC-01–TC-11`, `t6-teamlead-validation.md`, `.agents/skills/acceptance-testing/SKILL.md`
- **Description:** Create Python tests for data/consumer/API and Playwright tests for UI flows. Use actual PostgreSQL/Kafka in integration tests; stub USGS HTTP; run browser tests independently of Docker availability when necessary. Adapt TC-09/10 to simulated local API outage/recovery and make no ngrok attempt.

#### Plan 6.2 — Document reproducible local execution and scope limits
- **Requirements:** NFR-02, NFR-03, NFR-04
- **Design inputs:** `t2-pm.md#Scope Baseline`, `t3-architect.md#Risks and Handoff`, `.agents/AGENTS.md`
- **Description:** Update `README.md` with prerequisites, `.env.example` setup, Compose startup/health checks, historical bootstrap, local Angular startup, replay procedure, tests, shutdown/cleanup, Natural Earth credit, and explicit no-publication/no-academic-claim boundaries. Commands must match actual scripts and existing service IDs.

## Task Breakdown

Tasks are listed in dependency order. `[P]` marks tasks that may run in parallel after their stated prerequisites; execute each task with a single accountable technical role/session. No project topology exists, so G-group labels are not applicable.

### Phase 1 — Setup and foundational tasks

- [ ] T001 [Plan:1.1] Create `compose.yaml`, `backend/Dockerfile.producer`, `backend/Dockerfile.consumer`, `backend/Dockerfile.api`, `.env.example`, and `.gitignore`; define exactly the five canonical services, healthchecks, real dependency edges, private Kafka/PostgreSQL, and API loopback binding.
- [ ] T002 [P] [Plan:1.2] Verify and integrate existing `backend/db/init.sql`; test all required relations, 12 monthly historical partitions, replay isolation, UTC/null/negative rules, and documented strict-newer transaction protocol without rewriting the DBA-owned schema.
- [ ] T003 [P] [Plan:1.3] Add `frontend/public/datos/paises.geojson` from the approved Natural Earth URL and `frontend/public/datos/README.md` with source URL, public-domain terms, attribution, and the `NAME_ES`/`ADMIN` display fallback.

### Phase 2 — User Story 1: Live ingestion and correct persistence

- [ ] T004 [US1] [Plan:2.1] Implement `backend/producer/usgs_client.py`, `backend/producer/main.py`, and `backend/producer/envelope.py` for the 60-second USGS live poll, type filter, audit/envelope, bounded retry, Kafka key/ack, and `earthquakes.live`; depends on T001.
- [ ] T005 [US1] [Plan:2.2] Implement `backend/consumer/quality.py`, `backend/consumer/spatial.py`, `backend/consumer/db_writer.py`, and `backend/consumer/main.py` for validation/quarantine, STRtree enrichment, strictly-newer UPSERT/versioning, and DB-then-offset commit; depends on T001–T003.

### Phase 3 — User Story 2: Historical baseline and API analytics

- [ ] T006 [US2] [Plan:3.1] Implement `backend/scripts/download_historical_2025.py` and `backend/consumer/bootstrap_historical.py` for all 12 monthly UTC slices, >18,000 recursive subdivision, boundary deduplication, reusable cache, and idempotent imports into the monthly `historical_2025` partitions; depends on T001–T005.
- [ ] T007 [P] [US2] [Plan:3.2] Implement `backend/api/main.py`, `backend/api/db.py`, and `backend/api/routes/{health,earthquakes,stats,comparison}.py` for the architecture's API/DTO contracts, filters, UTC buckets, distributions, 365-day 2025 mean, and loopback-local CORS; depends on T001–T002 and T005–T006.

### Phase 4 — User Story 3: Angular map and dashboard

- [ ] T008 [P] [US3] [Plan:4.1] Scaffold `frontend/` as a minimal Angular app, pin a compatible Angular/toolchain version in `frontend/package-lock.json`, add runtime config loading, Leaflet country/event map, accessible detail view, `ND`, maritime label, and Natural Earth credit; may proceed against the approved API DTO contract after T003.
- [ ] T009 [US3] [Plan:4.2] Implement shared filters, map/table/chart synchronization, live-only comparison, UTC freshness/status, responsive/accessibility behaviors, and retained-data connection banner in `frontend/src/app/`; depends on T007–T008.

### Phase 5 — User Story 4: Isolated replay

- [ ] T010 [US4] [Plan:5.1] Implement `backend/scripts/replay_producer.py` and consumer replay routing in `backend/consumer/` for ordered start/event/finish controls on `earthquakes.replay`, unique run IDs, and replay-only writes; depends on T005–T006.
- [ ] T011 [US4] [Plan:5.2] Implement `/api/v1/replay/state`, required `run_id` replay query behavior, and Angular replay selection/badge/failure retention in `backend/api/routes/replay.py` and `frontend/src/app/`; depends on T007–T010.

### Phase 6 — Acceptance and local run guidance

- [ ] T012 [Cross-cutting] [Plan:6.1] Add `tests/test_ingestion.py`, `tests/test_pipeline_acceptance.py`, and `tests/test_api_contract.py` with deterministic fixtures for USGS/history, TC-01–08/11, partitions, response contracts, and replay/live isolation; wire `pytest` into the backend test image/command; depends on T004–T007 and T010–T011.
- [ ] T013 [Cross-cutting] [Plan:6.1] Add `frontend/e2e/dashboard.spec.ts`, Playwright configuration, and `build`, `test`, and `e2e` scripts in `frontend/package.json`; cover map/dashboard, `ND`, maritime labels, replay badge/isolation, and local API loss/recovery with retained data; depends on T008–T011.
- [ ] T014 [Plan:6.2] Update `README.md` with reproducible local setup, historical bootstrap, service health checks, UI startup, replay, test commands, secrets policy, attribution, cleanup, and non-goals; verify every command against the final scripts and canonical service IDs; depends on T001–T013.

## Project Structure

```text
compose.yaml
.env.example
.gitignore
README.md
backend/
  Dockerfile.api
  Dockerfile.consumer
  Dockerfile.producer
  requirements.txt
  db/init.sql                         # existing t4 DBA deliverable
  producer/{main.py,usgs_client.py,envelope.py}
  consumer/{main.py,quality.py,spatial.py,db_writer.py,bootstrap_historical.py}
  api/{main.py,db.py,routes/}
  scripts/{download_historical_2025.py,replay_producer.py}
frontend/
  package.json
  package-lock.json
  public/config.json
  public/datos/paises.geojson
  public/datos/README.md
  src/app/
  e2e/dashboard.spec.ts
tests/
  test_pipeline_acceptance.py
  test_api_contract.py
```

## Testing Strategy

- **appType:** Event-driven messaging + FastAPI REST API + Angular SPA (mixed/browser application).
- **Critical user journeys:** (1) new live event → Kafka → PostgreSQL → API/map; (2) duplicate/newer/stale versions maintain an idempotent current view; (3) invalid coordinates quarantine while null/negative values and maritime events retain their meanings; (4) historical 2025 baseline powers the 365-day comparison; (5) replay run shows `REPRODUCCIÓN` while live metrics remain unchanged and the UI retains data through API loss/recovery.
- **primaryValidationStack:** Docker Compose with real PostgreSQL/Kafka; Python `pytest` unit + integration/API contracts; Playwright browser E2E against the local Angular/API; USGS HTTP stub for deterministic source tests. Keep DB/infrastructure and browser capabilities independent.
- **fallbackMatrix:**
  - `infra-tier`: Compose-managed PostgreSQL 16 + Kafka/KRaft (Docker prerequisite) → isolated in-memory tests/stubs for component logic only if Docker cannot be restored. Do not report partitioning, SQL UPSERT, broker offset ordering, or full pipeline integration as passed under this fallback.
  - `browser-tier`: Playwright against the running local app (Node.js + installed Chromium prerequisite) → framework/component HTTP tests only if Node/Playwright installation is unavailable; this loses actual browser rendering and interaction evidence. Docker unavailability alone does not justify skipping Playwright.
- **Environment requirements:** Docker Engine/Desktop and Compose; PostgreSQL/Kafka images; Python 3.11 container; Node compatible with pinned Angular; `npx playwright install chromium`; loopback ports 8000/4200; outbound HTTPS only during one-time source/browser installation. Acceptance tests stub USGS and do not require external service availability.
- **knownGaps:** Docker is unavailable in the current planning shell, so full infra integration is blocked until provisioned. Node is available (`v22.15.0`), but Playwright/browser installation has not been attempted. No authentication is specified by the approved local API contract; test invalid query rejection (422), not an invented auth flow. TC-09/10 simulate API outage/recovery locally; tunnel-specific behavior is out of scope.
- **Test data strategy:** Seed deterministic UTC fixtures with unique UUID/prefixed event IDs and replay `run_id`; exercise repeat/newer/stale versions; cleanup only test-scoped rows/runs in teardown. Never assume external USGS or preloaded live events. Use stubbed USGS HTTP and checked-in Natural Earth source data.
- **Acceptance criteria:** Every endpoint in t3 contract returns its expected status/schema; event insert/duplicate/revision/quarantine/maritime behavior matches TC-01–08; historical partitions cover all 2025 months and import deduplicates; replay queries require a run ID and do not change live/baseline data; browser shows expected map/dashboard/`ND`/status/badge and preserves last valid data after simulated API loss; all invoked test commands exit 0.
- **Test infrastructure:** Real PostgreSQL/Kafka in Compose for pipeline integration; `pytest` fixtures for IDs, connections, cleanup, stubbed USGS responses, and contract assertions; per-module startup checks via each Compose healthcheck and API health route; Playwright config for local Angular. Keep tests runnable without manual database/topic setup by using schema/topic bootstrap and test fixtures.
- **Canonical commands to create and run:** `docker compose config --services`; `docker compose up --build -d`; `docker compose ps`; `docker compose exec -T api pytest -q tests/test_api_contract.py tests/test_pipeline_acceptance.py`; `npm --prefix frontend ci`; `npm --prefix frontend run build`; `npm --prefix frontend test`; `npm --prefix frontend run e2e`. The root currently has no canonical test command, so the implementation must wire these project scripts and document them.
- **Validation review expectations:** Confirm five services only, no published DB/broker port, API loopback binding, all five healthchecks and only real dependency edges, exact topic/table naming, every acceptance case mapped to runnable evidence, per-axis fallback evidence, test command exit codes/counts, and no publication/secret/academic-deliverable claims.

## Requirement Mapping

| Requirement | Description | Plan items | Implementation evidence |
|---|---|---|---|
| FR-01 | USGS live feed every 60 seconds, filter earthquake type, record metadata | 2.1 | `backend/producer/{usgs_client.py,main.py,envelope.py}`, live-ingestion tests |
| FR-02 | Complete cached 2025 catalog, monthly and subdivided requests, deduplication | 3.1 | `backend/scripts/download_historical_2025.py`, cache/import tests |
| FR-03 | Natural Earth WGS84 country enrichment, maritime and boundary rules | 1.3, 2.2, 4.1 | GeoJSON attribution, `backend/consumer/spatial.py`, map tests |
| FR-04 | Strictly newer revisions and version history | 1.2, 2.2, 5.1 | `backend/db/init.sql`, `backend/consumer/db_writer.py`, revision tests |
| FR-05 | 6D data rules, quarantine, NULL/negative semantics | 1.2, 2.2, 4.1 | `backend/consumer/quality.py`, quarantine/`ND` tests |
| FR-06 | Keyed at-least-once transport, idempotency, DB-before-offset | 1.2, 2.1, 2.2, 5.1 | producer/consumer, SQL transaction, duplicate/restart tests |
| FR-07 | FastAPI contracts, filters, analytics, historical comparison | 3.1, 3.2, 5.2 | `backend/api/routes/`, `tests/test_api_contract.py` |
| FR-08 | Angular interactive map/dashboard and status handling | 1.3, 4.1, 4.2, 5.2 | `frontend/src/app/`, `frontend/e2e/dashboard.spec.ts` |
| FR-09 | Historical replay and clear replay-only UI state | 1.2, 5.1, 5.2 | replay relations/topic/API, `REPRODUCCIÓN` E2E |
| NFR-01 | Query and batch latency targets | 2.1, 3.2, 4.2, 6.1 | measured API/poll test evidence |
| NFR-02 | Healthchecks, restart, source retry/failure resilience | 1.1, 2.1, 2.2, 4.2, 6.1 | Compose health status, retry and outage/recovery tests |
| NFR-03 | Private broker/database, local API, no secrets | 1.1, 3.2, 4.1, 6.2 | Compose port/bind inspection, `.env.example`, CORS and README checks |
| NFR-04 | Reproducible, dependency-pinned local system | 1.1, 3.1, 4.1, 6.2 | lock/requirements files, documented build/bootstrap commands |

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t2-pm.md` — behavioral scope, non-goals, canonical names, acceptance evidence.
- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — architecture, API contracts, event envelope, replay tables and run scope.
- `.github/modernize/rearchitecture/artifacts/t4-dba.md` — delivered DDL, partition model, idempotency protocol.
- `.github/modernize/rearchitecture/artifacts/t5-ux.md` — UI states and local-only outage/recovery behavior.
- `specs/001-observatorio-sismico/{spec.md,plan.md,tasks.md,data-spec.md,acceptance-tests.md}` — original requirements, stack, and acceptance source.
- `.specify/memory/constitution.md`, `.agents/AGENTS.md`, `.agents/rules/*`, relevant `.agents/subagents/*/AGENT.md`, `.agents/skills/{acceptance-testing,kafka-idempotent-consumer,spatial-strtree-pipeline,usgs-ingestion}/SKILL.md` — project constraints and implementation/test expectations.
- `.github/modernize/rearchitecture/artifacts/t1-teamlead.md` and `t3.1-teamlead.md` — approved clarification decisions and service health policy.

## Evidence Mapping

- `spec.md#FR-01–FR-09` → plan items 1.2–5.2; exact mappings in `Requirement Mapping` and `checkpoints/t6-spec-to-plan.yaml`.
- `spec.md#NFR-01–NFR-04` → plan items 1.1, 2.1, 3.2, 4.2, 6.1–6.2; exact mappings in the checkpoint.
- `t3-architect.md#Decisions and Naming` + `t4-dba.md#Schema and Naming Decisions` → task T002/T005/T010 canonical services, topics, relations, and isolated replay.
- `acceptance-tests.md#TC-01–TC-11` + `t5-ux.md#Acceptance Mapping for Frontend Verification` → plan 6.1 and the focused test cases in `t6-teamlead-validation.md`.

## Test Results

- Command: PowerShell inline Python traceability assertions; `docker info`; `node --version`; `python --version`.
- Passed: 13/13 requirements mapped; 13/13 plan items mapped; 14/14 tasks trace to plan items; artifact links and structural indentation checks passed.
- Failed: No application-test failures (application tests are not available). `docker info` exited 1 because the Docker Engine named pipe is missing. A PyYAML parse could not be run: `python -m pip install PyYAML` exited 1 because a Python 3.15 native build requires unavailable Microsoft C++ Build Tools.
- Skipped: Application tests, Compose validation, and Playwright installation/run; reserved for execution/validation tasks.

## Decisions and Open Constraints

- Use dotted `earthquakes.replay`, not hyphenated `earthquakes-replay`; preserve canonical service IDs and database snake_case names.
- Replay persistence is isolated in `replay_runs`, `replay_earthquakes`, `replay_versions`, and `replay_quarantine_events`; queries for replay require a `run_id`.
- The baseline is not live state. Historical downloads use monthly intervals; persistence uses the existing monthly partitions.
- Natural Earth data is public domain per official terms; record the source and attribution with the checked-in GeoJSON and use `ADMIN` when `NAME_ES` is absent.
- Local API loss/recovery replaces ngrok-specific TC-09/10 execution; no publication is attempted.
- `.github/modernize/rearchitecture/context.md`, `decisions.md`, project topology, `package.json`, and canonical test scripts do not exist. The available PM/architect/DBA/UX artifacts provide the required design inputs; no topology groups apply.
- Current Docker daemon absence is an execution blocker for container integration evidence. It does not change the required primary test stack or authorize a false pass.
