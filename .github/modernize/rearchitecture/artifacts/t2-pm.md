# t2 — MVP behavior traceability

## Summary

Traced the requested bounded local MVP against the approved feature specification, technical plan, task breakdown, data contract, acceptance matrix, constitution, project rules/skills, and t1 scenario decisions. The MVP's observable product behaviors are substantially specified. The main handoff gaps are replay isolation details, the Natural Earth Spanish-name mapping, and translating tunnel-specific acceptance cases into local tests without deploying a tunnel.

This is a product traceability artifact, not an implementation or feature-parity sign-off. No runtime behavior is claimed as implemented or verified.

## Scope Baseline

- Implement and validate a reproducible **local** MVP. Compose contains exactly five required services; do not publish to Netlify or configure/use ngrok for this assignment.
- In-scope behaviors: USGS live and historical-2025 ingestion; quality/quarantine; geospatial enrichment; idempotent persistence and revisions; documented API analytics; map/dashboard; isolated replay and its badge; focused acceptance tests; local run instructions and `.env.example`.
- Preserve UTC; preserve null magnitude as `NULL` and display it as `ND`; do not reject negative magnitudes or depths by default.
- Do not claim academic deliverables (Big-O/benchmarks/TCO/notebook/grade evidence) unless separately produced and verifiable.
- The user-approved Natural Earth source, license/attribution, and the naming resolutions below come from t1.

## Behavior Traceability

| ID | Observable requirement / acceptance | Existing specification evidence | MVP evidence to capture |
|---|---|---|---|
| MVP-01 | Local startup has exactly the five required services and keeps Kafka/PostgreSQL private; only local API access is exposed. | `constitution.md` §2.1–2.2; `plan.md` §§2, 4; `tasks.md` TASK-1.2; t1 canonical decisions | Compose service-ID list is exactly `productor`, `broker`, `consumidor`, `almacenamiento`, `api`; inspect published ports and verify no broker/database port is exposed. |
| MVP-02 | Live ingestion polls USGS's rolling 24-hour GeoJSON every 60 seconds, keeps only earthquake events, and records extraction metadata/failures. | `spec.md` FR-01, NFR-02; `data-spec.md` §1.1; `plan.md` §2.1; `tasks.md` TASK-3.1 | Test source/type filtering, message metadata, and retry/audit behavior without depending on public deployment. |
| MVP-03 | Historical ingestion covers all of 2025 with magnitude ≥4, monthly requests, safe subdivision near the USGS limit, boundary deduplication, and reusable local cache. | `spec.md` FR-02; `data-spec.md` §1.2; `plan.md` §2.1; `tasks.md` TASK-2.2 | Validate all 12 month ranges, subdivision threshold, unique event IDs, and cache reuse. Monthly request partitioning is specified; database table partitioning is not mandated by these sources. |
| MVP-04 | Country enrichment uses WGS84 country polygons, deterministic point-in-polygon, and explicit maritime/boundary behavior; it never infers country from `place` or nearest-country distance. | `spec.md` FR-03; `data-spec.md` §§1.3–2; `tasks.md` TASK-2.1/TASK-4.1; `.agents/rules/data_quality_rules.md` §2; `spatial-strtree-pipeline/SKILL.md` | Verify country hit, maritime `N/A`/`Sin país asignado`, boundary tie-break, and documented source attribution/license. |
| MVP-05 | Invalid/unrecoverable events are quarantined with an explicit reason and raw payload; valid null/negative values retain their meaning. | `spec.md` FR-05; `data-spec.md` §§3–4; `.agents/rules/data_quality_rules.md` §§1, 3; `tasks.md` TASK-4.2; acceptance TC-05/06 | Exercise null magnitude, negative magnitude/depth, out-of-range/non-finite coordinates, corrupt JSON, and missing identifier. Confirm `NULL`/`ND` and quarantine contents. |
| MVP-06 | Repeated messages do not duplicate current events or aggregates; only strictly newer revisions replace current state and prior versions are traceable. Kafka offsets commit only after the database transaction commits. | `spec.md` FR-04/06; `constitution.md` §2.3; `plan.md` §§2.3, 6; `data-spec.md` §3; `kafka-idempotent-consumer/SKILL.md`; acceptance TC-01–04/08 | Verify insert, exact duplicate, newer revision, stale revision, consumer restart, and database-before-offset ordering. |
| MVP-07 | The API exposes health, filtered/paginated earthquakes, geographic/hourly/distribution analytics, and the 2025 comparison. | `spec.md` FR-07/NFR-01; `plan.md` §2.5; `tasks.md` TASK-5.1–5.5; `.agents/subagents/04-backend-modeler/AGENT.md` | Probe each documented endpoint and verify filters, UTC-hour buckets, null handling, unassigned-country inclusion, and 365-day comparison denominator. |
| MVP-08 | The dashboard presents a map with event detail, synchronized filters, charts, historical comparison, status/freshness, and a table alternative. A null magnitude is `ND`; a failed API retains last valid data and reports disconnection. | `spec.md` FR-08; `tasks.md` TASK-6.1–6.4; `.agents/subagents/05-frontend-cartographer/AGENT.md`; acceptance TC-05/09/10 | Browser or focused UI tests verify map/detail, filters update all views, chart/card behavior, `ND`, stale-data retention, and recovery. No publication required. |
| MVP-09 | Historical replay is visibly marked `REPRODUCCIÓN` and cannot contaminate live counts, analytics, or state. | `spec.md` FR-09; `constitution.md` §2.5; `plan.md` §6; `tasks.md` TASK-7.2; acceptance TC-11 | Publish controlled replay fixtures and assert replay UI state while live queries/counts remain unchanged. |
| MVP-10 | The developer can configure and run the bounded local system without committed secrets. | `tasks.md` TASK-1.1; `constitution.md` §2.2; `plan.md` §4; user's direct instruction | Verify `.env.example` contains placeholders only, local run instructions match Compose, and no credentials/publication are used. |

## Canonical Names and Explicit Resolutions

Use the t1 decision record as the source of truth where source files disagree:

- Compose services and Compose DNS names: `productor`, `broker`, `consumidor`, `almacenamiento`, `api`. Do not introduce alternate service IDs `kafka` or `postgres`, despite examples in older constitution/plan text.
- Kafka topics: `earthquakes.live` and `earthquakes.replay`; use dotted names, not the functional spec's `earthquakes-replay`.
- Database names: snake_case, including `current_earthquakes`, `earthquake_versions`, `quarantine_events`, `historical_2025`, `dim_countries`, and `ingestion_audit`.
- Source GeoJSON is not assumed to contain `NAME_ES`. Record the t1-approved Natural Earth public-domain source and attribution; document the chosen Spanish-name mapping/fallback and preserve available source properties.
- Keep UTC and `mag = NULL`/UI `ND`; maritime events remain `adm0_a3 = 'N/A'` and `country_name = 'Sin país asignado'`.

## Gaps and Handoff Notes

1. **Replay separation is an acceptance requirement, not a settled persistence design.** `plan.md` §6 permits a separate replay table or a simulation flag and mentions `/api/v1/replay/state`; `spec.md` FR-09 does not define that endpoint. Architecture must choose and document a contract that proves live queries and aggregates exclude replay, plus a replay-state signal for the UI. Do not treat a dedicated topic alone as proof of end-to-end isolation.
2. **Natural Earth `NAME_ES` needs a documented mapping/fallback.** The data spec names this property, but t1 notes that the approved source does not promise it. Do not claim that the source directly provides Spanish names.
3. **Local acceptance scope differs from the original tunnel scenarios.** TC-09/TC-10 name ngrok specifically; for this local-only MVP, simulate API loss/recovery and verify stale-data retention/recovery without installing, authenticating, or starting ngrok.
4. **Healthcheck guidance differs.** `.agents/rules/architecture_invariants.md` calls for healthchecks on every service; `plan.md` §4 demonstrates healthchecks on PostgreSQL/Kafka and readiness dependencies for the other services. The five-service invariant is firm; the architecture role should state how the healthcheck rule is satisfied for every service, or document the exact limitation rather than silently ignoring it.
5. **Scope boundary:** the task list also includes Netlify/ngrok publication and academic outputs (TASK-7.1, TASK-8.2–8.4). These are not evidence of completion for this bounded local MVP; do not attempt publication or claim those deliverables.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t1-teamlead.md` — canonical user decisions, local-only boundary, service/topic/table naming, Natural Earth source/license direction, and replay isolation requirement.

## Evidence Mapping

- `t1-teamlead.md#Canonical Decisions` → scope baseline and canonical names above.
- `t1-teamlead.md#Country boundaries and attribution` → MVP-04 and the documented Spanish-name mapping gap.
- `t1-teamlead.md#Naming and isolation conventions` → canonical names and MVP-09 replay isolation.
- `specs/001-observatorio-sismico/spec.md#FR-01–FR-09` → MVP-02, MVP-04–09.
- `specs/001-observatorio-sismico/data-spec.md#1–4` → MVP-03–06 and data-contract test evidence.
- `specs/001-observatorio-sismico/acceptance-tests.md#TC-01–TC-11` → focused acceptance coverage in MVP-05–09.
- `.specify/memory/constitution.md#2.1–2.5` → MVP-01, MVP-05, MVP-06, MVP-09 and secret/network constraints.

## Verification

- Cross-checked the requested MVP behaviors against the cited product, architecture, data, and acceptance documents and the t1 decision record.
- No application code was changed and no runtime tests were run in this PM traceability task; implementation evidence remains for the downstream implementation/validation tasks.
- No blockers to the specification handoff. The gaps above are explicit follow-ups, not user clarification requests.
