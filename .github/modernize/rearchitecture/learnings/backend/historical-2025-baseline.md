# Historical 2025 Baseline Import

Use the producer's persistent cache for USGS monthly GeoJSON and import the validated immutable baseline through the consumer, not through live Kafka rows.

## What Happened

In `Observatorio-de-actividad-s-smica` task `t14`, the monthly files were kept under `$USGS_CACHE_DIR/historical/`, matching the shared named-volume architecture rather than committing data under the repository. A checksum manifest makes the download resumable and prevents the consumer from importing incomplete/tampered month files. The importer uses the existing Natural Earth STRtree and writes the ID registry plus all monthly fact rows in one PostgreSQL transaction; conflict handling is immutable and the full import succeeded with 18,302 unique events.

The consumer container mounts the USGS volume read-only, so only the producer writes cache/manifest data. The importer should not try to write an import marker there; its all-or-nothing DB transaction avoids exposing a partially imported baseline.

## Takeaway

- Keep historical rows out of `current_earthquakes` and do not wrap them as `mode=live`.
- Use half-open UTC intervals and still deduplicate `event_id` across files before persistence.
- Import the key registry and partitioned fact table in the same transaction because their foreign keys are deferred and circular.
- Preserve `source=usgs_2025`, original Feature payload, negative depths, and the source revision timestamp.
- Use a verified completion manifest as the gate for import; a failed/partial download must not be interpreted as a complete baseline.

## History

- 2026-11-02 (`Observatorio-de-actividad-s-smica/t14`): initial
