# Data Model: Análisis Sísmico Reproducible

## Purpose and persistence boundary

This feature derives auditable analytical values from the existing event and import relations. It does not require a new persistent database table. A run's reproducibility record is stored with its generated evidence, while the database remains the source of event and import data.

## Entities

### Analysis Run

One reproducible execution of the analysis.

| Attribute | Meaning | Validation |
|---|---|---|
| `analysis_id` | Unique identifier for the evidence execution | Non-empty and unique within the evidence set |
| `generated_at_utc` | Time the report was generated | UTC timestamp |
| `baseline_dataset_key` | Existing identity of the imported 2025 dataset | Must resolve to the successful import registry entry |
| `baseline_event_count` | Imported unique event count | Non-negative integer; must agree with the import registry |
| `baseline_source_manifest` | Source/cache manifest identifier and available checksums | Record only values that exist; never fabricate a checksum |
| `recent_window_start_utc`, `recent_window_end_utc` | Exact rolling 24-hour observation interval | UTC, start < end, duration exactly 24 hours for the fixed comparison |
| `magnitude_threshold` | Fixed comparison cut-off | 4.5 |
| `geographic_filters` | Country, continent, and subregion filters | Same normalized values used for recent and historical cohorts |
| `query_or_method_version` | Version/reference of the calculation procedure | Required to reproduce the result |

### Annual Daily Count

One row/value per calendar date in the historical baseline. This is a derived evidence entity, not a new database table.

| Attribute | Meaning | Validation |
|---|---|---|
| `date_utc` | UTC calendar date in 2025 | Exactly one value for every date from 2025-01-01 through 2025-12-31 |
| `event_count` | Number of eligible historical events for that date | Non-negative integer; zero when no event matches |

Relationship: one Analysis Run has exactly 365 Annual Daily Count values. Their sum equals the historical event count for the selected threshold and geographic filters.

### Regional Event Summary

An aggregate for one declared geographic group and analysis period.

| Attribute | Meaning | Validation |
|---|---|---|
| `period` | Recent 24-hour or historical 2025 population | Exact period bounds recorded |
| `geographic_group` | Country or declared region | Grouping definition and filters recorded |
| `assigned_event_count` | Events assigned to a country | Non-negative integer |
| `unassigned_event_count` | Events with the `N/A` country category | Non-negative integer |
| `eligible_event_count` | Events in the denominator | Must equal assigned plus unassigned counts |
| `assigned_share`, `unassigned_share` | Fractions of eligible events | Numerators/denominator recorded; shares reconcile to 1 within documented rounding, or both are null for an empty population |

This entity supports the first conclusion for both recent and historical periods. “Sin país asignado” means no point-in-polygon match in the selected country catalogue; it is not direct proof that every such event is submarine.

### Depth Population

The set of eligible records used for a depth percentile. The final conclusion uses the 2025 historical population; the dashboard endpoint also reports p90 for its selected live or run-scoped replay population.

| Attribute | Meaning | Validation |
|---|---|---|
| `scope` | Historical 2025, live, or a specific replay run | Must identify the data relation and replay run where applicable |
| `period_start_utc`, `period_end_utc` | Applied event-time interval | UTC and start < end; values match the declared cohort |
| `geographic_group` | Country or declared region summarized by the result | Grouping definition is recorded |
| `geographic_filters` | Applied country, continent, and subregion filters | Match the declared analysis filters; live dashboard results match the selected filters |
| `depth_population_count` | Count of finite, non-null depths | Non-negative; no null-to-zero conversion |
| `depth_p90_km` | 90th percentile depth | Null iff population is empty; km; Hyndman–Fan Type 7 |

### Analytical Result and Conclusion

An analytical result stores an exact value plus the context needed to interpret it. A conclusion references one or more analytical results and separates the observation from its interpretation.

Required context includes population, period, filters, threshold where applicable, units, calculation method, and relevant limitations. Percentages must have explicit numerator and denominator. Percentile depth excludes unavailable values and reports its eligible population count.

The three required conclusion families use M≥4.5 and declared geographic filters: (1) assigned versus unassigned shares in recent and historical cohorts; (2) 2025 depth distribution and Type 7 p90 by declared geographic area; and (3) the recent count compared with the 2025 daily mean and population standard deviation, including whether the absolute standardized deviation exceeds one or two standard deviations. The comparison is descriptive, not predictive.

### Evidence Capture

A dashboard image tied to an Analysis Run and identifying visible filters and period. It must not be used to claim evidence for an indicator that is not actually visible.

## Derived comparison metrics

For the annual daily counts \(x_1,\ldots,x_{365}\):

- `historical_2025_event_count` = \(\sum x_i\).
- `historical_daily_average` = \(\sum x_i/365\).
- `historical_daily_population_stddev` = \(\sqrt{\sum(x_i-\mu)^2/365}\).
- `recent_event_count` = eligible live events in the exact rolling 24-hour interval.
- `recent_standard_deviations_from_mean` = \((recent\_event\_count-\mu)/\sigma\), undefined when \(\sigma=0\).
- `recent_to_historical_daily_average_ratio` = `recent_event_count / historical_daily_average`, undefined when the historical daily average is zero.

Both cohorts use the same M≥4.5 condition and the same geographic filter values. The z-score describes deviation from this fixed-year reference; it is not a forecast or seismic-risk estimate.
