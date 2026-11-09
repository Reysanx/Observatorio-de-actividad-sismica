# Implementation Plan: Análisis Sísmico Reproducible

**Branch**: `[002-analisis-sismico-reproducible]` | **Date**: 2026-11-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-analisis-sismico-reproducible/spec.md`

## Summary

Make the observatory's quantitative analysis reproducible and internally consistent. Extend the existing live-versus-2025 comparison to use a symmetric M≥4.5 threshold and a complete 365-day daily baseline (including zero-count days), report population standard deviation and the recent count's standardized deviation, and expose a reproducible 90th percentile for filtered depth data. Reconcile the three written conclusions against identified data and calculations, and capture the filters and results shown by the dashboard. Preserve the existing five-service runtime, UTC behavior, live/replay separation, and local-only scope.

## Technical Context

**Language/Version**: Python 3.11 in backend containers; TypeScript/Angular 21 in the existing frontend.

**Primary Dependencies**: Existing FastAPI, asyncpg, PostgreSQL, Angular, RxJS, and Node.js test runner. No new runtime dependency is planned.

**Storage**: Existing PostgreSQL 16 relations `current_earthquakes`, `historical_2025`, `dim_countries`, and `dataset_imports`; documentation/evidence files remain in the repository.

**Testing**: Backend `pytest` unit/API contract tests and the focused Docker acceptance suite; frontend `npm test --prefix frontend` plus the existing production build.

**Target Platform**: Existing local Docker Compose backend on Windows/Linux hosts and the existing local Angular dashboard. No public deployment is part of this feature.

**Project Type**: Existing web application with a containerized Python API and Angular single-page dashboard.

**Performance Goals**: Preserve the dashboard's existing refresh cadence and responsive use. No new numerical latency SLO is specified; measure query behavior during validation and report any material regression rather than inventing a target.

**Constraints**:
- The annual baseline is the complete UTC calendar year 2025: exactly 365 calendar-day buckets, with zero-count days included.
- Use M≥4.5 and identical geographic predicates for the rolling recent 24-hour count and annual baseline comparison.
- Calculate annual standard deviation as a population statistic over those 365 daily counts. Calculate depth p90 with Hyndman–Fan Type 7 (linear interpolation).
- Do not impute missing magnitudes or depths as zero; the depth percentile population contains only valid finite depths and reports its population count.
- Keep all times UTC, keep replay queries and displays isolated from this live-versus-historical comparison, and do not add Compose services or expose credentials/public endpoints.
- Treat previous prose figures as unverified until recalculated from an identified dataset. Document source, extraction/import identity, analysis window, filters, and calculation method with results.
- Scope is the analytical comparison, depth p90, evidence, and related display/tests; it does not include unrelated quality-dimension metrics, benchmarking, TCO, or public deployment.

**Scale/Scope**: One additional bounded feature in an existing repository, reusing current API routes, response models, dashboard panels, and test suites; one historical year plus a rolling 24-hour window.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitution constraint | Plan decision | Gate |
|---|---|---|
| Exactly five long-running Compose services; no host execution of backend services | Reuse the existing API and database; no additional service or runtime | PASS |
| Kafka and PostgreSQL stay private; secrets remain outside source control | No network, credential, or deployment changes | PASS |
| UTC is used consistently for event time and API serialization | Keep UTC half-open intervals and UTC response timestamps | PASS |
| Missing numeric values are not replaced with zero; negative physical values remain valid | Compute depth p90 only from finite, present values; report its population; preserve existing null/negative behavior | PASS |
| Replay is isolated from live data and explicitly identified | Keep this comparison live-only and do not query replay relations | PASS |
| Existing architecture and dependencies should be reused | Extend current analytical contracts and dashboard rather than adding a service or dependency | PASS |

No constitution exception is required.

## Project Structure

### Documentation (this feature)

```text
specs/002-analisis-sismico-reproducible/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── adr/
│   └── 001-comparison-threshold.md
├── contracts/
│   ├── historical-comparison.md
│   └── depth-distribution.md
└── tasks.md                 # Created by /speckit-tasks, not by this plan
```

### Source Code (repository root)

```text
backend/
├── api/
│   ├── models.py
│   └── routes/
│       ├── comparison.py
│       └── stats.py
├── tests/
│   ├── test_api_contract.py
│   └── test_acceptance.py
└── scripts/
    └── generate_seismic_analysis.py # Deterministic evidence from the API container

frontend/
├── src/app/
│   ├── api/earthquake-api.service.ts
│   ├── app.ts
│   └── app.html
└── tests/
    └── dashboard-utils.test.mjs

docs/
├── memoria_calidad.md
└── evidence/
    └── seismic-analysis/   # Reproducible analysis output and dashboard captures
```

**Structure Decision**: Extend the existing API's historical comparison and distribution responses, add the corresponding fields to the existing Angular client and analytical panels, and keep query-contract and acceptance coverage beside the current backend tests. Add a deterministic report generator under the existing backend scripts directory and run it inside the API container. Store reproducible run evidence under a dedicated documentation evidence folder and reconcile the existing analysis memorandum. No new route, service, or database relation is needed.

The comparison threshold is M≥4.5 because the evaluation rubric's analytical requirement is more specific than the legacy M≥4.0 implementation. The canonical `specs/001-observatorio-sismico/spec.md` contract is updated to state this target behavior while preserving the M≥4.0 historical import population. See [ADR-001](./adr/001-comparison-threshold.md) for the decision and alternatives.

## Phase 0: Research

See [research.md](./research.md). Research resolves the two statistical conventions needed for reproducibility: population standard deviation for the complete fixed-year population of daily counts, and Hyndman–Fan Type 7 for a conventional interpolated empirical p90. Local repository inspection confirms the current comparison uses a fixed M≥4.0 threshold, returns a total divided by 365, and has no daily-count standard deviation; the current distributions response exposes histograms but no p90. These are bounded contract extensions, not unresolved design questions.

## Phase 1: Design & Contracts

- [Data model](./data-model.md) defines the analysis period, daily baseline, depth population, run provenance, and conclusions/evidence without introducing persistence requirements beyond the existing import metadata.
- [Historical comparison contract](./contracts/historical-comparison.md) specifies the symmetric M≥4.5 comparison, 365-day zero-filled baseline, population standard deviation, standardized deviation, and live-only scope.
- [Depth distribution contract](./contracts/depth-distribution.md) specifies filtered valid-depth population, Type 7 p90, and the empty-population response.
- [Validation guide](./quickstart.md) defines reproducible data checks, focused backend/frontend tests, evidence capture, and reconciliation steps.

The generated analysis evidence must also contain the three rubric conclusions, not just the dashboard metrics: geographical assignment shares for recent and historical populations; 2025 depth distributions by geographic area with p90; and the M≥4.5 recent count's location relative to the 2025 daily mean and population standard deviation. All three report populations use M≥4.5 and declared geographic filters. The dashboard p90 remains responsive to its selected live filters. Any tectonic interpretation is presented as a qualified hypothesis unless independently sourced.

### Constitution Check — Post-Design

| Design decision | Constitution constraint | Gate |
|---|---|---|
| Aggregate only existing live and historical relations; do not touch replay relations | Live/replay isolation | PASS |
| Generate all 365 dates in UTC and use half-open interval boundaries | UTC data integrity and correct annual denominator | PASS |
| Use the same threshold and geographic predicates on both sides of the comparison | Analytical consistency | PASS |
| Exclude missing depth values from percentile math and report the valid population size | No null-to-zero imputation | PASS |
| Extend existing API and dashboard without adding a service, port, or secret | Five-service architecture and network/security boundary | PASS |
| Keep sources, extraction identity, period, filters, and methods with published evidence | Data provenance and verifiability | PASS |

No constitution exception is required. Planning gates pass; there are no unresolved clarifications.

## Complexity Tracking

No constitution violations or architectural complexity exceptions.
