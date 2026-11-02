# Compose Health Dependencies

Define `depends_on: condition: service_healthy` only for real direct dependencies; require a healthcheck on every service without inventing edges for infrastructure roots.

## What Happened

For Observatorio de actividad sísmica task t3.1, the project rule required both a healthcheck and a dependency declaration on every service, while the five-service design has independent Kafka and PostgreSQL roots. The plan’s sample also showed distinct direct dependencies: producer→Kafka, consumer→Kafka and PostgreSQL, API→PostgreSQL. Fake edges would couple unrelated infrastructure and could create cycles. Docker's startup-order documentation confirms `service_healthy` is a startup gate and that `depends_on.restart` refers to explicit Compose operations, not automatic unhealthy recovery.

## Takeaway

Keep the Compose graph acyclic. Health-check all services, gate each actual dependency edge on `service_healthy`, and leave root services without `depends_on`. Remember that Compose health is a startup gate/status signal, not ongoing recovery or automatic dependent restart. See [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/).

## History
- 2026-11-02 (Observatorio-de-actividad-s-smica/t3.1): initial
