\pset pager off
\echo 'PostgreSQL plans for the E-05 index evidence'
\echo 'PLAN 1 - current time window and newest page'
EXPLAIN (ANALYZE, BUFFERS, COSTS, TIMING OFF, SUMMARY ON)
SELECT event_id, time_utc, mag
FROM current_earthquakes
WHERE time_utc >= TIMESTAMPTZ '2026-11-05 00:00:00+00'
  AND time_utc < TIMESTAMPTZ '2026-11-12 00:00:00+00'
ORDER BY time_utc DESC
LIMIT 50;

\echo 'PLAN 2 - current magnitude threshold'
EXPLAIN (ANALYZE, BUFFERS, COSTS, TIMING OFF, SUMMARY ON)
SELECT event_id, time_utc, mag
FROM current_earthquakes
WHERE mag >= 5.0;

\echo 'PLAN 3 - historical narrow time and magnitude range'
EXPLAIN (ANALYZE, BUFFERS, COSTS, TIMING OFF, SUMMARY ON)
SELECT event_id, time_utc, mag
FROM historical_2025
WHERE time_utc >= TIMESTAMPTZ '2025-07-14 00:00:00+00'
  AND time_utc < TIMESTAMPTZ '2025-07-15 00:00:00+00'
  AND mag >= 5.0
ORDER BY time_utc DESC;

\echo 'PLAN 4 - historical country and month'
EXPLAIN (ANALYZE, BUFFERS, COSTS, TIMING OFF, SUMMARY ON)
SELECT event_id, time_utc, mag
FROM historical_2025
WHERE adm0_a3 = 'CHL'
  AND time_utc >= TIMESTAMPTZ '2025-07-01 00:00:00+00'
  AND time_utc < TIMESTAMPTZ '2025-08-01 00:00:00+00'
ORDER BY time_utc DESC;

\echo 'PLAN 5 - audit by completion time'
EXPLAIN (ANALYZE, BUFFERS, COSTS, TIMING OFF, SUMMARY ON)
SELECT poll_id, completed_at, status
FROM ingestion_audit
WHERE completed_at >= TIMESTAMPTZ '2026-11-11 00:00:00+00'
ORDER BY completed_at DESC
LIMIT 20;

\echo 'PLAN 6 - replay run, country, and event-time range'
EXPLAIN (ANALYZE, BUFFERS, COSTS, TIMING OFF, SUMMARY ON)
SELECT run_id, event_id, time_utc
FROM replay_earthquakes
WHERE run_id = 'replay-7e2bc4e98fe249d88e972e8341a90c7e'
  AND adm0_a3 = 'CHL'
  AND time_utc >= TIMESTAMPTZ '2025-06-01 00:00:00+00'
  AND time_utc < TIMESTAMPTZ '2025-07-01 00:00:00+00'
ORDER BY time_utc;

\echo 'PLAN 7 - country-only live filter at current development scale'
EXPLAIN (ANALYZE, BUFFERS, COSTS, TIMING OFF, SUMMARY ON)
SELECT count(*)
FROM current_earthquakes
WHERE adm0_a3 = 'N/A';
