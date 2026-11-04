# Consumer Quality, Spatial Lookup, and Persistence

For the seismic consumer, validate the canonical envelope before enrichment, repair invalid Natural Earth polygons in memory, and commit Kafka only after the record's PostgreSQL transaction succeeds.

## What Happened

_Discovered in `Observatorio-de-actividad-s-smica` during task `t12` while integrating the checked-in Natural Earth GeoJSON with the PostgreSQL consumer._

Natural Earth 1:110m contains an invalid USA polygon; Shapely 2's `STRtree` query returns integer indexes. `make_valid` repairs polygon topology for the in-memory lookup while preserving the original file and attributes. Use `intersects` so shared boundaries are considered, then select the lexicographically smallest `ADM0_A3`. An initial Chile fixture coordinate was offshore; confirmed -70,-30 as an inland point against the supplied map.

The existing schema's event payload column is `raw_payload`, and country foreign keys require seeding `dim_countries` before consuming. Keep each event UPSERT and version append in one transaction; only append a version for a strictly newer accepted row. Quarantine deduplication is keyed by Kafka topic, partition, and offset.

Kafka tombstones arrive with no value bytes; represent that missing payload as JSON `null` in quarantine so the schema constraint is met and the offset remains safely committable.

## Takeaway

- Pin Shapely 2 when using integer-index STRtree results.
- Keep longitude/latitude order and never infer an ocean country from `place` or nearest distance.
- Preserve `NULL`/negative measurements; let the database enforce its existing relations and column names.
- For each consumed record, persist the event/audit/quarantine outcome first, then commit exactly that partition's next offset.
- Store tombstones as JSON `null` when the quarantine table requires at least one raw representation.

## History

- 2026-11-02 (`Observatorio-de-actividad-s-smica/t12`): initial
