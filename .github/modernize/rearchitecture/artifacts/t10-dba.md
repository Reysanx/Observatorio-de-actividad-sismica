# t10 — PostgreSQL Schema Contract Verification

## Result

**PASS.** `backend/db/init.sql` executes on PostgreSQL 16.4 and can be re-applied safely to a database initialized with the same schema. The key data-integrity, partitioning, replay-isolation, and idempotency contracts passed behavioral checks using disposable test rows.

## Contract Verified

- Canonical base relations: `dim_countries`, `current_earthquakes`, `earthquake_versions`, `historical_2025_event_keys`, `historical_2025`, `quarantine_events`, and `ingestion_audit`.
- Replay is isolated in `replay_runs`, `replay_earthquakes`, `replay_versions`, and `replay_quarantine_events`; replay events are run-scoped.
- `current_earthquakes.event_id` remains a global primary key suitable for `ON CONFLICT (event_id)`. The schema permits null magnitude and negative magnitude/depth values, and validates coordinate bounds.
- Historical facts use 12 monthly 2025 partitions. The unpartitioned identity registry preserves global event IDs while the deferred foreign keys allow the registry and fact row to be committed atomically.
- `earthquake_versions` has year partitions for 2024–2030 and a default partition. Quarantine deduplication is keyed by Kafka topic, partition, and offset.
- Database timestamps use `TIMESTAMPTZ`; country assignment is protected by the `dim_countries` foreign key and pre-seeded `N/A` member.
- The UPSERT rule is an application persistence contract documented in the schema: update current state only when `EXCLUDED.updated_utc > current_earthquakes.updated_utc`; append the accepted version and commit PostgreSQL before Kafka offset commit.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — canonical relation names, live/replay boundaries, and persistence ordering.
- `.github/modernize/rearchitecture/artifacts/t4-dba.md` — designed DDL, partitioning strategy, data constraints, and compatibility caveats.
- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — PostgreSQL/Docker toolchain preparation.
- `.github/modernize/rearchitecture/artifacts/t8-devops.md` and `t8-devops-runtime.md` — PostgreSQL 16 runtime image and Compose initialization behavior.

## Evidence Mapping

- `t3-architect.md#Decisions and Naming` and `t4-dba.md#Schema and Naming Decisions` → canonical live, baseline, audit, quarantine, and replay relations; confirmed in `backend/db/init.sql` and by successful PostgreSQL execution.
- `t3-architect.md#Processing and persistence boundaries` and `t4-dba.md#Persistence Contract` → strict-newer current UPSERT, isolated replay writes, and DB-before-offset sequence; strict-newer behavior and replay row isolation passed behavioral tests. Kafka offset ordering remains consumer-owned, not enforced by DDL.
- `t4-dba.md#Compatibility and Migration Notes` → repeatable initialization is for the same schema shape, not a forward migration; applying the file twice to PostgreSQL 16.4 succeeded.
- `specs/001-observatorio-sismico/data-spec.md#1.1-1.2`, `#3`, and `specs/001-observatorio-sismico/acceptance-tests.md#TC-02–TC-07/TC-11` → nullable/negative measurements, coordinate checks, monthly baseline partitioning, quarantine dedupe, and replay isolation; all corresponding database behaviors passed.
- `.agents/rules/data_quality_rules.md#1-3` and `.specify/memory/constitution.md#2.3-2.5` → NULL/negative-value preservation, country sentinel, quarantine, idempotency, and replay isolation; checked through the database fixture.

## Integration Handoff

No schema edits were needed. The consumer/API persistence call sites were not yet present in the workspace at verification time, so this result validates the database schema and contract behavior, not end-to-end SQL-to-application field binding. The producer is not a database writer under the approved service boundary. Downstream persistence code must use the exact column names in `backend/db/init.sql`, write the historical identity and fact rows in one transaction, append versions only for accepted strict-newer upserts, and keep replay writes within replay relations.

The script contains no destructive DDL. `CREATE ... IF NOT EXISTS` does not reconcile a pre-existing table with a different shape; future populated-volume changes still require explicit forward migrations and lock/rollback assessment.

## Test Results

- PostgreSQL image/runtime: `postgres:16.4-alpine`; container remained isolated, had no published host port, and was removed after testing.
- Command: `docker run --name t10-pg-schema-check -e POSTGRES_PASSWORD=t10-local-only -e POSTGRES_DB=t10_contract -d postgres:16.4-alpine`
  - Passed: 1; Failed: 0; Skipped: 0.
- Command: `Get-Content -Raw backend/db/init.sql | docker exec -i t10-pg-schema-check psql -v ON_ERROR_STOP=1 -U postgres -d t10_contract` — executed twice.
  - Passed: 2 schema applications; Failed: 0; Skipped: 0.
- Command: multiline PostgreSQL behavioral fixture piped to `docker exec -i t10-pg-schema-check psql -X -v ON_ERROR_STOP=1 -U postgres -d t10_contract`.
  - Passed: 8 contract checks; Failed: 0; Skipped: 0.
  - Verified nullable magnitude and negative depth, strict-newer UPSERT (equal/older ignored, newer accepted), monthly historical routing and magnitude threshold, two replay runs retaining the same event independently from live, duplicate Kafka-offset quarantine rejection, all 12 baseline partitions, coordinate-range rejection, and global historical event-ID uniqueness.

## Findings

None. No blocker was found for this schema verification task.
