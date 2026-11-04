## [t4] PostgreSQL schema, time partitions, and idempotent persistence
- Kept the live/current table unpartitioned because its required `event_id`-only conflict target must be globally unique; PostgreSQL partition uniqueness must include the partition key.
- Added monthly partitions for the fixed 2025 baseline and a global event-key registry with deferred foreign keys so month partitioning does not weaken event identity.
- Used yearly version partitions plus a default partition; replay stays in separate run-scoped tables so live aggregates cannot accidentally include replay.
- Added Kafka topic/partition/offset unique keys to quarantine writes for safe redelivery after DB success and before broker offset commit.
- Docker daemon was unavailable, so validation used the PostgreSQL grammar parser and schema-contract assertions; do not treat that as a live database migration test.
- Learnings consumed: (none)

## [t4] Revalidated PostgreSQL schema during implementation resume
- Confirmed `context.md` and `decisions.md` are absent in this workspace; used the approved architect artifact and the existing task artifact for decisions/contracts.
- Re-ran pglast against `backend/db/init.sql`: 49 SQL statements parsed; all 8 structural checks passed (required relations, 12 baseline partitions, version partitions, magnitude threshold, strict-newer UPSERT, quarantine offset uniqueness, replay isolation, transaction wrapper).
- A first assertion incorrectly assumed the SQL file began with `BEGIN;` before its leading comments; corrected the test to check for the transaction statement anywhere in the script. No schema defect was found.
- Docker daemon is unavailable and `psql` is not installed, so a PostgreSQL execution/re-run test remains blocked.
- Learnings consumed: [dba/postgres-partitioned-idempotency]

## [t10] Verified PostgreSQL schema contract at runtime
- Applied `backend/db/init.sql` twice to a disposable PostgreSQL 16.4 container; both applications succeeded, including the deferred historical identity foreign keys and default/yearly partitions.
- Exercised 8 database contracts: nullable magnitude and negative depth, strict-newer UPSERT, 2025 monthly routing, run-scoped replay isolation, quarantine offset uniqueness, partition count, coordinate rejection, and global historical ID uniqueness.
- No schema changes were required. Application persistence call sites were not available yet, so downstream code must still be checked against the exact DDL column names.
- Learnings consumed: [dba/postgres-partitioned-idempotency]
