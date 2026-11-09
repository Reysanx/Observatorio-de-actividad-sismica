# ADR-001: Umbral para la comparación histórica

**Status**: Accepted  
**Date**: 2026-11-09  
**Scope**: `GET /api/v1/stats/historical-comparison` and the reproducible analysis report

## Context

The evaluation rubric requires comparing the M≥4.5 events from the recent 24-hour window with the 2025 daily average. The current endpoint and its canonical specification described M≥4.0, while the historical catalogue itself is intentionally imported from M≥4.0.

The project constitution requires implemented behavior to be supported by `specs/001-observatorio-sismico/` and requires impact-level design decisions to record their alternatives and rationale.

## Decision

Keep the stored historical catalogue at its existing M≥4.0 coverage. Apply M≥4.5 symmetrically when calculating both the recent count and the 2025 comparison population. Update the canonical endpoint contract in `specs/001-observatorio-sismico/spec.md`; feature 002 implements that contract and exposes its statistics.

## Consequences

- The historical import remains broad enough to support existing analyses at M≥4.0.
- The comparison API, report, and dashboard use M≥4.5 on both cohorts.
- The current M≥4.0 endpoint behavior is a known implementation gap until feature 002 is implemented.
- Acceptance tests must assert the threshold on both sides of the comparison.

## Alternatives considered

1. **Keep M≥4.0 in the comparison endpoint**: rejected because it does not meet the evaluation rubric.
2. **Add a separate M≥4.5 endpoint or analysis mode**: rejected because it duplicates comparison behavior and expands scope without a rubric requirement.
3. **Reduce the historical catalogue to M≥4.5**: rejected because it unnecessarily discards already available data and changes ingestion coverage.
