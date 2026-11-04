# USGS Live Envelope and Deduplication

Use the architect's versioned Kafka envelope and only advance in-memory producer deduplication after broker acknowledgement.

## What Happened

For Observatorio de actividad sísmica task t9, the live producer routes event envelopes and poll-control records through `earthquakes.live`. Event keys are the UTF-8 USGS event ID; poll audit keys are separate UUID poll IDs. Poll audits hash the raw HTTP response, while event hashes use canonical feature JSON. A failed Kafka acknowledgement must not mark the feature seen, preserving at-least-once retry behavior.

USGS feeds are complete snapshots, so duplicate unchanged `updated_ms` values are expected. Suppress equal/older revisions in memory, but publish strictly newer revisions. Preserve nullable values and serialize non-finite numbers such as `NaN`, `Infinity`, or overflowing numeric exponents as strings for downstream quarantine.

## Takeaway

Keep HTTP retry/error classification separate from the Kafka polling loop. Use the `earthquakes.live` topic and versioned event schema from the architect artifact, emit a `poll_audit` record on source success/failure, avoid database writes in the producer, and only update dedupe state after `send_and_wait` acknowledges.

## History
- 2026-11-02 (Observatorio-de-actividad-s-smica/t9): initial
