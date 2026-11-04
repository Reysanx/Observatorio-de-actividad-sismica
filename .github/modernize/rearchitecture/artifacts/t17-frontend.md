# t17 — Synchronized dashboard views

## Summary

Implemented the live dashboard's shared structured filters, synchronized map/event-page/analytics requests, magnitude and depth distributions, hourly UTC chart, geographic summary, comparison card, and searchable/sortable paginated event table. Table selection highlights the corresponding map marker. All dashboard data remains live-only; replay selection and its badge remain assigned to t19.

## Deliverables

- [t17-frontend-batch-report.yaml](./t17-frontend-batch-report.yaml) — task traceability, exact files, tests, and supplemental runtime evidence.
- [checkpoints/t17-tasks-to-impl.yaml](./checkpoints/t17-tasks-to-impl.yaml) — implementation checkpoint for `TASK-6.3`.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — Node 22.15.0 and local frontend validation environment.
- `.github/modernize/rearchitecture/artifacts/t13-frontend.md` — existing Angular/Leaflet shell, runtime API configuration, map component, and event DTO conventions.
- `.github/modernize/rearchitecture/artifacts/t13.1-devops.md` — patched frontend dependency set; no dependency changes were needed.
- `.github/modernize/rearchitecture/artifacts/t15-backend.md` — implemented route names, JSON DTOs, filter parameters, and fixed-live historical-comparison contract.
- `.github/modernize/rearchitecture/artifacts/t5-ux.md` — dashboard hierarchy, shared filter behavior, table/search scope, UTC labels, stale-data handling, and responsive/accessibility requirements.
- `specs/001-observatorio-sismico/{spec.md,plan.md,tasks.md,data-spec.md,acceptance-tests.md}` — FR-08, TASK-6.3, API data semantics, and acceptance criteria.
- `.specify/memory/constitution.md` and `.agents/{AGENTS.md,subagents/05-frontend-cartographer/AGENT.md,rules/architecture_invariants.md,rules/data_quality_rules.md,skills/acceptance-testing/SKILL.md}` — frontend ownership, local-only boundary, accessibility, `ND`, negative-value, and unassigned-country requirements.
- `.github/modernize/rearchitecture/learnings/frontend/{angular-leaflet-local-shell.md,natural-earth-data-provenance.md}` — Angular runtime/API conventions and preservation of the already-attributed local map asset.

`context.md`, `decisions.md`, and `team/frontend/inbox.md` were not present in the workflow directory. No project topology file or `*-fanout.md` artifact was supplied.

## Evidence Mapping

- `t7-devops.md#Target Environment Preparation` → `npm test` and `npm run build` executed with prepared Node.js 22.15.0; local app startup succeeded without changing packages.
- `t13-frontend.md#Summary` → existing runtime-configured Angular shell and Leaflet map were extended with typed dashboard requests and selection synchronization; country asset paths and attribution remain unchanged.
- `t13.1-devops.md#Test Results` → existing dependency lock was retained; final build and tests ran without dependency modifications or a new advisory remediation.
- `t5-ux.md#Shared filters` and `#Dashboard Query and Refresh Behavior` → `frontend/src/app/app.ts`, `app.html`, and `api/earthquake-api.service.ts`; browser validation confirmed invalid magnitude bounds are rejected, and a valid shared filter submits matching UTC range, negative magnitude, country, and live scope to events/geo/hourly/distributions. The comparison request contains only its supported geographic filter.
- `t5-ux.md#Main content` + `spec.md#FR-08` + `tasks.md#TASK-6.3` → `app.html` renders the existing Leaflet map beside distribution charts, hourly activity, historical comparison, country totals, and the event table; shared filters drive all supported views.
- `t5-ux.md#Map and Event Selection` → `map/earthquake-map.component.ts` emits marker selection and highlights/centers selected events; the table uses the same event ID and provides a keyboard-operable selection button.
- `t15-backend.md#API Contract and Naming Decisions` → `api/earthquake-api.service.ts` calls the canonical live endpoints and serializes common filters consistently; runtime probes returned HTTP 200 for health, events, geo, hourly, distributions, and historical comparison.
- `data-spec.md#1.1` + `data_quality_rules.md#1` + `acceptance-tests.md#TC-05` → `dashboard-utils.mjs`, table labels, charts, and map selection retain negative values and display null magnitude/depth as `ND`; helper tests cover negative filter values and explicit UTC conversion.
- `constitution.md#2.2` → no Compose service, public ingress, credential, or environment configuration was added or changed.

## Implementation Notes

- Applied filters are validated before any request is sent. The event page and all supported analytics are requested together; the screen replaces its last successful snapshot only when all responses succeed.
- `datetime-local` inputs are explicitly interpreted as UTC; they are not converted from the browser's local timezone.
- Search is intentionally limited to the rows on the loaded page and is labeled **Buscar en eventos cargados**. Server pagination remains available.
- The comparison API is fixed to live M4+ events over the latest 24 hours versus the 2025 daily mean; it accepts country/continent/subregion only. The UI states these fixed semantics and does not imply date, magnitude, or depth filters affect that card.
- API field names follow the implemented t15 models. `depth_km` remains nullable in the UI for safe display even though the current backend DTO defines it as numeric.

## Test Results

- Command: `Set-Location frontend; npm test`
  - Passed: 8; Failed: 0; Skipped: 0.
- Command: `Set-Location frontend; npm run build`
  - Passed: 1 production build; Failed: 0; Skipped: 0.
  - Non-blocking warnings: optional `lmdb` build cache unavailable, Leaflet CommonJS dependency, and `app.css` component-style budget is 7.44 kB against a 6 kB warning budget (below the 10 kB error budget).
- Runtime API probes: six dashboard endpoints returned HTTP 200.
- Local UI smoke: `GET /`, `/config.json`, and `/datos/paises.geojson` returned HTTP 200; browser showed connected state and an empty live-data state.
- Browser interaction checks: invalid `mag_min > mag_max` displays inline validation without replacing the existing view; applying a valid negative magnitude and country filter sent aligned query parameters to events and filterable analytics; 390 px viewport had no horizontal document overflow.
- The live API currently returns zero events. Real-data marker selection, non-empty chart rendering, and the API-failure/recovery state were not exercised in this task; browser acceptance tests remain downstream.
- The first Angular build caught a keydown callback variable shadowing an earthquake DTO; this was corrected before the final passing build. One attempted dev-server launch with an appended `--host` argument failed; the documented plain `npm start` script served the app successfully.

## Handoff / Risks

- No frontend/backend contract mismatch remains for the routes used here.
- `docker compose --env-file .env.example ps` reported only `almacenamiento` and `api` running/healthy (2/5). The frontend can reach the API, but `broker`, `productor`, and `consumidor` are not running, so pipeline ingestion must be recovered before full end-to-end validation.
- t19 owns replay scope selection and the persistent replay badge; this task intentionally does not request or blend replay data.
- The live feed is empty in the currently running API, so t21 should exercise map markers and `ND` with controlled acceptance fixtures.
