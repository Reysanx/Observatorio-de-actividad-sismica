## [t3] Designed five-service architecture and service contracts
- Codebase/domain discoveries: requirements describe a target system; no existing implementation was inspected or modified. `t2` canonicalizes the five Compose IDs and two main topics but left replay persistence unresolved.
- Wrong assumptions and corrections: initially the replay topic appeared sufficient; it does not prevent replay rows from contaminating live APIs. Specify separate replay relations and run-scoped queries.
- Debugging dead-ends and what actually worked: context.md, decisions.md, and architect inbox/log did not exist at task start; use available board, t1, and t2 artifacts. The all-services `depends_on` invariant is not satisfiable without an artificial edge/cycle among independent root services; report it to teamlead.
- Techniques/patterns worth reusing: document Kafka timestamp units explicitly (`updated_ms` vs UTC API timestamps), make replay controls ordered on a single partition, and preserve a strict live-only default at the API boundary.
- Learnings consumed: []

## [t3] Updated architecture after health-policy resolution
- Codebase/domain discoveries: `context.md` and `decisions.md` are absent; `board.md`, t1/t2 artifacts, and the t3.1-teamlead resolution contain the current run context.
- Wrong assumptions and corrections: the previous t3 artifact treated the healthcheck/`depends_on` wording as unresolved; t3.1 settles it—healthcheck all five services, declare only real dependency edges, and leave broker/PostgreSQL as roots.
- Debugging dead-ends and what actually worked: initial document assertions included healthcheck rows in the service count and used a case-sensitive phrase mismatch; scoping the assertion to the catalog table fixed the checker, with no architecture defect.
- Techniques/patterns worth reusing: validate service names, dependency edges, private ports, API paths, replay isolation, transaction ordering, and Mermaid constraints together as an architecture-contract check.
- Learnings consumed: [architect/replay-storage-and-contract]
