# Tasks: Análisis Sísmico Reproducible

**Input**: Design documents in `specs/002-analisis-sismico-reproducible/`

**Prerequisites**: `plan.md` and `spec.md`; supporting decisions and contracts in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

**Tests**: The specification defines independently testable outcomes and acceptance scenarios, so contract and acceptance test tasks are included. Write these tests before the corresponding implementation.

**Organization**: Tasks are grouped by the two user stories in `spec.md`. The project and test infrastructure already exist; no initialization or shared infrastructure changes are needed.

## Phase 1: Setup

**Purpose**: Project initialization.

The application, Docker Compose environment, and test runners are already established. No setup tasks are required.

---

## Phase 2: Foundational

**Purpose**: Blocking shared infrastructure for the user stories.

No new shared infrastructure is needed. The feature reuses the existing PostgreSQL import registry, API routes, dashboard, and test suites. User Story 1 must verify that the existing 2025 import is valid before it publishes analysis results.

---

## Phase 3: User Story 1 — Revisar conclusiones sísmicas trazables (Priority: P1) 🎯 MVP

**Goal**: Produce the three required quantitative conclusions from an identified 2025 import and a fixed recent window, with reproducible comparison statistics and depth percentiles.

**Independent Test**: Against a known fixture or valid imported baseline, verify that both comparison cohorts use M≥4.5 and matching geographic filters; all 365 UTC daily buckets (including zero days) sum to the historical total; population standard deviation and deviation bands are correct; and Type 7 p90 excludes missing depths. Regenerate the report from the same import and confirm the documented results and provenance are reproducible.

### Tests for User Story 1

- [ ] T001 [P] [US1] Add API contract tests for the M≥4.5 threshold, matching geographic predicates, 365 zero-filled UTC daily counts, population standard deviation, undefined zero-variance handling, and deviation bands in `backend/tests/test_api_contract.py`.
- [ ] T002 [P] [US1] Add acceptance coverage in `backend/tests/test_acceptance.py` proving analysis refuses an absent or invalid 2025 import and that generated totals and provenance reconcile with a valid import.

### Implementation for User Story 1

- [ ] T003 [US1] Extend the historical comparison query and response DTO in `backend/api/routes/comparison.py` and `backend/api/models.py` to return the fixed M≥4.5 comparison, exact UTC window, 365-day zero-filled baseline, population standard deviation, standardized deviation, descriptive band, and explicit unavailable values as specified in `contracts/historical-comparison.md`.
- [ ] T004 [US1] Extend filtered depth aggregation and its response DTO in `backend/api/routes/stats.py` and `backend/api/models.py` to return finite non-null population count, Hyndman–Fan Type 7 p90, exact applied period, and existing live/replay scope without mixing data, as specified in `contracts/depth-distribution.md`.
- [ ] T005 [US1] Update the frontend API types and response mapping in `frontend/src/app/api/earthquake-api.service.ts` for the comparison and depth response fields, preserving existing live/replay semantics.
- [ ] T006 [US1] Update the comparison and depth panels in `frontend/src/app/app.ts` and `frontend/src/app/app.html` to show the M≥4.5 threshold, comparison statistics, p90, valid-depth population, units, and unavailable states without presenting descriptive deviation as a risk forecast.
- [ ] T007 [P] [US1] Implement `backend/scripts/generate_seismic_analysis.py` to verify the successful 2025 import, record available provenance without inventing checksums, and generate reproducible report evidence including all 365 date/count pairs, recent and historical assigned/unassigned counts and shares, regional 2025 depth populations and p90, filters, calculation methods, and limitations.
- [ ] T008 [P] [US1] Reconcile the three quantitative conclusions and any unsupported prior figures in `docs/memoria_calidad.md` against the generated evidence; include the periods, populations, thresholds, denominators, and limitations, and do not publish unverified illustrative contract values.
- [ ] T009 [P] [US1] Update `specs/002-analisis-sismico-reproducible/quickstart.md` with the exact existing-container command and output locations for `backend/scripts/generate_seismic_analysis.py`, plus expected provenance and calculation checks.

**Checkpoint**: User Story 1 is complete when the comparison and p90 contracts are implemented, the report can be regenerated from a valid identified import, all three conclusions reconcile to the report output, focused backend/frontend checks pass, and the 11 acceptance scenarios pass and are recorded.

- [ ] T010 [US1] After completing User Story 1, run all 11 acceptance scenarios with `docker compose exec api pytest tests/test_acceptance.py -v`; record the TC-01–TC-11 results and any failures in `docs/evidence/seismic-analysis/acceptance-tc-01-to-11.md` before treating this story as a delivered increment.

---

## Phase 4: User Story 2 — Verificar la evidencia visual del análisis (Priority: P2)

**Goal**: Let an evaluator see the period, threshold, geographic filters, and values underlying the conclusions, and provide matching dashboard evidence.

**Independent Test**: Open the dashboard with the documented filters and verify that each saved screenshot visibly identifies its period, threshold and relevant geographic filters alongside the values shown in the report. Record any required indicator that is unavailable in the interface instead of claiming the screenshot proves it.

**Dependencies**: Requires User Story 1's API fields and dashboard metrics so captures can evidence the completed analysis.

### Implementation for User Story 2

- [ ] T011 [US2] Make the selected period and geographic-filter context visible beside the analytical panels in `frontend/src/app/app.ts` and `frontend/src/app/app.html`, retaining clear live/replay labeling and ensuring screenshots do not imply filters or periods that were not applied.
- [ ] T012 [US2] Capture the completed dashboard comparison and depth panels with the documented M≥4.5 threshold, period, and geographic filters visible, saving the evidence as `docs/evidence/seismic-analysis/dashboard-live-comparison.png` and `docs/evidence/seismic-analysis/dashboard-depth-distribution.png`.
- [ ] T013 [US2] Link the screenshots from `docs/memoria_calidad.md` and document any conclusion indicator that is not visible in the dashboard as an explicit evidence limitation.

**Checkpoint**: User Story 2 is complete when the images show the actual applied context and values, the report distinguishes visible evidence from unavailable indicators, and the 11 acceptance scenarios pass and are recorded.

- [ ] T014 [US2] After completing User Story 2, rerun all 11 acceptance scenarios with `docker compose exec api pytest tests/test_acceptance.py -v`; append the TC-01–TC-11 results to `docs/evidence/seismic-analysis/acceptance-tc-01-to-11.md` to validate this delivery increment.

---

## Final Phase: Polish & Cross-Cutting Validation

**Purpose**: Validate the complete feature against its documented acceptance scenarios without changing unrelated infrastructure.

- [ ] T015 Run the focused backend API tests, frontend tests and production build, and all reproducibility/evidence steps in `specs/002-analisis-sismico-reproducible/quickstart.md`; resolve failures in the relevant source, tests, or documentation files before declaring completion.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No work required; the project and test infrastructure already exist.
- **Foundational (Phase 2)**: No shared infrastructure work required; verifying the 2025 import is part of User Story 1.
- **User Story 1 (Phase 3)**: Starts after the existing project baseline is available. It is the MVP and does not depend on User Story 2.
- **User Story 2 (Phase 4)**: Depends on User Story 1's API response fields and dashboard metrics.
- **Polish (Final Phase)**: Depends on the desired user stories and their per-increment acceptance-suite runs being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Independent; delivers reproducible conclusions and is the suggested MVP.
- **User Story 2 (P2)**: Depends on User Story 1 for the implemented metrics and report values to capture.

### Within Each User Story

- User Story 1's contract and acceptance tests (T001–T002) precede implementation; its acceptance suite run (T010) gates the story checkpoint.
- Comparison response/model work (T003) precedes depth response/model work (T004) because both update `backend/api/models.py`.
- Frontend API mapping (T005) precedes panel rendering (T006).
- Generated evidence must exist before its conclusions are reconciled in `docs/memoria_calidad.md` (T008); the exact generator command is recorded in the quickstart (T009).
- User Story 2 starts after User Story 1 and T010; dashboard context (T011) precedes screenshots (T012), which precede documentation links and limitations (T013), followed by its acceptance suite run (T014).

### Parallel Opportunities

- T001 and T002 can be developed in parallel because they modify different test files.
- After the initial tests, T003 and T007 can proceed in parallel because they modify different files and their shared statistical semantics are already specified by the contracts.
- Once T007 is complete, T008 and T009 can proceed in parallel because they update separate documentation files.
- User Story 2 tasks are sequential because screenshots depend on the final dashboard and documentation depends on the captured files. T010 must finish before this story starts.

## Parallel Example: User Story 1

```text
Task: T001 — Add API contract tests in backend/tests/test_api_contract.py
Task: T002 — Add baseline/report acceptance tests in backend/tests/test_acceptance.py
```

## Implementation Strategy

### MVP First

1. Reuse the existing project setup; do not add services or dependencies.
2. Complete User Story 1, beginning with T001–T002 and continuing through the API, dashboard, report, and conclusion reconciliation.
3. Validate User Story 1 independently using its import-backed report and focused tests.
4. Stop for review if the imported 2025 dataset is absent, invalid, or cannot support reproducible results; do not substitute illustrative figures.

### Incremental Delivery

1. Deliver User Story 1 as the MVP with reproducible calculations and conclusions.
2. Add User Story 2's visible filter context and screenshots.
3. Run the final quickstart and focused validation after both stories.
