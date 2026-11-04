# t14 — Import the partitioned 2025 baseline

## Summary

Implemented resumable monthly USGS FDSNWS downloads and an explicit consumer-owned PostgreSQL bootstrap for the 2025 M4+ baseline. The downloader made 12 successful monthly requests and cached 18,302 unique features in the persistent Compose cache volume. The importer validated/enriched the baseline and committed all 18,302 rows atomically to the existing 12 monthly PostgreSQL partitions. Re-running the importer left the unique row count unchanged.

The cache is under `$USGS_CACHE_DIR/historical/` (`/var/lib/observatorio/cache/historical/` in Compose), with files `2025_m01.geojson` through `2025_m12.geojson` and a checksum-verified `2025_manifest.json`. No downloaded catalog was added to Git.

## Deliverables

- [t14-backend-batch-report.yaml](./t14-backend-batch-report.yaml) — task traceability and structured test results.
- [checkpoints/t14-tasks-to-impl.yaml](./checkpoints/t14-tasks-to-impl.yaml) — TASK-2.2 implementation checkpoint.

## Source Files Changed

- `backend/scripts/__init__.py` — makes the command package executable as a module.
- `backend/scripts/download_historical_2025.py` — monthly/recursive fetch, retry, half-open UTC filtering, cache resume, atomic writes, checksums, and completion manifest.
- `backend/consumer/historical.py` — validates and normalizes source Features as historical records without falsely labeling them live.
- `backend/consumer/historical_import.py` — verifies all cache partitions, enriches via the existing Natural Earth STRtree, and exposes the explicit consumer bootstrap command.
- `backend/consumer/db_writer.py` — inserts the event registry and historical facts in one all-or-nothing transaction using immutable conflict handling.
- `backend/tests/test_historical_2025.py` — deterministic request, split, boundary, retry, cache-resume, UTC, and data-quality tests.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — persistent producer cache, consumer-owned bootstrap, baseline/live separation, envelope/source naming, and explicit cache readiness.
- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — verified Python 3.11/Docker environment.
- `.github/modernize/rearchitecture/artifacts/t8-devops.md` and `t8-devops-runtime.md` — `USGS_CACHE_DIR`, shared named volume, container commands, and exact Compose service set.
- `.github/modernize/rearchitecture/artifacts/t9-backend.md` — shared USGS client/runtime dependencies and producer cache environment.
- `.github/modernize/rearchitecture/artifacts/t10-dba.md` — `historical_2025`, global `historical_2025_event_keys`, deferred relation constraints, and monthly partitions.
- `.github/modernize/rearchitecture/artifacts/t11-frontend.md` — canonical Natural Earth asset path and country-field source.
- `.github/modernize/rearchitecture/artifacts/t12-backend.md` — existing validated spatial index, country dimension seeding, and consumer ownership boundary.
- `specs/001-observatorio-sismico/{spec.md,plan.md,tasks.md,data-spec.md,acceptance-tests.md}` — FR-02, half-open/monthly requests, 18,000-record subdivision, cache naming, TASK-2.2, and domain validation.
- `.specify/memory/constitution.md`, `.agents/AGENTS.md`, `.agents/subagents/02-data-ingestion/AGENT.md`, `.agents/subagents/04-backend-modeler/AGENT.md`, `.agents/rules/{architecture_invariants.md,data_quality_rules.md}`, and `.agents/skills/usgs-ingestion/SKILL.md` — service boundaries, source rules, partitioning, timestamp, and data-quality contracts.

`.github/modernize/rearchitecture/context.md`, `decisions.md`, and `team/backend/inbox.md` were absent. The canonical design was taken from t3/t8 and the project specifications. The existing backend log was read and updated.

## Evidence Mapping

- `t3-architect.md#Decisions-and-Naming` and `#Processing-and-persistence-boundaries` → `backend/scripts/download_historical_2025.py` caches the 12 monthly files in the named-volume path; `backend/consumer/historical_import.py` imports only into baseline tables, not `current_earthquakes`.
- `data-spec.md#1.2` and `usgs-ingestion/SKILL.md#Historical-Catalog` → monthly UTC queries with `minmagnitude=4.0`, `eventtype=earthquake`, `orderby=time-asc`, recursive subdivision above 18,000, event-ID deduplication, and local cache; the live request made 12 HTTP 200 responses and produced 18,302 unique features.
- `t10-dba.md#Contract-Verified` → `persist_historical_events` writes `historical_2025_event_keys` and `historical_2025` in one PostgreSQL transaction; database verification found 18,302 unique event IDs across all 12 partitions, no magnitude below 4.0, and a successful unchanged-count re-import.
- `t11-frontend.md#Summary` + `t12-backend.md#Processing-and-Naming-Decisions` → `historical_import.py` loads the approved `paises.geojson`, reuses the STRtree and seeds `dim_countries` before baseline insert; the full database-backed import completed.
- `constitution.md#2.1-2.4` and `t8-devops.md#Implementation` → execution remained inside producer/consumer Compose containers; Kafka/PostgreSQL remain unpublished; Compose config still contains exactly the five canonical services.
- `tasks.md#TASK-2.2` + `spec.md#FR-02` → implemented downloader, persistent cache, import bootstrap, and associated deterministic tests.

## Naming and Design Resolution

- Use canonical `earthquakes.live` / `earthquakes.replay` topic names only; the baseline command does not publish to either topic.
- Cache files use the required `2025_mXX.geojson` names beneath the architect-approved persistent `USGS_CACHE_DIR/historical` directory rather than checking data into the repository.
- Treat the baseline as immutable and separate from live events. The importer performs historical-specific validation rather than wrapping baseline records in a `mode=live` envelope.
- One PostgreSQL transaction writes both the ID registry and fact rows, so a failed import cannot expose a partial baseline. Re-imports use `ON CONFLICT DO NOTHING`.

## Test Results

- Command: `docker compose --env-file .env.example run --build --rm --no-deps productor python -m unittest discover -s tests -p test_historical_2025.py -v`
  - Passed: 6; Failed: 0; Skipped: 0.
- Command: `docker compose --env-file .env.example run --build --rm -e RUN_DB_INTEGRATION=1 consumidor python -m unittest discover -s tests -q`
  - Passed: 37; Failed: 0; Skipped: 0.
- Command: `docker compose --env-file .env.example run --build --rm --no-deps productor python -m scripts.download_historical_2025`
  - Passed: 12 monthly USGS requests (HTTP 200); 18,302 unique features cached; no month required subdivision; no credentials used.
- Command: `docker compose --env-file .env.example run --rm --no-deps productor python -m scripts.download_historical_2025`
  - Passed: cache volume verification returned `cache_hit=True`; no refetch was needed.
- Command: `docker compose --env-file .env.example run --build --rm consumidor python -m consumer.historical_import` — run twice.
  - Passed: both imports completed; each reported 18,302 cached features and 18,302 unique events.
- Command: `docker compose --env-file .env.example exec -T almacenamiento psql -U observatorio -d observatorio -v ON_ERROR_STOP=1 -Atc "SELECT count(*), count(DISTINCT event_id), count(*) FILTER (WHERE mag < 4.0), count(DISTINCT tableoid::regclass) FROM historical_2025;"`
  - Passed: `18302|18302|0|12`; companion checks confirmed 18,302 registry rows, all 12 monthly partitions, and occurrence dates within 2025.
- Command: `git diff --check` and `docker compose --env-file .env.example config --quiet` plus exact service-set assertion.
  - Passed: no whitespace errors; exactly `productor`, `broker`, `consumidor`, `almacenamiento`, and `api`.

Validation containers were stopped with `docker compose down` without `-v`; the downloaded cache and imported PostgreSQL baseline remain in their named volumes.

## Findings and Handoff

- No blocker for TASK-2.2.
- The database import is atomic and repeatable; the `historical_2025` relation remains read-only to the API's comparison path.
- Full-stack endpoint checks, replay, frontend behavior, and the complete 11-case acceptance suite are not part of this task and remain downstream validation work.
- No credentials, Netlify, ngrok, publication, or unverifiable academic evidence were used or claimed.
