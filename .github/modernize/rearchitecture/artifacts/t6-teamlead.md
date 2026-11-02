# t6 — Local MVP Implementation Blueprint

## Summary

The implementation plan and focused validation strategy are ready for execution. The blueprint covers the bounded local MVP only: five Compose services, live and 2025 USGS ingestion, monthly historical baseline partitions, Natural Earth enrichment, quality/quarantine, transactional idempotency, FastAPI analytics, a minimal Angular dashboard, isolated replay, and local acceptance tests. It explicitly excludes Netlify/ngrok publication and academic deliverables.

## Deliverables

- [t6-teamlead-plan.md](./t6-teamlead-plan.md) — sequenced implementation plan, executable tasks, requirements mapping, canonical decisions, and plan constraints.
- [t6-teamlead-validation.md](./t6-teamlead-validation.md) — focused validation stack, journey-to-test matrix, environment evidence, fallback boundaries, and conformance expectations.
- [checkpoints/t6-spec-to-plan.yaml](./checkpoints/t6-spec-to-plan.yaml) — FR/NFR-to-plan traceability.
- [checkpoints/t6-plan-to-tasks.yaml](./checkpoints/t6-plan-to-tasks.yaml) — plan-item-to-task traceability.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t2-pm.md` — local MVP scope, feature evidence, exclusions, and naming decisions.
- `.github/modernize/rearchitecture/artifacts/t3-architect.md` — five-service design, event/API contracts, replay isolation, and Natural Earth source decision.
- `.github/modernize/rearchitecture/artifacts/t4-dba.md` — existing PostgreSQL DDL, monthly `historical_2025` partitions, replay relations, and write/offset protocol.
- `.github/modernize/rearchitecture/artifacts/t5-ux.md` — Angular dashboard behavior, `ND`, stale-data handling, replay UI, and local outage test scope.
- `.github/modernize/rearchitecture/artifacts/t1-teamlead.md` — user-approved Angular, Natural Earth attribution/license, canonical naming, local-only, and no-publication decisions (via t2/t3).
- `.github/modernize/rearchitecture/artifacts/t3.1-teamlead.md` — healthchecks on all services and only real `service_healthy` dependency edges.
- `specs/001-observatorio-sismico/{spec.md,plan.md,tasks.md,data-spec.md,acceptance-tests.md}` — requirement and behavior source of truth.
- `.specify/memory/constitution.md` — immutable architecture, privacy, replay, quality, and reproducibility constraints.
- `.agents/AGENTS.md`, `.agents/rules/{architecture_invariants.md,data_quality_rules.md}`, `.agents/subagents/*/AGENT.md`, and relevant `.agents/skills/*/SKILL.md` — execution boundaries and project validation rules.
- `.github/modernize/rearchitecture/learnings/teamlead/{canonical-compose-replay-names.md,compose-health-dependencies.md}` — canonical naming and non-artificial health dependency policy.

## Evidence Mapping

- `t2-pm.md#Scope Baseline` and `#Behavior Traceability` → local MVP boundary, requirement coverage, and explicit non-deliverables in `t6-teamlead-plan.md`.
- `t3-architect.md#Decisions and Naming`, `#Processing and persistence boundaries`, and `#API Endpoints Inventory` → plan items 1.1–5.2 and tasks T001–T011.
- `t4-dba.md#Schema and Naming Decisions` and `#Persistence Contract` → plan item 1.2, tasks T002/T005/T006/T010, and tests for monthly partitions, newer-only writes, and DB-before-offset.
- `t5-ux.md#Product Decisions`, `#Connection, Loading, and Empty States`, and `#Acceptance Mapping for Frontend Verification` → plan items 4.1–4.2 and 5.2 plus browser acceptance in `t6-teamlead-validation.md`.
- `spec.md#FR-01–FR-09` and `#NFR-01–NFR-04` → complete mappings in `checkpoints/t6-spec-to-plan.yaml` and the Requirement Mapping table.
- `acceptance-tests.md#TC-01–TC-11` plus `t2-pm.md#Gaps and Handoff Notes` item 3 → focused acceptance coverage; TC-09/10 use local API outage/recovery, not ngrok.

## Verification

- Plan-to-requirement and plan-to-task coverage: 100% in both checkpoints; no orphan plan items or tasks.
- Existing project baseline: specification-only workspace plus `backend/db/init.sql`; no `package.json`, backend requirements manifest, test suite, or canonical test command exists yet.
- Environment probe: `docker info` failed because `npipe:////./pipe/docker_engine` does not exist; Node.js is `v22.15.0`; Python is `3.15.0`. Runtime/container validation is therefore not claimed. See the validation detail for exact evidence and downstream action.
- No production source, Compose configuration, runtime tests, external services, credentials, or public deployment were changed or used by t6.

## Handoff

The next phase should execute T001–T014 with the named technical owners. The Docker daemon must be made available before any five-service or PostgreSQL/Kafka integration result can be claimed. Do not treat this planning deliverable as implementation completion.
