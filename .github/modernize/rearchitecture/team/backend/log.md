## [t9] Implemented the USGS live producer
- The canonical live route is `earthquakes.live`; event envelopes use `source=usgs_live`, while poll status/control records use `record_type=poll_audit` and a `poll_id` key.
- Deduplication is by `event_id` and strictly newer `updated_ms`; update local state only after `send_and_wait` succeeds so an unacknowledged event retries on the next poll.
- Keep poll-audit content hashes over the original HTTP response bytes and event hashes over canonical Feature JSON. Serialize non-finite source numbers (`NaN`/infinity or overflowing exponents) as strings so Kafka receives valid JSON and downstream quality checks can quarantine them.
- The producer keeps HTTP retry handling in `usgs_client.py` and event/Kafka orchestration in `main.py`; transient source failures generate safe poll-audit records without embedding response bodies or credentials.
- Workflow `context.md`, `decisions.md`, and prior backend log/inbox were absent; canonical decisions came from t3 and t8 artifacts. The initial shared requirements manifest contains producer dependencies only; downstream backend owners must extend it.
- Learnings consumed: [(none)].

## [t12] Implemented live quality and spatial event processing
- Followed the t3 envelope, t10 SQL schema, and t11 Natural Earth file path. The current schema uses `raw_payload` and requires real country rows in `dim_countries`, so the consumer seeds those rows at startup before consuming.
- The Natural Earth 1:110m USA geometry is invalid under GEOS; using Shapely `make_valid` plus polygonal filtering repaired it for the in-memory tree while leaving the source data/properties untouched.
- Corrected a bad Chile test coordinate: longitude -71.5 at latitude -30 is offshore in this simplified dataset; -70.0 maps to CHL.
- One transaction per record; explicit `TopicPartition -> OffsetAndMetadata(offset + 1)` after event, audit, or quarantine persistence. PostgreSQL integration and a Kafka-to-PostgreSQL smoke confirmed the contract.
- Kafka tombstones have no `value` bytes; store JSON `null` in quarantine to satisfy the existing raw-data constraint instead of leaving a poison offset permanently uncommitted.
- Canonical live topic is `earthquakes.live`; this task leaves replay routing for its dependent task.
- Learnings consumed: [backend/usgs-live-envelope-and-dedupe].

## [t14] Imported the partitioned 2025 baseline
- The FDSNWS catalog was successfully cached as 12 monthly GeoJSON files in the named `USGS_CACHE_DIR` volume; 18,302 unique M4+ features were imported.
- Keep cache files out of Git and require the checksum-verified completion manifest before import. The consumer sees the shared volume read-only.
- Historical persistence is separate from live/current state. Import the registry and monthly fact rows in a single transaction; repeat imports are immutable and idempotent.
- Month-level USGS requests completed below the 18,000 threshold, so the recursive subdivision branch was covered by deterministic mock tests rather than the live catalog.
- Tests consumed the real imported database after the first run; the second run kept the baseline at 18,302 rows and all 12 partitions.
- Learnings consumed: [backend/consumer-quality-spatial-persistence].

## [t15] Implemented FastAPI contracts and analytics
- The API uses the architect's routes and the checked schema names; live is the default, replay requires a run ID, and replay never falls back to live.
- Common event filters normalize offset-aware times to UTC, default to the previous 24h, enforce start-inclusive/end-exclusive ranges, and bind all values; only fixed allowlisted table names are interpolated.
- Historical comparison uses current live M4+ events over the rolling 24h versus baseline count / 365; no replay enters this comparison.
- Health freshness `ingestion_delay_seconds` is calculated from `now - latest updated_utc`; latest `ingested_at` remains a separate response field.
- FastAPI/Pydantic serialize UTC timestamps with `Z`; local CORS explicitly allows `ngrok-skip-browser-warning`.
- Focused API tests passed 7/7; complete suite passed 52 tests with 5 skipped in the consumer image, whose Natural Earth mount is required by spatial tests. Runtime routes passed against PostgreSQL with 18,302 baseline rows.
- Learnings consumed: [backend/consumer-quality-spatial-persistence, backend/historical-2025-baseline, backend/usgs-live-envelope-and-dedupe].

## [t16] Implemented isolated replay production and persistence
- Reused the verified 2025 cache and canonical `earthquakes.replay` topic; start/event/finish messages are acknowledged sequentially and all state is scoped to a `run_id`.
- The existing schema already had replay run/event/version/quarantine relations, so no DDL change was needed. Consumer transactions now keep replay and live persistence paths separate and finish PostgreSQL work before committing the corresponding Kafka offset.
- Equal/older replay revisions return “message accepted” while only a strictly newer revision creates a new replay version. This distinction prevents a valid duplicate from being wrongly quarantined.
- A June 2025 end-to-end replay persisted 1,157 run-scoped rows and 1,158 versions with no quarantines; the replay consumer offset reached log-end with zero lag. The smoke run data was deleted after validation.
- The first test run caught an indentation regression when moving quarantine code; restored the live writer body and reran the full suite and database integration tests successfully.
- `context.md`, `decisions.md`, and `team/backend/inbox.md` were absent; canonical replay rules came from t3/t10 and the project specifications.
- Learnings consumed: [backend/consumer-quality-spatial-persistence, backend/historical-2025-baseline, backend/usgs-live-envelope-and-dedupe].

## [t18] Exposed run-scoped replay API state
- The architect's route inventory specified `/api/v1/replay/state`, while the existing DB schema constrained persisted statuses to `starting`, `running`, `completed`, and `failed`.
- Added a response-only `idle` state for an empty registry, and derived `active` strictly from `starting`/`running`; no replay event or live table is queried.
- Newest-run selection is deterministic (`started_at DESC, run_id DESC`); use the DTO's UTC `Z` serializer for lifecycle timestamps.
- The focused API contract tests passed 10/10; the empty-registry HTTP probe returned 200 against PostgreSQL.
- Learnings consumed: [backend/fastapi-utc-filtered-analytics, backend/replay-run-scoped-persistence].
