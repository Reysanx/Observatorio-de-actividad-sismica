# Tasks: Métricas Reproducibles de Calidad 6D

**Input**: Design documents from `specs/003-metricas-calidad-6d/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/quality-report.schema.json`, `quickstart.md`

**Tests**: The plan requires deterministic unit and read-only integration validation; tasks include tests for the report calculations and its output.

**Organization**: Tasks are grouped by the two user stories in `spec.md`. The initial report/MVP covers User Story 1; User Story 2 adds focused interpretation of accuracy and its limits.

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel with another task in the same phase because it edits separate files and has no unfinished dependency.
- **[Story]**: Maps a task to its user story (`US1`, `US2`).
- Every task names the file it creates or changes.

## Phase 1: Setup

**Purpose**: Establish the report entry point without changing the existing services, schema, dependencies, or branch.

- [ ] T001 Create the read-only quality-report CLI entry point in `backend/scripts/quality_report.py`; emit JSON to stdout by default so output can be captured on the host without adding a Compose service or mounting repository documentation into a container.

## Phase 2: Foundational

**Purpose**: Provide trusted, shared inputs for all report dimensions; user-story work depends on these tasks.

- [ ] T002 Implement verified historical-cache and manifest loading in `backend/scripts/quality_report.py`; preserve monthly source counts separately from unique `event_id` counts, verify available SHA-256 identities, and fail explicitly on missing/incomplete source artifacts rather than silently substituting data.
- [ ] T003 Implement read-only PostgreSQL access and source-to-persisted matching in `backend/scripts/quality_report.py`; match historical features and `historical_2025` rows by `event_id`, use `raw_payload` as the stored source evidence, and execute reads in a read-only transaction without changing business tables.

**Checkpoint**: Report execution has a verifiable source identity and safe, read-only access to the persisted comparison population.

## Phase 3: User Story 1 - Evaluar la calidad con evidencia reproducible (Priority: P1) 🎯 MVP

**Goal**: Produce a repeatable, population-scoped report for all six dimensions, compare only traceable before/after records, reconcile dispositions, and replace unsupported historical quality claims.

**Independent Test**: Run the report twice against the same verified cache manifest, database snapshot, and rule-set version. Confirm that all six dimensions have a measured result or a reasoned `not_verifiable` result, every numeric metric includes its formula/evidence/numerator/denominator/unit, deterministic values match, and input-to-output discrepancies are reconciled without mixing live, replay, or synthetic records into the historical cohort.

### Tests for User Story 1

- [ ] T004 [US1] Add unit and report-contract tests in `backend/tests/test_quality_report.py` for eligible-field denominators, null handling, ID matching and collisions, historical cache-to-database reconciliation, deterministic output fields, exactly one entry for each of the six dimensions, and multiple submetrics in a dimension; assert rejection of missing/duplicate dimensions and measured submetrics without required fields, and cover transformation impact counts, possible overlap, unverified stages, missing timestamps, `N/A`, valid negative magnitude/depth values, and separate live/synthetic populations.

### Implementation for User Story 1

- [ ] T005 [US1] Implement population-scoped completeness, uniqueness, validity, consistency, currency, and accuracy calculations as nested submetrics in `backend/scripts/quality_report.py`; support per-field completeness and separate latency statistics, include numerator/denominator/formula/unit/evidence/limitations for each measured submetric, and mark absolute accuracy `not_verifiable` when no independent reference exists.
- [ ] T006 [US1] Add historical cache-to-database matching and report matched, missing, and unmatched rows in `backend/scripts/quality_report.py`; enumerate each observable transformation with stage, affected-record count, eligible denominator, evidence, and overlap policy. Mark pre-cache filtering, deduplication, and historical quarantine as not verifiable when their audit trail is absent; report accepted, excluded, and quarantined counts from live audit tables only as a separate population with independent denominators, and claim complete reconciliation only when audit coverage spans all stages.
- [ ] T007 [US1] Emit report JSON conforming to `specs/003-metricas-calidad-6d/contracts/quality-report.schema.json` from `backend/scripts/quality_report.py`; include exactly one dimension entry for each of the six dimensions, its one-or-more nested submetrics, per-population transformation counts/limitations, evaluation/method/rule-set identity, population filters/period, cache/dataset identity, and stable deterministic values apart from generation timestamps.
- [ ] T008 [US1] Generate the reproducible evidence package in `docs/evidence/data-quality/quality-report.json` and `docs/evidence/data-quality/README.md` from the real available cache and database; record the exact input identity, command, timestamp, rule version, historical match and per-transformation counts, their overlap policies, separately scoped live audit/quarantine counts when available, and non-verifiable stages, and do not fabricate results if required source artifacts are unavailable.
- [ ] T009 [US1] Update `docs/memoria_calidad.md` to link the generated 6D evidence, explain its measured populations and before/after meaning, and remove or label unsupported historical quality figures as non-reproducible rather than current results.

**Checkpoint**: User Story 1 can be reviewed and reproduced without implementing User Story 2's expanded accuracy interpretation.

## Phase 4: User Story 2 - Interpretar exactitud sin afirmar una verdad no disponible (Priority: P2)

**Goal**: Make the boundary between observable transformation/spatial proxies and absolute seismic accuracy explicit to reviewers.

**Independent Test**: Inspect the report and accuracy explanation. Every accuracy figure must name its observed comparison, source, denominator, and limitations; no value may claim an independent ground truth or imply an overall absolute-accuracy rate.

### Implementation for User Story 2

- [ ] T010 [P] [US2] Document the accuracy-proxy definitions, interpretation, required evidence, and scientific limitations in `docs/evidence/data-quality/accuracy-limitations.md`; distinguish payload-to-canonical-field fidelity and Natural Earth spatial concordance from independently verified seismic truth, and state that absolute accuracy is not verifiable with current sources.
- [ ] T011 [US2] Add a link from the accuracy discussion in `docs/memoria_calidad.md` to `docs/evidence/data-quality/accuracy-limitations.md`; ensure «Sin país asignado» is not interpreted as an accuracy failure and proxies are not presented as ground truth.
- [ ] T012 [US2] Extend report tests in `backend/tests/test_quality_report.py` to assert that accuracy results identify `reference_independent` as false, label measurable comparisons as proxies, and provide limitations or an explicit not-verifiable reason.

**Checkpoint**: The accuracy interpretation is independently auditable and consistent with the numeric report.

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete workflow and keep its reproduction instructions synchronized.

- [ ] T013 [P] Update `specs/003-metricas-calidad-6d/quickstart.md` with the final CLI invocation, prerequisites, host-side output capture, expected report structure, and read-only validation procedure.
- [ ] T014 Run the targeted report tests and the documented Compose-based reproduction from `specs/003-metricas-calidad-6d/quickstart.md`; verify `docs/evidence/data-quality/quality-report.json` against the contract, repeatability of deterministic metrics, unchanged database row counts, exact coverage of all six dimensions, and absence of live/replay/synthetic data in the historical population.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 establishes the CLI file and stdout contract.
- **Foundational (Phase 2)**: T002 depends on T001; T003 depends on T002 and enables source-to-persisted comparisons. Both block the user stories.
- **User Story 1 (Phase 3)**: Depends on the foundational phase. T004 specifies calculation and output expectations before T005; T005 precedes T006/T007; T008 requires the completed report; T009 uses the results from T008.
- **User Story 2 (Phase 4)**: Depends on the report and evidence from User Story 1 so the written proxy explanation reflects actual available measurements. T010 and T012 can proceed in parallel; T011 follows T010 and links the explanation.
- **Polish (Phase 5)**: T013 follows the finalized CLI behavior; T014 depends on all implementation and documentation tasks.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2. Delivers the MVP and does not depend on User Story 2.
- **User Story 2 (P2)**: Starts after User Story 1 because its interpretation must agree with the generated report. It does not change the report population or invent a reference dataset.

### Parallel Opportunities

- T010 and T012 edit separate files and can be done in parallel after User Story 1.
- T013 can be prepared in parallel with T010/T012 once the CLI contract from T001 and report contract from T007 are stable.
- No parallel marker is used for tasks that edit the same file or depend on unfinished report implementation.

### Parallel Example: User Story 2

```text
Task: T010 Document accuracy-proxy limits in docs/evidence/data-quality/accuracy-limitations.md
Task: T012 Extend accuracy assertions in backend/tests/test_quality_report.py
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001–T003 to establish the CLI, verified cache identity, and read-only database matching.
2. Complete T004–T007 to calculate, reconcile, and serialize the six-dimensional report.
3. Complete T008–T009 to generate actual evidence and replace unsupported claims in the quality memory.
4. Stop and validate the User Story 1 independent test before adding explanatory material for User Story 2.

### Incremental Delivery

1. Deliver User Story 1 as the evidence-producing MVP.
2. Add User Story 2's focused accuracy limitations and consistency assertions.
3. Run the final quickstart and repeatability checks in T014.

## Notes

- The historical cache is already filtered to USGS earthquake Features with M≥4 and deduplicated by the downloader. Its results cannot be described as measurements of the unfiltered raw feed or as counts of records removed before caching.
- Historical, live, replay, and synthetic populations must remain distinct.
- Preserve legitimate nulls and negative physical values; do not treat `N/A` as an error or use Natural Earth as ground truth.
- Do not add a service, database migration, API endpoint, or third-party dependency for this feature.
