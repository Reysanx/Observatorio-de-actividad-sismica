# t5 — Angular Dashboard and Replay Interaction Specification

## Summary

This specification defines a Spanish-language, accessible dashboard for the local Angular + Leaflet MVP. It turns the existing functional and API contracts into concrete screen hierarchy, filter behavior, map/table interactions, connection states, and a replay flow that keeps live data visibly separate.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t2-pm.md` — MVP-08/09 behavior, local-only scope, `ND`, replay isolation, and canonical naming.
- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — API routes/DTOs, live-by-default query scope, replay run contract, poll guidance, and Natural Earth attribution.
- `specs/001-observatorio-sismico/spec.md` — FR-07/08/09 dashboard behaviors and domain display requirements.
- `specs/001-observatorio-sismico/tasks.md` — TASK-6.1–6.4 and TASK-7.2 frontend expectations.
- `specs/001-observatorio-sismico/data-spec.md` — UTC values, country assignment, and null magnitude semantics.
- `specs/001-observatorio-sismico/acceptance-tests.md` — TC-01, TC-03–07, TC-09–11 observable outcomes.
- `.specify/memory/constitution.md` — five-service/local-only boundary, no false zeroes, and replay isolation.
- `.agents/subagents/05-frontend-cartographer/AGENT.md` — frontend ownership and definition of done.
- `.agents/skills/acceptance-testing/SKILL.md` — visible `ND`, disconnect-retention, recovery, and replay-badge assertions.
- `.agents/rules/data_quality_rules.md` — valid negative magnitudes/depths and `Sin país asignado` display.

## Evidence Mapping

- `t2-pm.md#MVP-08` + `spec.md#FR-08` → dashboard hierarchy, shared filters, map/detail, charts, comparison card, table, and connection status below.
- `t2-pm.md#MVP-09` + `t3-architect.md#Decisions` items 3 and 6 + `constitution.md#2.5` → default-live scope, explicit run selection, replay badge, and live/replay separation below.
- `t3-architect.md#API Endpoints Inventory` → query scopes, filters, pagination, health/freshness, statistics, and replay-state polling below.
- `acceptance-tests.md#TC-05` + `data_quality_rules.md#1` → `ND` and valid negative value rendering.
- `acceptance-tests.md#TC-07` + `data_quality_rules.md#2` → maritime events remain visible as `Sin país asignado`.
- `acceptance-tests.md#TC-09–TC-10` + `t2-pm.md#Gaps and Handoff Notes` item 3 → local API disconnect/recovery behavior without ngrok.
- `t3-architect.md#Decisions` item 7 → Natural Earth source citation and honest country-name fallback.

## Product Decisions

1. The dashboard and all user-facing labels are in Spanish. Display all timestamps in UTC and include `Z` or an explicit `UTC` label; never silently present a local-time interpretation.
2. Initial and reset scope is **En vivo**. Replay is a separate, explicit view selected for a specific `run_id`; a missing replay run must show an empty/error state, never live data.
3. Replay status is passive: the dashboard observes `GET /api/v1/replay/state`; it does not invent a UI action to start a replay because the API contract defines no start endpoint.
4. The table’s free-text search applies only to the loaded table rows and is labeled **Buscar en eventos cargados**. It does not silently change the map or aggregates. Shared structured filters do update every dashboard view.
5. Use the approved Natural Earth country GeoJSON as the local geographic context. Show this attribution in the map footer/about area: “Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com.” Link to the public-domain terms. Do not claim that the source supplies Spanish names; show the API’s `NAME_ES` where available and otherwise its `ADMIN` fallback.
6. This is a local-only MVP. No public Netlify/ngrok status or configuration controls are shown. A browser-to-API failure is presented as an API/backend connection issue.

## Screen and Information Hierarchy

### Header and status

- Left: product name **Observatorio de actividad sísmica**.
- Right: scope control (**En vivo** / **Reproducción**) and an API connection indicator.
- Beneath the header, show the last successful dashboard refresh and the latest live-ingestion time reported by health data. Label the two times separately.
- When a replay run is active, show a persistent amber banner across the dashboard: **REPRODUCCIÓN · En curso** plus the run ID and a **Ver reproducción** action. The banner is global run status, not a claim that the currently selected live data has changed.
- When a replay is selected, keep the amber **REPRODUCCIÓN** banner visible even after completion, with **Finalizada** status and the run ID. The scope control must still say **Reproducción**.

### Shared filters

Place the filter panel above the main content. It contains:

- Time range presets: **1 h**, **6 h**, **24 h** (default), and **Personalizado** with start/end date-time inputs explicitly marked UTC.
- Minimum and maximum magnitude.
- Minimum and maximum depth in km.
- Country selector, including **Sin país asignado**, plus continent and subregion selectors where values are available.
- **Aplicar filtros** and **Limpiar** controls. Do not issue partial queries while a user is still editing a multi-field custom range.
- Reject or explain `start >= end` and minimum greater than maximum inline, without replacing the last valid dashboard data.

Changing structured filters updates the map, event count, geographic/hourly/distribution summaries, and table using the same filter snapshot. Reset table offset to zero and clear the selected event if it no longer matches. While requests are pending, retain existing data and show a small loading indicator rather than blanking the whole page.

### Main content

- Desktop: two-column layout. The map occupies approximately 60% of the content width; analytics occupy the remaining 40%.
- Tablet and narrow/mobile widths: stack map, analytics, then table vertically; keep filters available without horizontal scrolling.
- Map: country context and earthquake circles, with a visible legend and keyboard-accessible zoom controls.
- Analytics: event total; magnitude and depth distributions; fixed one-hour UTC activity chart; and a prominent recent-24-hour versus 2025 daily-mean comparison card.
- Event table: below the map/analytics, with sortable visible columns, page navigation, and the clearly scoped loaded-row search. Default order is newest event time first.

The historical-comparison card is **live-only** because the API comparison endpoint is fixed to live data. In replay scope, hide it and explain: **La comparación con 2025 solo está disponible en la vista en vivo.** Do not show a live comparison beside replay metrics as if it described the selected replay.

## Map and Event Selection

- Render one interactive circle for each returned event. Circle size increases with numeric magnitude, is clamped to a small positive range for valid negative magnitudes, and uses a fixed neutral size when magnitude is null. A null is never rendered as `0.0`.
- Color circles by depth using the specified bands: green `<30 km`; yellow `30–70 km` inclusive; orange `>70–300 km` inclusive; red `>300 km`. Missing depth uses neutral gray. Include text labels in the legend so color is not the only encoding.
- Selecting a marker opens a detail panel/popover and highlights the corresponding table row. Selecting a table row centers/highlights the marker and opens the same detail.
- Detail fields: magnitude (`ND` when null), depth in km (`ND` when null), event time in UTC, place, assigned country, event ID, and ingestion latency when available. Negative magnitude/depth values are shown as received, not clamped in text.
- Maritime/unassigned events remain selectable and are labeled **Sin país asignado**; do not infer a nearby country or hide them.
- Provide the table as a complete keyboard/screen-reader alternative to map-only interaction. Give markers an accessible name containing magnitude/`ND`, place, and UTC time. Focus must move predictably to the detail heading on selection and return to the initiating marker/row on close.

## Dashboard Query and Refresh Behavior

- Initial load requests health, live events (default 24-hour window), geographic stats, hourly stats, distributions, and historical comparison. Every live request omits replay scope or explicitly uses `scope=live`.
- Structured filter requests use the same normalized filter snapshot across the event and applicable analytics endpoints. UTC intervals follow inclusive start/exclusive end semantics.
- Fetch events with the API’s supported page size (up to 500); paginate and expose the returned filtered total. If the returned total exceeds the loaded set, indicate that the table search covers only loaded records and retain server pagination controls.
- Refresh the dashboard data every 60 seconds. Refresh the health indicator every 15 seconds. Display the time of the last successful response; never overwrite it with a failed request time.
- Poll replay state every 30 seconds while idle and every 2 seconds while a run is active. When a new run appears, update the banner and offer **Ver reproducción** without switching the user’s selected scope automatically.
- Selecting **Ver reproducción** uses the returned `run_id` and applies the current common filters to replay event/stat queries. Switching to **En vivo** removes `run_id` and uses only live data. Never combine, sum, or overlay event totals across scopes.
- If a run is active but no replay records have arrived yet, show **La reproducción está iniciándose; todavía no hay eventos**. A completed run with no matching events gets the ordinary filtered-empty state.

## Connection, Loading, and Empty States

- **First load:** show labeled skeletons and a non-blocking loading state.
- **No matching events:** state the active time/scope and offer **Limpiar filtros**; do not imply the API is disconnected.
- **API failure after a successful load:** retain map, charts, table, and their last successful timestamp. Show a prominent red/amber banner **Sin conexión con la API. Se conservan los últimos datos recibidos.** Mark displayed values as stale.
- **API failure before first successful load:** show the connection banner and an empty retry state; do not fabricate placeholder values.
- Retry automatically on the regular refresh cadence. On the first successful response, hide the disconnect banner and replace the retained data without requiring page reload.
- A failed replay-state poll must not erase the last known replay badge/run ID; mark replay status as not recently updated. Do not interpret an unavailable replay-state response as “no replay”.
- For this local-only MVP, TC-09/TC-10 are verified by simulating API unavailability/recovery, not by opening or closing ngrok.

## Accessibility and Responsive Requirements

- Use visible labels and keyboard-operable controls; preserve a visible focus indicator and logical tab order from header → filters → map controls/details → charts → table.
- Announce connection/replay status changes through a polite live region; reserve assertive announcements for a newly detected disconnection.
- Do not communicate depth, connection, or replay state through color alone; pair colors with text, icons, and/or patterns.
- Charts require accessible titles, summaries, and an equivalent tabular data representation. Support reduced-motion preferences and avoid flashing replay effects.
- At narrow widths, controls wrap/stack, table columns may scroll horizontally within the table region, and the page itself must not overflow horizontally.
- Keep adequate text/control contrast and minimum 44×44 CSS-pixel touch targets for primary controls.

## Acceptance Mapping for Frontend Verification

| Acceptance | Visible behavior to verify |
|---|---|
| TC-01 | A new event appears in the live map, event count, detail view, and table. |
| TC-03/04 | A newer revision updates the selected event; a stale revision does not visibly replace it. |
| TC-05 | Null magnitude is displayed as `ND` in marker detail/table/analytics context and never as zero. |
| TC-07 | An ocean event remains visible and reads **Sin país asignado**. |
| TC-09 | Simulated API loss shows the connection banner and retains the last valid dashboard data/timestamp. |
| TC-10 | API recovery clears the banner and refreshes the dashboard without a reload. |
| TC-11 | Active replay shows **REPRODUCCIÓN** and a run ID; selecting it shows only that replay run, while **En vivo** remains isolated. |

## Verification

- Documentation reviewed against the upstream UX/API contracts and acceptance scenarios listed above.
- No application code or browser tests were run: this task produces a UX specification only. Frontend verification should use the acceptance mapping once implementation exists.

## Issues for Downstream Roles

- Frontend: implement the interaction hierarchy, UTC filter semantics, retained-data error state, accessible table alternative, and replay-scope flow in this artifact. Use `/api/v1/replay/state` and explicit `scope=replay&run_id=...`; do not add a replay-start endpoint or auto-switch from live.
- Backend: no new API endpoint is required for this UX. Keep `GET /api/v1/earthquakes` pagination semantics explicit; the UI searches loaded table rows and must label that scope.
- Local acceptance should simulate API loss/recovery; do not configure ngrok or Netlify for this MVP.
