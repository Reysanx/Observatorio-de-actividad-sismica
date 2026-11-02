# t8 — Five-service local runtime

## Summary

Scaffolded the canonical five-service Compose topology, private Kafka/PostgreSQL networking, loopback-only API binding, named persistent volumes, pinned backend/base images, container health checks, and idempotent Kafka topic setup. The broker was started and its topic layout verified in an isolated Compose project. The complete application build remains pending because implementation modules, requirements, and the Natural Earth data file are owned by downstream tasks and are not present yet.

## Deliverables

- [t8-devops-runtime.md](./t8-devops-runtime.md) — files, architecture choices, test evidence, and remaining integration prerequisite.
- [t8-devops-batch-report.yaml](./t8-devops-batch-report.yaml) — structured task and test report.
- [checkpoints/tasks-to-impl.yaml](./checkpoints/tasks-to-impl.yaml) — implementation traceability checkpoint.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — verified Docker/Compose readiness and Python 3.11 environment; informed the reproducible local run assumptions.
- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — canonical service/topic names, health dependency edges, volume boundaries, KRaft settings, and API loopback/private-broker policy.
- `.github/modernize/rearchitecture/board.md` — read-only task order; confirmed application implementations follow the scaffold.
- `specs/001-observatorio-sismico/{spec.md,plan.md,tasks.md,data-spec.md,acceptance-tests.md}` and `.specify/memory/constitution.md` — runtime/service and privacy invariants.
- `.agents/AGENTS.md`, `.agents/subagents/01-platform-devops/AGENT.md`, `.agents/rules/architecture_invariants.md`, `.agents/rules/data_quality_rules.md`, `.agents/skills/acceptance-testing/SKILL.md` — role boundaries, service topology, security, and acceptance expectations.
- `runtime-validation` and `implementing-code` skills — validation and implementation reporting procedure.

## Evidence Mapping

- `t3-architect.md#Service Catalog` + `#Startup dependencies` → `compose.yaml` service IDs, five-service count, and only genuine `service_healthy` dependency edges; verified by `docker compose config --format json`.
- `t3-architect.md#Kafka topics and delivery` → `backend/scripts/start_kafka.sh` creates `earthquakes.live` (3 partitions) and `earthquakes.replay` (1 partition), each with 48-hour retention; verified against a healthy Kafka container.
- `t3-architect.md#Security posture` + `.agents/rules/architecture_invariants.md#2` → only API publishes `127.0.0.1:8000`; broker and PostgreSQL have no host port mapping; verified from rendered Compose JSON.
- `t7-devops.md#Target Environment Preparation` → Compose validation and broker smoke tests use the verified Docker daemon and Compose CLI.
- `tasks.md#TASK-1.2` → Compose and three backend Dockerfiles are scaffolded; full image build/start is deferred until the implementation-owned modules and data files exist.

## Naming Resolution

Use the t3 canonical runtime names `productor`, `broker`, `consumidor`, `almacenamiento`, and `api`; use `earthquakes.live` and `earthquakes.replay`. Older spec examples mentioning `kafka`, `postgres`, or `earthquakes-replay` are not used in Compose. No `decisions.md` exists in the workflow directory; this follows the already approved t3 architecture and does not create a competing decision record.

## Test Results

- Command: `docker compose --env-file .env.example config --quiet`
  - Passed: 1; Failed: 0; Skipped: 0.
- Command: `docker compose --env-file .env.example config --format json` plus structural assertions
  - Passed: 1; Failed: 0; Skipped: 0.
  - Confirmed exactly five services, health checks and `unless-stopped` restart policies on all five, expected healthy dependency edges, API loopback binding, and no Kafka/PostgreSQL published ports.
- Command: `docker compose -p t8-scaffold-check --env-file .env.example up -d broker`, then `docker compose -p t8-scaffold-check exec -T broker /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker:9092 --describe --topic <topic>`
  - Passed: 1; Failed: 0; Skipped: 0.
  - Broker became `healthy`; live topic reported 3 partitions and replay topic 1 partition; both reported `retention.ms=172800000`. The isolated validation project and its volume were removed afterward.
- Full stack command `docker compose --env-file .env.example up --build -d`: not run yet. Build prerequisites are absent at this phase: `backend/requirements.txt`, `backend/producer/main.py`, `backend/consumer/main.py`, `backend/api/main.py`, and `frontend/public/datos/paises.geojson`. These are downstream implementation deliverables; the Compose bind mount explicitly refuses to invent a missing country file.
- Attempted to parse the auxiliary report/checkpoint YAML with Python; PyYAML is not installed (`ModuleNotFoundError`). This optional artifact-parser check was skipped; the Compose YAML itself was validated by Docker Compose.
- Initial broker smoke attempt exposed CRLF in the mounted shell script on Windows. The script was normalized to LF, `.gitattributes` now enforces LF, and the repeated broker smoke test passed.

## Findings and Handoff

- Full five-service application startup is not yet demonstrated; run the full build and acceptance checks after the dependent implementation tasks land.
- Docker images use Python `3.11.9-slim-bookworm`, Apache Kafka `3.7.0`, and PostgreSQL `16.4-alpine`; the later dependency/image security task should review and update pins as appropriate.
- The Compose network is a normal bridge, not marked `internal`, so the producer can make the required outbound USGS HTTPS requests. Only the API has a host port binding, and that binding is loopback-only.
