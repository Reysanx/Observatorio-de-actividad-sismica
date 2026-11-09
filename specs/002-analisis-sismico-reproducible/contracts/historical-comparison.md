# Contract: Live vs 2025 Historical Comparison

**Existing route**: `GET /api/v1/stats/historical-comparison`  
**Scope**: Live data only; replay mode must not consume this result.

## Request

| Query parameter | Type | Meaning |
|---|---|---|
| `adm0_a3` | Optional string | Country filter |
| `continent` | Optional string | Continent filter |
| `subregion` | Optional string | Subregion filter |

The route owns a fixed rolling 24-hour window ending at its UTC calculation time. Its magnitude threshold is fixed at M≥4.5. The same geographic predicates are applied to recent live and historical 2025 records. The API does not accept a client override for the threshold, time window, or reference year.

## Response

```json
{
  "calculated_at": "2026-11-09T18:00:00Z",
  "window_start_utc": "2026-11-08T18:00:00Z",
  "window_end_utc": "2026-11-09T18:00:00Z",
  "magnitude_threshold": 4.5,
  "recent_event_count": 41,
  "historical_2025_event_count": 14600,
  "historical_days": 365,
  "historical_daily_average": 40.0,
  "historical_daily_population_stddev": 8.2,
  "recent_standard_deviations_from_mean": 0.121951,
  "deviation_band": "within_1_sd",
  "ratio_to_historical_daily_average": 1.025,
  "adm0_a3": null,
  "continent": null,
  "subregion": null,
  "scope": "live"
}
```

The values above illustrate shape only; they are not project results.

## Semantics and errors

- Historical daily counts cover 2025-01-01 through 2025-12-31 UTC and include zero-count dates. Their sum equals `historical_2025_event_count`; `historical_daily_average` is that sum divided by exactly 365.
- `historical_daily_population_stddev` uses denominator 365. `recent_standard_deviations_from_mean` is null only when the standard deviation is zero or not definable because the historical dataset is not valid for analysis. The API must not return a fabricated zero in that case.
- `deviation_band` is `within_1_sd` when the absolute standardized deviation is at most 1; `between_1_and_2_sd` when it is greater than 1 and at most 2; `beyond_2_sd` when it is greater than 2; and `unavailable` when a standardized deviation is undefined. These are descriptive bands only, not risk classifications.
- `ratio_to_historical_daily_average` is null when the historical daily average is zero.
- `window_start_utc` and `window_end_utc` define a half-open interval `[start, end)` of exactly 24 hours; all returned timestamps are UTC RFC 3339 strings.
- `scope` is always `live`; the endpoint cannot query replay tables.
- Validation errors for malformed geographic filters follow the existing FastAPI query-validation contract. Database/data readiness failures return an explicit service error, not success-shaped metrics.
- The dashboard labels the threshold as M≥4.5 and shows the recent count, historical daily mean, population standard deviation, standardized deviation, event count, and day count. It must not imply a risk forecast.
