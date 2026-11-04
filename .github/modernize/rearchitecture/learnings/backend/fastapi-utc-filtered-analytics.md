# FastAPI UTC and Scope-Safe Analytics

Keep API timestamps UTC, bind filter values, and select live/replay relations from a fixed allowlist so analytics cannot silently cross data scopes.

## What Happened

During `Observatorio-de-actividad-s-smica` task `t15`, the FastAPI routes were aligned to the architect contract and the actual PostgreSQL column names. A shared filter parser normalizes aware timestamps to UTC, defaults event analytics to a 24-hour window, rejects naive dates and invalid bounds, and requires `run_id` for replay. SQL predicates use bound values, while relation names come only from the fixed scope mapping. The historical comparison uses a fixed 365-day denominator even though the baseline is partitioned monthly.

Runtime probes against PostgreSQL confirmed the 2025 baseline count and filterable route behavior. The aggregate backend suite passes in the consumer image because it mounts the Natural Earth file required by spatial tests; the API-only image does not mount that file.

## Takeaway

- Preserve UTC on input and output; serialize API instants with `Z`.
- Compute feed freshness from source `updated_utc`, separately from the time the event was persisted (`ingested_at`).
- Bind all user filters as query parameters; whitelist any dynamic table selection.
- Replay queries must require a run ID and must never fall back to live tables.
- Keep comparison windows fixed by contract and spell out zero-denominator behavior.
- Run the focused API contract tests and the whole backend regression suite in the test image that supplies required shared fixtures.

## History

- 2026-11-02 (`Observatorio-de-actividad-s-smica/t15`): initial
