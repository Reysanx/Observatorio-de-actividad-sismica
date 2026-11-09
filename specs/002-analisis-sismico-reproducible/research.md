# Research: Análisis Sísmico Reproducible

**Feature**: [spec.md](./spec.md)  
**Date**: 2026-11-09

## Statistical conventions

### Comparison threshold

- **Decision**: The historical-comparison endpoint applies M≥4.5 to both recent and 2025 populations, while the stored 2025 catalogue may retain events from M≥4.0.
- **Rationale**: The evaluation rubric explicitly requires comparison of M≥4.5 events, and the same threshold must apply to both sides. Updating the canonical feature contract resolves the previous discrepancy without narrowing the stored historical catalogue.
- **Alternatives considered**: Keep M≥4.0 for the endpoint (fails the rubric); add a separate M≥4.5 endpoint or analysis mode (duplicates comparison behavior and expands scope).
- **Decision record**: [ADR-001](./adr/001-comparison-threshold.md).

### Population standard deviation for the 2025 daily counts

- **Decision**: Treat the 365 UTC calendar-day counts in 2025 as the complete population for the fixed-year descriptive comparison. Compute population standard deviation with divisor \(N=365\), not sample standard deviation with divisor \(n-1\).
- **Rationale**: The target being described is the full specified calendar year, not a sample drawn to estimate a larger population of days. This makes the choice of divisor explicit and repeatable. Zero-event dates are observations in the population and must be retained as zero.
- **Formula**: For daily counts \(x_1,\ldots,x_{365}\), \(\mu=(\sum x_i)/365\) and \(\sigma=\sqrt{\sum(x_i-\mu)^2/365}\). The recent standardized deviation is \((x_\text{recent}-\mu)/\sigma\) when \(\sigma>0\); otherwise it is unavailable and the report explains why.
- **Alternatives considered**: Sample standard deviation (divisor 364) would be appropriate if the 2025 days were a sample used to estimate an unobserved day-generating process. That is not the fixed-year descriptive estimand chosen here.
- **References**: OpenStax distinguishes population variance (divide by \(N\)) from sample variance (divide by \(n-1\)): <https://openstax.org/books/introductory-statistics/pages/2-7-measures-of-the-spread-of-the-data>. NIST/SEMATECH describes sample standard deviation and its use as an estimator: <https://www.itl.nist.gov/div898/handbook/eda/section3/eda356.htm>.

### Empirical 90th percentile of depth

- **Decision**: Use Hyndman–Fan Type 7, equivalent to NumPy's `linear` quantile convention, for the descriptive depth p90. State the method in the contract and report.
- **Rationale**: It is a widely used, deterministic interpolated sample quantile, appropriate for a descriptive percentile and easy for an independent reviewer to reproduce. The selected values are sorted in ascending order; with one-based rank \(h=1+(n-1)p\), linearly interpolate between adjacent order statistics. For \(p=0.90\), the p90 may lie between observed depths.
- **Alternatives considered**: Type 1 / inverted empirical CDF returns an observed sample value and is useful when the percentile must be an empirical threshold. Type 8 is designed for approximate median-unbiasedness when estimating a population quantile. The feature needs a descriptive percentile, not a threshold classifier or an estimator with a different inferential objective.
- **Empty/single-value behavior**: With no eligible values, p90 is null and the eligible population count is zero. With one value, p90 equals that value.
- **References**: R documents the Hyndman–Fan quantile types and identifies Type 7 as its default: <https://stat.ethz.ch/R-manual/R-devel/library/stats/html/quantile.html>. NumPy documents the `linear` method and the supported methods: <https://numpy.org/doc/stable/reference/generated/numpy.quantile.html>. Hyndman and Fan discuss the competing sample-quantile definitions: <https://doi.org/10.1080/00031305.1996.10473566>.

## Existing repository behavior and gaps

- `backend/api/routes/comparison.py` currently compares the rolling 24-hour live count and 2025 total with M≥4.0 and divides the annual total by 365. It does not construct an explicit daily series, report population standard deviation, or calculate a standardized deviation.
- The same route currently applies geography filters to both cohorts; preserve that behavior while raising the fixed threshold to M≥4.5.
- `backend/api/routes/stats.py` returns magnitude/depth histograms but no depth percentile or eligible-depth population count.
- `backend/api/models.py` holds the corresponding response DTOs; `frontend/src/app/api/earthquake-api.service.ts` mirrors them. `frontend/src/app/app.html` labels the current comparison M≥4 and displays the ratio, count, and daily mean.
- `backend/db/init.sql` defines `dataset_imports` for import count and timestamp. The historical bootstrap uses that registry and caches downloaded source files. Evidence must record the baseline import identity/count and source/cache manifest details available for the run; it must not claim a source checksum unless one is actually available and recorded.
- Existing backend contract and acceptance tests provide patterns for route assertions and full Compose-based event validation. Existing frontend tests run with Node's test runner.

## Design choices carried into Phase 1

- Preserve the current endpoint and dashboard workflow; extend their response contracts instead of adding a service or a second data pipeline.
- Build a complete 2025 UTC calendar series before computing population statistics, so absent dates contribute zero.
- Use a single fixed M≥4.5 contract threshold on both sides of the recent/historical comparison; keep geographic filter semantics symmetric.
- Return aggregate comparison statistics to the dashboard. Make a separate reproducibility artifact/query in the validation guide retain the 365 daily counts used for the evidence, avoiding repeated transmission of the whole annual series on every dashboard refresh.
- Expose dashboard p90 for the currently selected live filters, explicitly reporting eligible count and period/filter metadata. For the reproducible conclusion, calculate regional p90 from the 2025 historical population with the declared M≥4.5 threshold and geographic filters. Do not impute null depth in either calculation.
- Keep the dashboard's annual comparison unavailable in replay mode, as it is today.
