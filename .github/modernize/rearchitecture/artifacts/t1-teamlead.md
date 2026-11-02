# t1 — Canonical Scenario Decisions

**Status:** Complete for the assigned scenario-decision gate  
**Project:** `001-observatorio-sismico`  
**Decision source:** User's direct response in this task; no further clarification form is required.

## Canonical Decisions

### Product scope and frontend
- Implement a bounded local MVP, not a public deployment.
- Use a minimal Angular starter and the existing mandated Angular + Leaflet direction. No component library, design system, screenshots, or Angular version was specified; do not invent a design-system requirement. Select and record a compatible Angular version during implementation without asking the user another question.
- Keep UTC as the time basis. A missing magnitude remains database `NULL` and is rendered as `ND`, never `0`.
- Do not use credentials or attempt Netlify/ngrok publication.

### Country boundaries and attribution
- Use Natural Earth's Admin-0 countries GeoJSON from the public `nvkelso/natural-earth-vector` repository:
  `https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson`
- Natural Earth's official terms state that its raster and vector map data are public domain. Record the source URL and the license/terms alongside the checked-in data. Include the suggested attribution: “Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com.”
- Natural Earth source GeoJSON does not promise the specification's `NAME_ES` field. The implementation must not claim that it does; provide a documented Spanish-name mapping or a documented `ADMIN` fallback while preserving the other available source attributes.

### Naming and isolation conventions
- Canonical Docker Compose service IDs are `productor`, `broker`, `consumidor`, `almacenamiento`, and `api`, matching the constitution. There must be exactly these five required services. Use these same IDs for Compose DNS references; do not use `kafka`/`postgres` as alternate service IDs.
- Canonical Kafka topics are `earthquakes.live` and `earthquakes.replay`. This resolves the hyphenated `earthquakes-replay` variant in the functional specification in favor of the dotted topic style used by the plan and task breakdown.
- Replay must remain isolated from live data, analytics, and counts, and the UI must show the `REPRODUCCIÓN` badge while replay is active. The architecture phase must specify how the dedicated replay topic is isolated in persistence/API queries.
- Continue using the established snake_case table names from the data specification and constitution (including `current_earthquakes`, `earthquake_versions`, `quarantine_events`, `historical_2025`, `dim_countries`, and `ingestion_audit`).
- Never expose Kafka or PostgreSQL outside the Compose network; keep secrets out of the repository.

## Clarification State

The user supplied the decisions above directly and explicitly asked that no further clarification form be created. Angular version selection and the exact implementation of replay persistence remain implementation/design choices for downstream roles, not questions to return to the user. No source code, dataset, or public deployment was produced by this t1 decision-record task.

## Upstream Artifacts Consumed

- `board.md` — confirmed t1 is the scenario-decision gate and that the next dependency is PM specification tracing.
- `specs/001-observatorio-sismico/spec.md` — product requirements, especially FR-03, FR-08, and FR-09.
- `specs/001-observatorio-sismico/plan.md` — five-service plan and dotted live/replay topic convention.
- `specs/001-observatorio-sismico/tasks.md` — implementation task names and current division of work.
- `specs/001-observatorio-sismico/data-spec.md` — Natural Earth attributes, UTC/null rules, country assignment, and canonical database names.
- `specs/001-observatorio-sismico/acceptance-tests.md` — acceptance contracts for null magnitudes, maritime events, recovery, and isolated replay.
- `.specify/memory/constitution.md` — mandatory stack, five service IDs, secret/network boundaries, idempotency, and replay isolation.
- `.agents/AGENTS.md`, `.agents/rules/architecture_invariants.md`, `.agents/rules/data_quality_rules.md`, `.agents/skills/acceptance-testing/SKILL.md`, and `.agents/skills/usgs-ingestion/SKILL.md` — project orchestration, quality, and ingestion constraints.
- Natural Earth official terms: <https://www.naturalearthdata.com/about/terms-of-use/> — confirms public-domain status and provides the suggested attribution.
- Natural Earth Admin-0 countries page: <https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/> — authoritative dataset context; the GeoJSON URL above is the public vector repository file.
- `none — no dependency artifacts were provided for t1`.

## Evidence Mapping

- `constitution.md#2.1` and `.agents/rules/architecture_invariants.md#1` → five canonical Compose IDs and exactly-five-services constraint above.
- `spec.md#FR-08` and `constitution.md#3.1` → minimal Angular starter while preserving the Angular + Leaflet product direction.
- `spec.md#FR-09`, `plan.md#2.2`, `plan.md#6`, and `tasks.md#TASK-3.2` → dotted replay topic and strict live/replay separation.
- `data-spec.md#1.3` and Natural Earth official terms → public Natural Earth GeoJSON source, accurate license record, and attribution above.
- `data-spec.md#2-3`, `constitution.md#2.3-2.5`, and `acceptance-tests.md#TC-05/TC-07/TC-11` → UTC/null-magnitude, maritime classification, idempotency, and replay-badge constraints.
- User's direct response in this task → no further clarification form, minimal Angular starter, Natural Earth source/license attribution, local-only MVP, and no credentials/publication.

## Verification

- Reviewed the decision record against the cited specifications, constitution, project rules/skills, and official Natural Earth terms.
- Runtime/build tests: not applicable; this task changes no application code or runtime configuration.
- Blockers for t1: none. Downstream implementation must verify the GeoJSON download and document the Spanish-name mapping/fallback before claiming the map data contract is complete.
