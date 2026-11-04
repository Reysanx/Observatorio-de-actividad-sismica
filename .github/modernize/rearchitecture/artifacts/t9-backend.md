# t9 — USGS Live Producer

## Summary

Implemented the Compose-only live producer for the canonical `earthquakes.live` topic. It fetches the USGS 24-hour GeoJSON feed using async `httpx`, retries transient transport/429/5xx errors with bounded exponential backoff, filters non-earthquake features, deduplicates unchanged/older event versions in memory, and publishes versioned event envelopes plus a poll-audit control record with broker acknowledgements.

The producer does not connect to PostgreSQL. It preserves null magnitude, keeps non-finite numeric values JSON-safe for downstream quarantine, emits UTC timestamps and content hashes, and leaves uncertain delivery at-least-once for the consumer's idempotent persistence.

## Files Changed

- `backend/producer/__init__.py` — producer package marker.
- `backend/producer/usgs_client.py` — asynchronous HTTP client, response validation, hashing, and bounded retry policy.
- `backend/producer/main.py` — polling loop, strict-newer deduplication, event/audit envelopes, Kafka publication and environment configuration.
- `backend/requirements.txt` — exact pins for the producer runtime (`aiokafka`, `httpx`).
- `backend/tests/test_usgs_live_producer.py` — focused isolated tests using HTTPX mock transport and a fake Kafka producer.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — followed canonical topic, service names, event-envelope fields, poll-audit control record, at-least-once delivery, and producer/database boundary.
- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — used the prepared Python 3.11 and Docker Compose environment.
- `.github/modernize/rearchitecture/artifacts/t8-devops.md` — matched the producer Docker entrypoint, broker DNS, service configuration, and `USGS_POLL_INTERVAL_SECONDS`.
- `specs/001-observatorio-sismico/spec.md#FR-01/FR-06`, `data-spec.md#1.1`, and `tasks.md#TASK-3.1` — followed the 60-second live feed, earthquake-only filter, USGS fields, and event-ID key.
- `.specify/memory/constitution.md#2.1-2.4`, `.agents/subagents/02-data-ingestion/AGENT.md`, `.agents/skills/usgs-ingestion/SKILL.md`, and `.agents/rules/data_quality_rules.md` — honored service containment, async ingestion, null/negative-value semantics, and quarantine handoff.
- `.github/modernize/rearchitecture/board.md` — read-only task/dependency sequencing.

`context.md`, `decisions.md`, and `team/backend/{log.md,inbox.md}` were absent in this workspace at task start. No `*-fanout.md` topology artifact was present; the assigned producer task has no group-splitting requirement.

## Evidence Mapping

- `t3-architect.md#Decisions and Naming` + `#Kafka topics and delivery` → producer sends all records to `earthquakes.live`; event keys are UTF-8 `event_id`, audit keys are UTF-8 `poll_id`, and `send_and_wait` confirms broker delivery.
- `t3-architect.md#Versioned JSON envelope` → event records include `schema_version`, `record_type`, `source=usgs_live`, UTC `ingested_at`, `mode=live`, `event_id`, integer `updated_ms`, `content_hash`, `run_id=null`, and original Feature payload.
- `t3-architect.md#Live poll-control record` + `data-spec.md#1.1` → each successful or failed source poll emits an audit record with request/completion UTC times, HTTP status, content hash, counts, excluded reasons, and safe error code; non-earthquake features are excluded rather than sent as earthquake events.
- `tasks.md#TASK-3.1` + `constitution.md#2.3` → in-memory state suppresses duplicate/older `updated_ms` values and is marked only after a broker acknowledgement, allowing retry after uncertain publication.
- `data-spec.md#1.1` + `data_quality_rules.md#1` → absent `mag` remains JSON `null`; `NaN`/infinity tokens and numeric overflow are kept as JSON strings so downstream quality checks can quarantine them without emitting invalid Kafka JSON.
- `t8-devops.md#Implementation` → `backend/Dockerfile.producer` invokes `python -m producer.main`; Compose supplies `broker:9092`, the USGS URL, and the 60-second interval.

## Naming Resolution

Followed the architect/Compose canonical names `productor` and `earthquakes.live`, and `source=usgs_live`. Older requirements referring to `kafka`, `earthquakes-replay`, or an unversioned envelope do not change this live-producer contract. Replay, historical downloads, consumer processing, API, and frontend remain assigned to downstream tasks.

## Test Results

- Command: `docker compose --env-file .env.example run --build --rm --no-deps productor python -m unittest discover -s tests -p test_usgs_live_producer.py -v`
  - Passed: 9; Failed: 0; Skipped: 0.
  - Covers response hashing/validation, 429/5xx backoff, permanent HTTP errors, malformed JSON status, safe NaN forwarding, type filtering, Kafka keys/envelopes, unchanged-event deduplication, newer revisions, failed-poll audit, and retry after missing broker acknowledgement.
- Command: `docker compose --env-file .env.example config --quiet`
  - Passed: 1; Failed: 0; Skipped: 0.
- No live USGS request or Kafka service integration was run; producer behavior was validated with deterministic mocks. The full five-service build/start and whole-system acceptance suite remain downstream integration work.

## Handoff / Remaining Integration

- `backend/requirements.txt` currently pins the live producer's runtime only. Consumer/API implementation tasks must add their dependencies to this shared manifest before building the full Compose stack.
- Historical USGS ingestion, country enrichment, consumer persistence, and full-stack runtime/acceptance validation are not claims of this task.
- No secrets were added, and no Netlify/ngrok publication was attempted.
