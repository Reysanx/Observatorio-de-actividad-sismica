# t4 — PostgreSQL Schema, Partitions, and Idempotent Persistence

## Summary

Added `backend/db/init.sql` for PostgreSQL 16 with the canonical live, historical, audit, quarantine, country, and replay relations. The schema preserves live/replay isolation, UTC instants, nullable magnitudes, negative magnitudes/depths, global event identity, and transaction-safe deduplication.

## Deliverable

- `backend/db/init.sql` — repeatable initial DDL, indexes, constraints, pre-created time partitions, replay-isolated tables, and canonical persistence protocol comments.

## Schema and Naming Decisions

- Kept the canonical snake_case relations: `current_earthquakes`, `earthquake_versions`, `historical_2025`, `dim_countries`, `quarantine_events`, and `ingestion_audit`.
- Added `replay_runs`, `replay_earthquakes`, `replay_versions`, and `replay_quarantine_events`; replay data never shares the live or historical fact tables. `run_id` scopes every replay event and revision.
- Kept `current_earthquakes` unpartitioned so `event_id` remains a globally unique `ON CONFLICT` key. A partitioned PostgreSQL table cannot enforce uniqueness on a key that omits its partition key.
- Partitioned the immutable historical baseline monthly by `time_utc` for all 12 months of 2025 and enforced the source contract (`mag` is present and `>= 4.0`). `historical_2025_event_keys` is an unpartitioned identity registry with deferred foreign keys to the partitioned fact table; this preserves global `event_id` uniqueness despite the partitioned table's required `(event_id, time_utc)` primary key.
- Partitioned `earthquake_versions` yearly for 2024–2030, with a default partition to avoid rejecting later revisions before partition maintenance. Added a parent index for event/revision lookups.
- Left replay tables unpartitioned so their `(run_id, event_id)` keys remain suitable for strict-newer UPSERTs. Replay revisions use `(run_id, event_id, updated_utc)`.
- Made quarantine inserts idempotent by `(source_topic, source_partition, source_offset)`, including support for storing corrupt, non-JSON Kafka bytes.
- The database relation `current_earthquakes.source` accepts only `usgs_live`; baseline and replay sources are `usgs_2025` and `usgs_replay` in their corresponding relations. Kafka topics follow the architect's canonical dotted names.
- `dim_countries` seeds the required `N/A` member. Country loaders should insert the remaining Natural Earth rows with source attributes preserved; `display_name` is the consumer/API display contract, not an assertion that Natural Earth supplies Spanish names.
- Checks reject non-finite magnitude/depth and out-of-range coordinates, but intentionally allow SQL `NULL` magnitude and negative magnitude/depth. Event times are `TIMESTAMPTZ`; clients remain responsible for UTC serialization.

## Persistence Contract

The canonical live transaction is documented at the end of `backend/db/init.sql`:

1. UPSERT `current_earthquakes` on `event_id`, updating only when the incoming `updated_utc` is strictly greater.
2. Append the accepted current snapshot to `earthquake_versions` only when the UPSERT returns a row, with `ON CONFLICT (event_id, updated_utc) DO NOTHING`.
3. Commit PostgreSQL before committing the Kafka offset.

For the historical bootstrap, insert the `(event_id, time_utc)` identity and baseline row in one transaction. Replays first create their `replay_runs` record and only write to replay tables. Quarantine is mode-specific and offset-keyed.

## Compatibility and Migration Notes

- This is an idempotent **initialization script**: it can be re-run against a database created from this exact schema. `CREATE TABLE/INDEX IF NOT EXISTS`, conflict-safe sentinel seeding, and guarded deferred-constraint creation prevent duplicate-object failures.
- It is not a general schema-upgrade mechanism: PostgreSQL's `IF NOT EXISTS` does not reconcile a pre-existing, differently shaped table. Future changes to a populated volume require explicit forward migrations and an assessed lock/rollback plan.
- There is no destructive DDL and no PostGIS dependency. Spatial lookup remains consumer-owned.
- `earthquake_versions_default` is a safety net. Before adding future yearly partitions, operators should inspect and, if necessary, move matching rows out of the default partition so PostgreSQL can validate the new partition bound.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — canonical relation names, source/mode routing, live/replay isolation, strict-newer semantics, and DB-before-offset ordering.
- `.github/modernize/rearchitecture/artifacts/t2-pm.md` — local MVP scope and explicit canonical naming resolutions.
- `.github/modernize/rearchitecture/artifacts/t1-teamlead.md` — user-approved naming and replay-isolation decisions.
- `specs/001-observatorio-sismico/data-spec.md` — USGS field meanings, monthly 2025 source slices, country attributes, quality rules, and quarantine minimums.
- `specs/001-observatorio-sismico/spec.md` — FR-04/05/06 versioning, data validity, and idempotency requirements.
- `specs/001-observatorio-sismico/plan.md` — initial table/index inventory and PostgreSQL 16 direction.
- `specs/001-observatorio-sismico/tasks.md` — `TASK-1.3` schema deliverable and required relation names.
- `specs/001-observatorio-sismico/acceptance-tests.md` — TC-01–TC-08 and TC-11 database behavior.
- `.specify/memory/constitution.md` — UTC/null/negative-value, idempotency, privacy, and replay invariants.
- `.agents/AGENTS.md`, `.agents/rules/architecture_invariants.md`, `.agents/rules/data_quality_rules.md`, `.agents/skills/kafka-idempotent-consumer/SKILL.md`, and `.agents/subagents/04-backend-modeler/AGENT.md` — project constraints, persistence ordering, and expected database ownership.
- `.github/modernize/rearchitecture/board.md` and `.github/modernize/rearchitecture/team/dba/inbox.md` — current task sequencing and DBA handoff note.

## Evidence Mapping

- `t3-architect.md#Decisions and Naming` → canonical names/topics and separate replay relations in `backend/db/init.sql`.
- `t3-architect.md#Processing and persistence boundaries` → live strict-newer UPSERT, version append, replay-only writes, and transaction/offset protocol comments.
- `data-spec.md#1.2` + `tasks.md#TASK-1.3` → 12 2025 monthly database partitions, baseline relation, and indexes.
- `data-spec.md#4` + `spec.md#FR-05` + `acceptance-tests.md#TC-06` → mode-specific quarantine with explicit reason, raw JSON or raw bytes, and source Kafka position.
- `spec.md#FR-04/FR-06` + `kafka-idempotent-consumer/SKILL.md#2-3` + `acceptance-tests.md#TC-01–TC-04/TC-08` → globally unique event keys, strict timestamp updates, revision uniqueness, offset-keyed quarantine, and DB-before-offset sequence.
- `spec.md#FR-05` + `data_quality_rules.md#1-3` + `acceptance-tests.md#TC-05/TC-07` → nullable magnitude, negative measurements, coordinate checks, and country sentinel FK.
- `t3-architect.md#Decisions and Naming` + `spec.md#FR-09` + `acceptance-tests.md#TC-11` → isolated run-scoped replay tables and replay run state.

## Test Results

- Command: `python -c "from pathlib import Path; from pglast import parse_sql; s=Path('backend/db/init.sql').read_text(encoding='utf-8'); statements=parse_sql(s); relations=('dim_countries','current_earthquakes','historical_2025_event_keys','historical_2025','earthquake_versions','quarantine_events','ingestion_audit','replay_runs','replay_earthquakes','replay_versions','replay_quarantine_events'); missing=[name for name in relations if f'CREATE TABLE IF NOT EXISTS {name}' not in s]; months=[f'CREATE TABLE IF NOT EXISTS historical_2025_{month:02d} PARTITION' in s for month in range(1,13)]; years=[f'CREATE TABLE IF NOT EXISTS earthquake_versions_{year} PARTITION' in s for year in range(2024,2031)]; baseline=s.split('CREATE TABLE IF NOT EXISTS historical_2025 (',1)[1].split(') PARTITION BY RANGE',1)[0]; assert not missing, missing; assert all(months) and all(years); assert 'mag            DOUBLE PRECISION NOT NULL' in baseline; assert 'CONSTRAINT ck_historical_2025_mag_threshold CHECK (mag >= 4.0)' in baseline; assert 'WHERE EXCLUDED.updated_utc > current_earthquakes.updated_utc' in s; assert 'UNIQUE (source_topic, source_partition, source_offset)' in s; assert s.rstrip().endswith('COMMIT;'); print(f'PASS: {len(statements)} SQL statements parsed; {len(relations)} required relations; {sum(months)} history partitions; {sum(years)} version partitions; baseline >=4, live strict-newer, Kafka-offset uniqueness, transaction terminator present')"`
- Command: `python -c "from pathlib import Path; files=(Path('backend/db/init.sql'),Path('.github/modernize/rearchitecture/artifacts/t4-dba.md'),Path('.github/modernize/rearchitecture/team/dba/log.md'),Path('.github/modernize/rearchitecture/learnings/dba/postgres-partitioned-idempotency.md')); bad={str(p):[n for n,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1) if line.rstrip()!=line] for p in files}; bad={name:lines for name,lines in bad.items() if lines}; assert not bad,bad; print(f'PASS: no trailing whitespace in {len(files)} task files')"`
- Passed: 2 checks (PostgreSQL grammar/schema contract; whitespace in all 4 task files).
- Failed: 0.
- Skipped: 1 PostgreSQL server execution/re-run test; Docker daemon is unavailable in this environment and `psql` is not installed.
- The validator used local `pglast` 8.7, installed outside the repository; it is not an application dependency.
- Database runtime limitation evidence: `docker info --format '{{.ServerVersion}}'` failed because `//./pipe/docker_engine` is absent.
- Academic deliverables and end-to-end application behavior are not claimed by this DBA schema task.

## Blockers / Downstream Notes

- Before integration, the consumer/backend must use the exact column names in `init.sql`, seed all real countries before event inserts, and keep each event/version or quarantine write in one PostgreSQL transaction.
- The historical importer must insert the identity registry and baseline row in the same transaction. An event ID reused with a different occurrence timestamp is rejected by the deferred FK rather than silently duplicated.
- PostgreSQL execution and repeat-run behavior still need verification once Docker/PostgreSQL is available.
