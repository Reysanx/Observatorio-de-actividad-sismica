# Feature Specification: Benchmarks y TCO reproducibles

**Feature ID**: `005-benchmarks-y-tco-reproducibles`  
**Status**: Complete  
**Scope**: Reproducible measurements and an auditable cost model for Criterio 5 / E-07.

## Context

The existing [`complexity_and_benchmarks.md`](../../docs/complexity_and_benchmarks.md)
and [`tco_costs.md`](../../docs/tco_costs.md) contain precise timings, memory
values, vendor charges, and projections without reproducible raw evidence or
complete price assumptions. Their figures must be audited and must not be
presented as confirmed measurements or quotations.

## Requirements

- **FR-001**: Provide a runnable procedure for 500, 10,000, and 100,000
  lookups using the production spatial lookup implementation and a
  source-identified historical cache.
- **FR-002**: Record elapsed wall time, process CPU time, throughput, and
  Python traced peak memory, including repetitions, warm-up, runtime versions,
  source hashes, and limitations.
- **FR-003**: Identify whether batch work uses unique source events or reuses
  source coordinates; do not call repeated lookups 100,000 unique earthquakes.
- **FR-004**: Keep benchmark scope explicit; do not imply that spatial
  microbenchmarks measure Kafka, PostgreSQL, API latency, or whole-process RSS.
- **FR-005**: Audit legacy benchmark/TCO figures as measured, arithmetically
  reproducible, assumed, or unsupported. Do not retain unsupported numbers as
  confirmed results.
- **FR-006**: Document TCO period, sources, retrieval date, currency, scope,
  formulas, and every assumption; distinguish list-price references from a
  quote for the target configuration.
- **FR-007**: Document theoretical Big-O separately from empirical evidence
  and avoid worst-case or performance guarantees not supported by the code or
  measurements.

## Acceptance criteria

1. The benchmark command produces machine-readable output for all three batch
   sizes and identifies cache/catalogue input by SHA-256.
2. Tests cover invalid/missing source files and reported measurement fields.
3. The 100k batch explicitly reports coordinate reuse when the cache is
   smaller than the requested lookup count.
4. Existing benchmark claims are marked unverified unless accompanied by
   reproducible evidence; no API/DB latency result is fabricated.
5. Existing TCO arithmetic is checked, but prices and operating assumptions
   are explicitly not treated as quotes or observed bills.
6. Every external price or tariff reference is linked with an accessed date
   and is not generalized beyond what its source states.
