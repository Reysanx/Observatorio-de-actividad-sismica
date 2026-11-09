# Contract: Filtered Depth Distribution and p90

**Existing route**: `GET /api/v1/stats/distributions`  
**Scope**: The existing selected live or run-scoped replay event filters. This endpoint provides dashboard p90; the reproducible conclusion's regional p90 is calculated over the 2025 historical population in the analysis evidence.

## Request

The route uses the existing event time, magnitude, depth, and geographic filters. It must apply the same selected filter set to the depth histogram and depth percentile. A replay request remains scoped to its explicit replay run and must not be combined with live data.

## Response additions

```json
{
  "depth_p90_km": 42.5,
  "depth_population_count": 137,
  "depth_percentile_method": "hyndman_fan_type_7",
  "depth_period_start_utc": "2026-11-08T18:00:00Z",
  "depth_period_end_utc": "2026-11-09T18:00:00Z",
  "scope": "live",
  "run_id": null
}
```

The values above illustrate shape only; they are not project results. Existing magnitude/depth bins and null counts remain present.

## Semantics and errors

- The p90 is calculated over finite, non-null depth measurements matching the request's event and geographic filters. Missing values are excluded, never changed to zero.
- The method is Hyndman–Fan Type 7: sort the \(n\) values; for probability \(p=0.90\), use one-based rank \(h=1+(n-1)p\) and linearly interpolate between the adjacent order statistics.
- `depth_population_count` is the number of eligible measurements. If it is zero, p90 is null. A one-value population returns that value.
- Period fields are the exact event-time bounds applied by the request, in UTC, and must agree with the filters used for the histogram.
- Existing `scope` and `run_id` semantics are preserved. For a replay response, p90 describes only that run; replay observations never enter live conclusions.
- Database/data-readiness failures follow the existing explicit error behavior.
- The historical 2025 conclusion uses the same M≥4.5 threshold and declared geographic filters as the other report conclusions, grouped by the specified geographic area. It is not inferred from the live-only dashboard response.
