# Service Health and Dependency Policy

Give every Compose service a healthcheck, but add startup dependency edges only for real runtime prerequisites.

## What Happened

In `Observatorio-de-actividad-s-smica` task t3, the project rule's wording appeared to require `depends_on` for all services, including independent infrastructure roots. Teamlead task t3.1 resolved the inconsistency: healthcheck all five canonical services; use `condition: service_healthy` for producer→broker, consumer→broker/PostgreSQL, and API→PostgreSQL only. Kafka and PostgreSQL remain independent roots.

## Takeaway

Treat health reporting and startup dependency as separate concerns. Avoid artificial edges or cycles solely to satisfy broad wording; downstream Compose implementation should preserve the resolved acyclic graph and separately implement runtime retry/recovery.

## History
- 2026-11-02 (Observatorio-de-actividad-s-smica/t3): initial
