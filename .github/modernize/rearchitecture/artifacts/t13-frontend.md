# t13 — Minimal Angular map shell

## Summary

Created the local Angular/Leaflet map shell with runtime API configuration, live event/health polling, stale-data notices, Natural Earth country boundaries, depth-colored event markers, UTC detail popups, and map attribution. Replay controls, filters, charts, and the synchronized dashboard remain downstream frontend tasks.

## Deliverables

- [t13-frontend-batch-report.yaml](./t13-frontend-batch-report.yaml) — exact source changes, traceability, test commands/results, and known handoff items.
- [checkpoints/t13-tasks-to-impl.yaml](./checkpoints/t13-tasks-to-impl.yaml) — implementation checkpoint for TASK-6.1 and TASK-6.2.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — Node 22.15/npm toolchain and local browser-validation assumptions.
- `.github/modernize/rearchitecture/artifacts/t8-devops.md` — frontend stays outside Compose; API is loopback-only and backend remains exactly five services.
- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — canonical API routes, local scope, live-only default, and response semantics.
- `.github/modernize/rearchitecture/artifacts/t5-ux.md` — Spanish labels, UTC, `ND`, stale-data behavior, marker colors, and Natural Earth attribution.
- `.github/modernize/rearchitecture/artifacts/t11-frontend.md` — country asset path, data provenance, and license details.
- `.github/modernize/rearchitecture/artifacts/t13.1-devops.md` — patched frontend dependency set and clean advisory scan.
- `specs/001-observatorio-sismico/{spec.md,plan.md,tasks.md,data-spec.md,acceptance-tests.md}` — FR-08, TASK-6.1–6.2, map/data contracts, and acceptance expectations.
- `.specify/memory/constitution.md` and `.agents/{AGENTS.md,subagents/05-frontend-cartographer/AGENT.md,rules/architecture_invariants.md,rules/data_quality_rules.md,skills/acceptance-testing/SKILL.md}` — role, local-only, accessibility, and data-quality constraints.

## Evidence Mapping

- `t3-architect.md#API Endpoints Inventory` → `frontend/src/app/api/earthquake-api.service.ts` requests `/api/v1/earthquakes` with explicit `scope=live` and `/api/v1/health`; page/event field spellings are recorded in the t13 batch report and were sent to backend for alignment.
- `t5-ux.md#Header and status` + `#Connection, Loading, and Empty States` → `frontend/src/app/app.ts` and `app.html` poll health every 15 seconds and events every 60 seconds, preserve the last successful event response, and display connection/error state.
- `t5-ux.md#Map and Event Selection` + `spec.md#FR-08` + `acceptance-tests.md#TC-05` → Leaflet event circles/popup values, UTC labels, keyboard-operable marker paths, and `ND` for null magnitude/depth; three focused helper tests pass.
- `spec.md#FR-08` + `data-spec.md#1.3` + `t11-frontend.md#Source and Naming Resolution` → country polygons load from `/datos/paises.geojson`; the built asset and attribution are present and the source checksum matches.
- `t3-architect.md#Decisions` items 1 and 8 + `t8-devops.md#Security posture` → dev server defaults to localhost and runtime API config uses `http://127.0.0.1:8000`; no Compose service or public deployment was added.
- `t13.1-devops.md#Test Results` → fresh `npm ci`, `npm audit`, frontend tests, and Angular production build pass with zero reported vulnerabilities.
- `t3-architect.md#API Endpoints Inventory` + observed `/api/v1/health` response → `HealthResponse` consumes `last_event_ingested_at`; this replaces the earlier guessed `latest_live_event_ingestion_utc` key.

## Test Results

- `npm test` — **3 passed, 0 failed, 0 skipped** (ND formatting, negative values, marker-size clamp, and depth-band boundaries).
- `npm run build` — **passed**; Angular production bundle generated. Non-blocking warnings: optional `lmdb` build cache unavailable and Leaflet is CommonJS.
- `curl.exe` probes for `http://localhost:4200/`, `/config.json`, and `/datos/paises.geojson` — **3/3 returned HTTP 200**.
- `npx --yes playwright@1.64.1 screenshot --browser chromium --wait-for-timeout=3000 http://localhost:4200/ ...` — **passed**; inspected screenshot showed the country map, attribution, and backend-unavailable state.
- Build output contained `config.json`, `datos/paises.geojson`, and `datos/ATTRIBUTION.md`; built and source GeoJSON SHA-256 values matched.

The clean recheck found both live API routes responding successfully. The current live response contains zero events, so non-empty marker rendering and popups remain unverified; the browser displayed the country map and connected status without fabricated data.

### Clean recheck after t13.1 dependency remediation

- `npm ci` — passed; 398 packages installed, 0 vulnerabilities reported.
- `npm audit --audit-level=low` — passed; 0 vulnerabilities.
- `npm test` — 3 passed, 0 failed, 0 skipped.
- `npm run build` — passed with Angular 21.2.29 build tooling. Non-blocking warnings: optional `lmdb` build cache is unavailable and Leaflet is CommonJS.
- `npm start` — passed after changing the script to `--prebundle false`; Angular CLI 21.2.29 rejected the previous `--prebundle=false` form as an unknown argument.
- Static smoke: `/`, `/config.json`, `/datos/paises.geojson`, and `/datos/ATTRIBUTION.md` — 4/4 HTTP 200.
- API contract probes: `GET /api/v1/health` and `GET /api/v1/earthquakes?limit=500&offset=0&scope=live` — 2/2 HTTP 200; live response shape matched the page DTO and currently contains zero events.
- Playwright Chromium rendered the country map, Natural Earth attribution, and connected status; no event markers or popups could be exercised because the API returned an empty page.
- `git diff --check` and the required `build`/`test` script check — passed.
- Aggregate focused recheck: **8 validation groups passed, 0 failed, 0 skipped**. Command set: `npm ci`; `npm audit --audit-level=low`; `npm test`; `npm run build`; `npm start`; `curl.exe` static-asset and API probes; `npx --yes playwright@1.64.1 screenshot --browser chromium`; `git diff --check` and npm-script validation.

## Naming and Scope

Uses the architecture's canonical `scope=live`, `/api/v1/...` routes, `frontend/public/datos/paises.geojson`, and IPv4 loopback API URL. Field spellings for the API DTOs were made explicit and sent to backend because t3 specifies DTO semantics but not every JSON property name. No replay UI, charts, filters, or event table were added; those belong to later frontend tasks.

Angular 21 remains the selected major; dependency remediation advanced the Angular packages to `21.2.25` and CLI/build tooling to `21.2.29`. Leaflet `1.9.4` is pinned. Angular 21 supports the available Node `22.15.0` toolchain per the [official Angular version compatibility table](https://angular.dev/reference/versions).

## Handoff / Risks

- The health API field is `last_event_ingested_at`; the frontend now consumes that runtime field, and backend was notified to record/confirm it because t3 specifies the freshness semantics but not the JSON property spelling.
- Current live API responses contain no events, so non-empty marker rendering and detail popups remain unverified.
- The t13.1 remediation is clean under both `npm ci` and `npm audit`; no known frontend advisories remain in this check.
- Local startup disables Vite prebundling using the Angular CLI 21.2.29-compatible `--prebundle false` syntax. Build warnings for optional `lmdb` cache and Leaflet CommonJS remain non-blocking.
