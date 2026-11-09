-- PostgreSQL 16 schema for the local seismic-observatory MVP.
--
-- This file is intentionally re-runnable against a database initialized with
-- this schema. The PostgreSQL image runs it only for a new data volume; it is
-- not a replacement for forward migrations when an existing schema changes.
-- All application timestamps are instants (TIMESTAMPTZ) and clients must use
-- UTC. No PostGIS extension is required; spatial assignment is done by the
-- consumer before persistence.

BEGIN;

CREATE TABLE IF NOT EXISTS dataset_imports (
    dataset_key   TEXT PRIMARY KEY,
    event_count   BIGINT NOT NULL CHECK (event_count >= 0),
    imported_at   TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS dim_countries (
    adm0_a3       VARCHAR(8) PRIMARY KEY,
    name_es       TEXT,
    admin_name    TEXT NOT NULL,
    display_name  TEXT NOT NULL,
    continent     TEXT,
    subregion     TEXT,
    source_props  JSONB NOT NULL DEFAULT '{}'::JSONB,
    CONSTRAINT ck_dim_countries_code_nonempty CHECK (length(adm0_a3) > 0),
    CONSTRAINT ck_dim_countries_admin_nonempty CHECK (length(admin_name) > 0),
    CONSTRAINT ck_dim_countries_display_nonempty CHECK (length(display_name) > 0)
);

-- A real dimension member lets all valid maritime events retain a country FK.
INSERT INTO dim_countries (
    adm0_a3, name_es, admin_name, display_name, continent, subregion, source_props
)
VALUES (
    'N/A', NULL, 'Sin país asignado', 'Sin país asignado', NULL, NULL,
    '{"kind":"unassigned"}'::JSONB
)
ON CONFLICT (adm0_a3) DO UPDATE
SET name_es = EXCLUDED.name_es,
    admin_name = EXCLUDED.admin_name,
    display_name = EXCLUDED.display_name,
    continent = EXCLUDED.continent,
    subregion = EXCLUDED.subregion,
    source_props = EXCLUDED.source_props;

-- Live/current state is deliberately NOT partitioned: event_id must be a
-- globally unique conflict target for strict, revision-aware UPSERTs.
CREATE TABLE IF NOT EXISTS current_earthquakes (
    event_id       VARCHAR(32) PRIMARY KEY,
    mag            DOUBLE PRECISION,
    mag_type       VARCHAR(16),
    depth_km       DOUBLE PRECISION NOT NULL,
    time_utc       TIMESTAMPTZ NOT NULL,
    updated_utc    TIMESTAMPTZ NOT NULL,
    ingested_at    TIMESTAMPTZ NOT NULL,
    adm0_a3        VARCHAR(8) NOT NULL REFERENCES dim_countries(adm0_a3),
    place          TEXT,
    geom_lon       DOUBLE PRECISION NOT NULL,
    geom_lat       DOUBLE PRECISION NOT NULL,
    source         VARCHAR(32) NOT NULL DEFAULT 'usgs_live',
    content_hash   VARCHAR(80),
    raw_payload    JSONB NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_current_source_live CHECK (source = 'usgs_live'),
    CONSTRAINT ck_current_mag_finite CHECK (
        mag IS NULL OR mag::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
    ),
    CONSTRAINT ck_current_depth_finite CHECK (
        depth_km::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
    ),
    CONSTRAINT ck_current_lon_range CHECK (geom_lon BETWEEN -180 AND 180),
    CONSTRAINT ck_current_lat_range CHECK (geom_lat BETWEEN -90 AND 90),
    CONSTRAINT ck_current_time_order CHECK (time_utc <= updated_utc)
);

CREATE INDEX IF NOT EXISTS idx_current_earthquakes_time
    ON current_earthquakes (time_utc DESC);
CREATE INDEX IF NOT EXISTS idx_current_earthquakes_mag
    ON current_earthquakes (mag) WHERE mag IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_current_earthquakes_adm0
    ON current_earthquakes (adm0_a3);
CREATE INDEX IF NOT EXISTS idx_current_earthquakes_country_time
    ON current_earthquakes (adm0_a3, time_utc DESC);

-- Immutable 2025 baseline. PostgreSQL requires a partition key to be present
-- in every unique constraint on a partitioned table. The unpartitioned key
-- registry preserves global event_id uniqueness across the monthly partitions.
CREATE TABLE IF NOT EXISTS historical_2025_event_keys (
    event_id      VARCHAR(32) PRIMARY KEY,
    occurred_utc  TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_historical_2025_key_pair UNIQUE (event_id, occurred_utc),
    CONSTRAINT ck_historical_2025_key_year CHECK (
        occurred_utc >= TIMESTAMPTZ '2025-01-01 00:00:00+00'
        AND occurred_utc < TIMESTAMPTZ '2026-01-01 00:00:00+00'
    )
);

CREATE TABLE IF NOT EXISTS historical_2025 (
    event_id       VARCHAR(32) NOT NULL,
    time_utc       TIMESTAMPTZ NOT NULL,
    mag            DOUBLE PRECISION NOT NULL,
    mag_type       VARCHAR(16),
    depth_km       DOUBLE PRECISION NOT NULL,
    updated_utc    TIMESTAMPTZ NOT NULL,
    ingested_at    TIMESTAMPTZ NOT NULL,
    adm0_a3        VARCHAR(8) NOT NULL REFERENCES dim_countries(adm0_a3),
    place          TEXT,
    geom_lon       DOUBLE PRECISION NOT NULL,
    geom_lat       DOUBLE PRECISION NOT NULL,
    source         VARCHAR(32) NOT NULL DEFAULT 'usgs_2025',
    content_hash   VARCHAR(80),
    raw_payload    JSONB NOT NULL,
    PRIMARY KEY (event_id, time_utc),
    CONSTRAINT fk_historical_2025_global_event_key
        FOREIGN KEY (event_id, time_utc)
        REFERENCES historical_2025_event_keys (event_id, occurred_utc)
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT ck_historical_2025_source CHECK (source = 'usgs_2025'),
    CONSTRAINT ck_historical_2025_mag_finite CHECK (
        mag::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
    ),
    CONSTRAINT ck_historical_2025_mag_threshold CHECK (mag >= 4.0),
    CONSTRAINT ck_historical_2025_depth_finite CHECK (
        depth_km::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
    ),
    CONSTRAINT ck_historical_2025_lon_range CHECK (geom_lon BETWEEN -180 AND 180),
    CONSTRAINT ck_historical_2025_lat_range CHECK (geom_lat BETWEEN -90 AND 90),
    CONSTRAINT ck_historical_2025_time_order CHECK (time_utc <= updated_utc),
    CONSTRAINT ck_historical_2025_time_window CHECK (
        time_utc >= TIMESTAMPTZ '2025-01-01 00:00:00+00'
        AND time_utc < TIMESTAMPTZ '2026-01-01 00:00:00+00'
    )
) PARTITION BY RANGE (time_utc);

CREATE TABLE IF NOT EXISTS historical_2025_01 PARTITION OF historical_2025
    FOR VALUES FROM (TIMESTAMPTZ '2025-01-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2025-02-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS historical_2025_02 PARTITION OF historical_2025
    FOR VALUES FROM (TIMESTAMPTZ '2025-02-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2025-03-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS historical_2025_03 PARTITION OF historical_2025
    FOR VALUES FROM (TIMESTAMPTZ '2025-03-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2025-04-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS historical_2025_04 PARTITION OF historical_2025
    FOR VALUES FROM (TIMESTAMPTZ '2025-04-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2025-05-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS historical_2025_05 PARTITION OF historical_2025
    FOR VALUES FROM (TIMESTAMPTZ '2025-05-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2025-06-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS historical_2025_06 PARTITION OF historical_2025
    FOR VALUES FROM (TIMESTAMPTZ '2025-06-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2025-07-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS historical_2025_07 PARTITION OF historical_2025
    FOR VALUES FROM (TIMESTAMPTZ '2025-07-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2025-08-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS historical_2025_08 PARTITION OF historical_2025
    FOR VALUES FROM (TIMESTAMPTZ '2025-08-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2025-09-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS historical_2025_09 PARTITION OF historical_2025
    FOR VALUES FROM (TIMESTAMPTZ '2025-09-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2025-10-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS historical_2025_10 PARTITION OF historical_2025
    FOR VALUES FROM (TIMESTAMPTZ '2025-10-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2025-11-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS historical_2025_11 PARTITION OF historical_2025
    FOR VALUES FROM (TIMESTAMPTZ '2025-11-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2025-12-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS historical_2025_12 PARTITION OF historical_2025
    FOR VALUES FROM (TIMESTAMPTZ '2025-12-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2026-01-01 00:00:00+00');

-- Complete the circular, deferred relationship after both sides exist. This
-- prevents orphan registry rows while still allowing both rows to be written
-- atomically in either order inside one transaction.
DO $schema$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_historical_2025_key_fact'
          AND conrelid = 'historical_2025_event_keys'::REGCLASS
    ) THEN
        ALTER TABLE historical_2025_event_keys
            ADD CONSTRAINT fk_historical_2025_key_fact
            FOREIGN KEY (event_id, occurred_utc)
            REFERENCES historical_2025 (event_id, time_utc)
            DEFERRABLE INITIALLY DEFERRED;
    END IF;
END
$schema$;

CREATE INDEX IF NOT EXISTS idx_historical_2025_time_mag
    ON historical_2025 (time_utc, mag);
CREATE INDEX IF NOT EXISTS idx_historical_2025_country_time
    ON historical_2025 (adm0_a3, time_utc);

-- Append-only snapshots, range partitioned by revision time. The primary key
-- includes updated_utc as required by PostgreSQL's partition uniqueness rules.
CREATE TABLE IF NOT EXISTS earthquake_versions (
    event_id       VARCHAR(32) NOT NULL REFERENCES current_earthquakes(event_id),
    updated_utc    TIMESTAMPTZ NOT NULL,
    ingested_at    TIMESTAMPTZ NOT NULL,
    mag            DOUBLE PRECISION,
    mag_type       VARCHAR(16),
    depth_km       DOUBLE PRECISION NOT NULL,
    time_utc       TIMESTAMPTZ NOT NULL,
    adm0_a3        VARCHAR(8) NOT NULL REFERENCES dim_countries(adm0_a3),
    place          TEXT,
    geom_lon       DOUBLE PRECISION NOT NULL,
    geom_lat       DOUBLE PRECISION NOT NULL,
    source         VARCHAR(32) NOT NULL DEFAULT 'usgs_live',
    content_hash   VARCHAR(80),
    raw_payload    JSONB NOT NULL,
    PRIMARY KEY (event_id, updated_utc),
    CONSTRAINT ck_earthquake_versions_source CHECK (source = 'usgs_live'),
    CONSTRAINT ck_earthquake_versions_mag_finite CHECK (
        mag IS NULL OR mag::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
    ),
    CONSTRAINT ck_earthquake_versions_depth_finite CHECK (
        depth_km::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
    ),
    CONSTRAINT ck_earthquake_versions_lon_range CHECK (geom_lon BETWEEN -180 AND 180),
    CONSTRAINT ck_earthquake_versions_lat_range CHECK (geom_lat BETWEEN -90 AND 90),
    CONSTRAINT ck_earthquake_versions_time_order CHECK (time_utc <= updated_utc)
) PARTITION BY RANGE (updated_utc);

CREATE TABLE IF NOT EXISTS earthquake_versions_2024 PARTITION OF earthquake_versions
    FOR VALUES FROM (TIMESTAMPTZ '2024-01-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2025-01-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS earthquake_versions_2025 PARTITION OF earthquake_versions
    FOR VALUES FROM (TIMESTAMPTZ '2025-01-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2026-01-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS earthquake_versions_2026 PARTITION OF earthquake_versions
    FOR VALUES FROM (TIMESTAMPTZ '2026-01-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2027-01-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS earthquake_versions_2027 PARTITION OF earthquake_versions
    FOR VALUES FROM (TIMESTAMPTZ '2027-01-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2028-01-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS earthquake_versions_2028 PARTITION OF earthquake_versions
    FOR VALUES FROM (TIMESTAMPTZ '2028-01-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2029-01-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS earthquake_versions_2029 PARTITION OF earthquake_versions
    FOR VALUES FROM (TIMESTAMPTZ '2029-01-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2030-01-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS earthquake_versions_2030 PARTITION OF earthquake_versions
    FOR VALUES FROM (TIMESTAMPTZ '2030-01-01 00:00:00+00')
                 TO (TIMESTAMPTZ '2031-01-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS earthquake_versions_default PARTITION OF earthquake_versions DEFAULT;

CREATE INDEX IF NOT EXISTS idx_earthquake_versions_event_time
    ON earthquake_versions (event_id, updated_utc DESC);

-- Kafka offsets make quarantine writes idempotent even if the DB transaction
-- commits but the consumer crashes before committing the broker offset.
CREATE TABLE IF NOT EXISTS quarantine_events (
    quarantine_id      BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    source_event_id    VARCHAR(64),
    failure_reason     VARCHAR(128) NOT NULL,
    failure_detail     TEXT,
    raw_payload        JSONB,
    raw_message        BYTEA,
    quarantined_at     TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    source_topic       VARCHAR(128) NOT NULL DEFAULT 'earthquakes.live',
    source_partition   INTEGER NOT NULL,
    source_offset      BIGINT NOT NULL,
    CONSTRAINT uq_quarantine_live_kafka_offset
        UNIQUE (source_topic, source_partition, source_offset),
    CONSTRAINT ck_quarantine_live_topic CHECK (source_topic = 'earthquakes.live'),
    CONSTRAINT ck_quarantine_live_position CHECK (source_partition >= 0 AND source_offset >= 0),
    CONSTRAINT ck_quarantine_live_raw CHECK (raw_payload IS NOT NULL OR raw_message IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_quarantine_events_time
    ON quarantine_events (quarantined_at DESC);

CREATE TABLE IF NOT EXISTS ingestion_audit (
    poll_id             VARCHAR(64) PRIMARY KEY,
    source              VARCHAR(32) NOT NULL,
    requested_at        TIMESTAMPTZ NOT NULL,
    completed_at        TIMESTAMPTZ NOT NULL,
    http_status         SMALLINT,
    content_hash        VARCHAR(80),
    records_received    INTEGER NOT NULL DEFAULT 0,
    records_accepted    INTEGER NOT NULL DEFAULT 0,
    records_excluded    INTEGER NOT NULL DEFAULT 0,
    records_quarantined INTEGER NOT NULL DEFAULT 0,
    status              VARCHAR(16) NOT NULL,
    error_code          VARCHAR(64),
    error_message       TEXT,
    CONSTRAINT ck_ingestion_audit_source CHECK (source IN ('usgs_live', 'usgs_2025')),
    CONSTRAINT ck_ingestion_audit_status CHECK (status IN ('succeeded', 'failed', 'partial')),
    CONSTRAINT ck_ingestion_audit_time CHECK (completed_at >= requested_at),
    CONSTRAINT ck_ingestion_audit_counts CHECK (
        records_received >= 0 AND records_accepted >= 0
        AND records_excluded >= 0 AND records_quarantined >= 0
    ),
    CONSTRAINT ck_ingestion_audit_http_status CHECK (
        http_status IS NULL OR http_status BETWEEN 100 AND 599
    )
);
CREATE INDEX IF NOT EXISTS idx_ingestion_audit_completed
    ON ingestion_audit (completed_at DESC);

-- Replay records use separate, non-partitioned tables so (run_id,event_id)
-- remains a global unique UPSERT target and cannot mutate live/baseline rows.
CREATE TABLE IF NOT EXISTS replay_runs (
    run_id               VARCHAR(64) PRIMARY KEY,
    status               VARCHAR(16) NOT NULL,
    source               VARCHAR(32) NOT NULL DEFAULT 'usgs_replay',
    started_at           TIMESTAMPTZ NOT NULL,
    finished_at          TIMESTAMPTZ,
    events_received      INTEGER NOT NULL DEFAULT 0,
    events_processed     INTEGER NOT NULL DEFAULT 0,
    events_quarantined   INTEGER NOT NULL DEFAULT 0,
    error_message        TEXT,
    CONSTRAINT ck_replay_runs_status CHECK (
        status IN ('starting', 'running', 'completed', 'failed')
    ),
    CONSTRAINT ck_replay_runs_source CHECK (source = 'usgs_replay'),
    CONSTRAINT ck_replay_runs_counts CHECK (
        events_received >= 0 AND events_processed >= 0 AND events_quarantined >= 0
    ),
    CONSTRAINT ck_replay_runs_time CHECK (
        finished_at IS NULL OR finished_at >= started_at
    )
);
CREATE INDEX IF NOT EXISTS idx_replay_runs_started
    ON replay_runs (started_at DESC);

CREATE TABLE IF NOT EXISTS replay_earthquakes (
    run_id         VARCHAR(64) NOT NULL REFERENCES replay_runs(run_id),
    event_id       VARCHAR(32) NOT NULL,
    mag            DOUBLE PRECISION,
    mag_type       VARCHAR(16),
    depth_km       DOUBLE PRECISION NOT NULL,
    time_utc       TIMESTAMPTZ NOT NULL,
    updated_utc    TIMESTAMPTZ NOT NULL,
    ingested_at    TIMESTAMPTZ NOT NULL,
    adm0_a3        VARCHAR(8) NOT NULL REFERENCES dim_countries(adm0_a3),
    place          TEXT,
    geom_lon       DOUBLE PRECISION NOT NULL,
    geom_lat       DOUBLE PRECISION NOT NULL,
    source         VARCHAR(32) NOT NULL DEFAULT 'usgs_replay',
    content_hash   VARCHAR(80),
    raw_payload    JSONB NOT NULL,
    PRIMARY KEY (run_id, event_id),
    CONSTRAINT ck_replay_earthquakes_source CHECK (source = 'usgs_replay'),
    CONSTRAINT ck_replay_earthquakes_mag_finite CHECK (
        mag IS NULL OR mag::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
    ),
    CONSTRAINT ck_replay_earthquakes_depth_finite CHECK (
        depth_km::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
    ),
    CONSTRAINT ck_replay_earthquakes_lon_range CHECK (geom_lon BETWEEN -180 AND 180),
    CONSTRAINT ck_replay_earthquakes_lat_range CHECK (geom_lat BETWEEN -90 AND 90),
    CONSTRAINT ck_replay_earthquakes_time_order CHECK (time_utc <= updated_utc)
);
CREATE INDEX IF NOT EXISTS idx_replay_earthquakes_run_time
    ON replay_earthquakes (run_id, time_utc DESC);
CREATE INDEX IF NOT EXISTS idx_replay_earthquakes_run_country_time
    ON replay_earthquakes (run_id, adm0_a3, time_utc);

CREATE TABLE IF NOT EXISTS replay_versions (
    run_id         VARCHAR(64) NOT NULL,
    event_id       VARCHAR(32) NOT NULL,
    updated_utc    TIMESTAMPTZ NOT NULL,
    ingested_at    TIMESTAMPTZ NOT NULL,
    mag            DOUBLE PRECISION,
    mag_type       VARCHAR(16),
    depth_km       DOUBLE PRECISION NOT NULL,
    time_utc       TIMESTAMPTZ NOT NULL,
    adm0_a3        VARCHAR(8) NOT NULL REFERENCES dim_countries(adm0_a3),
    place          TEXT,
    geom_lon       DOUBLE PRECISION NOT NULL,
    geom_lat       DOUBLE PRECISION NOT NULL,
    source         VARCHAR(32) NOT NULL DEFAULT 'usgs_replay',
    content_hash   VARCHAR(80),
    raw_payload    JSONB NOT NULL,
    PRIMARY KEY (run_id, event_id, updated_utc),
    FOREIGN KEY (run_id, event_id)
        REFERENCES replay_earthquakes (run_id, event_id),
    CONSTRAINT ck_replay_versions_source CHECK (source = 'usgs_replay'),
    CONSTRAINT ck_replay_versions_mag_finite CHECK (
        mag IS NULL OR mag::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
    ),
    CONSTRAINT ck_replay_versions_depth_finite CHECK (
        depth_km::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
    ),
    CONSTRAINT ck_replay_versions_lon_range CHECK (geom_lon BETWEEN -180 AND 180),
    CONSTRAINT ck_replay_versions_lat_range CHECK (geom_lat BETWEEN -90 AND 90),
    CONSTRAINT ck_replay_versions_time_order CHECK (time_utc <= updated_utc)
);
CREATE INDEX IF NOT EXISTS idx_replay_versions_run_event_time
    ON replay_versions (run_id, event_id, updated_utc DESC);

CREATE TABLE IF NOT EXISTS replay_quarantine_events (
    quarantine_id      BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    run_id             VARCHAR(64) REFERENCES replay_runs(run_id),
    source_event_id    VARCHAR(64),
    failure_reason     VARCHAR(128) NOT NULL,
    failure_detail     TEXT,
    raw_payload        JSONB,
    raw_message        BYTEA,
    quarantined_at     TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    source_topic       VARCHAR(128) NOT NULL DEFAULT 'earthquakes.replay',
    source_partition   INTEGER NOT NULL,
    source_offset      BIGINT NOT NULL,
    CONSTRAINT uq_replay_quarantine_kafka_offset
        UNIQUE (source_topic, source_partition, source_offset),
    CONSTRAINT ck_replay_quarantine_topic CHECK (source_topic = 'earthquakes.replay'),
    CONSTRAINT ck_replay_quarantine_position CHECK (
        source_partition >= 0 AND source_offset >= 0
    ),
    CONSTRAINT ck_replay_quarantine_raw CHECK (
        raw_payload IS NOT NULL OR raw_message IS NOT NULL
    )
);
CREATE INDEX IF NOT EXISTS idx_replay_quarantine_run_time
    ON replay_quarantine_events (run_id, quarantined_at DESC);

-- Canonical live persistence transaction (perform every statement in one
-- PostgreSQL transaction; commit the Kafka offset only after COMMIT succeeds):
--
--   INSERT INTO current_earthquakes (...)
--   VALUES (...)
--   ON CONFLICT (event_id) DO UPDATE SET
--       mag = EXCLUDED.mag, mag_type = EXCLUDED.mag_type,
--       depth_km = EXCLUDED.depth_km, time_utc = EXCLUDED.time_utc,
--       updated_utc = EXCLUDED.updated_utc, ingested_at = EXCLUDED.ingested_at,
--       adm0_a3 = EXCLUDED.adm0_a3, place = EXCLUDED.place,
--       geom_lon = EXCLUDED.geom_lon, geom_lat = EXCLUDED.geom_lat,
--       content_hash = EXCLUDED.content_hash, raw_payload = EXCLUDED.raw_payload
--   WHERE EXCLUDED.updated_utc > current_earthquakes.updated_utc
--   RETURNING event_id, updated_utc;
--
-- Only when RETURNING yields a row, append the same accepted snapshot to
-- earthquake_versions with ON CONFLICT (event_id, updated_utc) DO NOTHING.
-- Equal/older revisions have no effect on current state or version count.
--
-- Canonical historical bootstrap: in the same transaction, insert the
-- (event_id, time_utc) pair into historical_2025_event_keys with
-- ON CONFLICT (event_id) DO NOTHING, then insert historical_2025 with
-- ON CONFLICT (event_id, time_utc) DO NOTHING. The deferred FK rejects an
-- event_id already registered against a different occurrence timestamp.
--
-- Replay uses equivalent strict-newer UPSERT semantics on
-- replay_earthquakes (run_id, event_id), records accepted revisions in
-- replay_versions, and never writes to current_earthquakes or historical_2025.

COMMIT;
