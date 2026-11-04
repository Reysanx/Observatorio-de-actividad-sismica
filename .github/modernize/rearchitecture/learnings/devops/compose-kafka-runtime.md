# Compose Kafka Runtime

For this Windows-hosted project, Compose-mounted Kafka shell scripts need LF enforcement and the Kafka broker can provision topics itself without adding a sixth service.

## What Happened
In Observatorio de Actividad Sísmica task t8, the first broker smoke test failed because the Windows-generated CRLF line ending made Bash read `pipefail\r` as an invalid option. Normalizing the entrypoint and adding `.gitattributes` with `*.sh text eol=lf` fixed the repeat test. The same broker container now creates `earthquakes.live` with three partitions and `earthquakes.replay` with one, both at 48-hour retention, before it reports healthy.

## Takeaway
For shell scripts bind-mounted into Linux containers from Windows checkouts, commit an explicit LF policy and test the actual container entrypoint. Initialize deterministic Kafka topic partition/retention settings from the broker's own startup path to preserve the exact service count; make creation idempotent and verify topic descriptions before marking broker health. For Python workers, combine an event-loop heartbeat with direct dependency probes: a 10-second heartbeat cadence and 45-second expiry catches a stalled loop while tolerating the 60-second USGS polling interval. Do not make external source availability a worker-liveness condition.

## History
- 2026-11-02 (Observatorio-de-actividad-s-smica/t8): initial
- 2026-11-02 (Observatorio-de-actividad-s-smica/t17.1): added Python worker heartbeat and dependency-probe guidance
