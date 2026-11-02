# t8 — Runtime scaffold details

## Implementation

- `compose.yaml` defines exactly the canonical five services: `productor`, `broker`, `consumidor`, `almacenamiento`, and `api`.
- Compose uses a bridge network for service DNS and producer outbound USGS access. Kafka and PostgreSQL publish no host ports. FastAPI is bound only to `127.0.0.1:${API_PORT}:8000`.
- All containers use `unless-stopped` and health checks. Startup gates follow t3: producer waits for broker; consumer waits for broker and PostgreSQL; API waits for PostgreSQL. Broker and PostgreSQL remain dependency roots.
- PostgreSQL mounts the existing `backend/db/init.sql` for first-volume initialization. Named volumes persist Kafka data, PostgreSQL data, and USGS cache; consumer mounts the cache and Natural Earth source read-only.
- Broker startup creates the t3 topics idempotently: live has 3 partitions, replay has 1, each with 48-hour retention.
- Producer, consumer, and API Dockerfiles use Python 3.11.9 slim Bookworm, install the shared `backend/requirements.txt` expected from backend implementation, and run as UID/GID 10001. Their entrypoints match the planned `producer.main`, `consumer.main`, and `api.main:app` modules.
- `.env.example` contains local-only placeholders; `.gitignore` excludes `.env`. `backend/.dockerignore` excludes local state and caches.
- `docs/deployment.md` describes local setup, health/log inspection, safe shutdown, and destructive volume reset.
- `.gitattributes` pins shell scripts to LF because Windows checkout defaults otherwise produced an invalid CRLF-mounted Bash entrypoint.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — host toolchain/readiness evidence.
- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — service, topic, health, network, volume, and endpoint contracts.
- `specs/001-observatorio-sismico/plan.md#4.1` and `tasks.md#TASK-1.2` — Compose health and five-service scaffold criteria.
- `.specify/memory/constitution.md#2.1-2.2` and `.agents/rules/architecture_invariants.md#1-2` — exact service set and private networking constraints.

## Evidence Mapping

- `t3-architect.md#Service Catalog` → `compose.yaml#services`; parsed model contains exactly the five canonical service keys.
- `t3-architect.md#Startup dependencies` → `compose.yaml#depends_on`; structural assertion confirms the four genuine dependency edges.
- `t3-architect.md#Kafka topics and delivery` → `backend/scripts/start_kafka.sh`; healthy broker topic descriptions confirm partition counts and retention.
- `t3-architect.md#Security posture` → `compose.yaml#api.ports` and absence of broker/database `ports`; rendered model confirms loopback-only API publication.
- `t7-devops.md#Target Environment Preparation` → verified Docker daemon was used for the broker smoke test.

## Test Results

- `docker compose --env-file .env.example config --quiet` — passed, exit 0.
- Rendered Compose JSON topology/security/health assertions — passed, exit 0.
- Isolated Kafka broker startup and healthcheck — passed, exit 0.
- `earthquakes.live` topic: 3 partitions, replication factor 1, retention 172,800,000 ms — verified.
- `earthquakes.replay` topic: 1 partition, replication factor 1, retention 172,800,000 ms — verified.
- Final focused validation counts: passed 3, failed 0, skipped 2.
- Optional parser check for the auxiliary YAML reports was unavailable because PyYAML is not installed (`ModuleNotFoundError`); Compose YAML parsing passed through Docker Compose.
- Full application startup/build is not run because required implementation files are absent until downstream tasks. No application endpoint behavior is claimed.

## Issues / Next Step

The downstream backend/frontend implementation must add the requirements manifest and referenced entrypoint modules, and the frontend task must add `frontend/public/datos/paises.geojson`. Then run `docker compose up --build -d`, verify all five health states, and execute the backend/browser acceptance suites. No credentials, ngrok, or Netlify were used.
