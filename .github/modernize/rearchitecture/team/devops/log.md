## [t7] Prepared local runtime toolchain
- Python 3.11.9 was installed with WinGet; `py -3.11` and an explicit PATH activation both resolve to the requested interpreter.
- Node 22.15.0 and Compose v5.6.1 were already installed. Docker Desktop was present but its daemon was stopped; starting Docker Desktop made `docker info` succeed.
- Pinned Playwright CLI 1.64.1 installed Chromium/headless browser binaries; an `about:blank` screenshot smoke test passed.
- The task is environment preparation only. The Compose project and frontend test manifest are downstream scaffold work; do not interpret an empty `docker compose ls` as an application failure.
- Missing workflow files: `context.md`, `decisions.md`, and the prior devops log/inbox did not exist. The board was read-only and left untouched.
- Learnings consumed: [(none)]

## [t8] Scaffolded the five-service local runtime
- Codebase/domain discoveries: t3 architecture fixes service IDs/topics and startup edges; old plan examples using `kafka`, `postgres`, and `earthquakes-replay` must not leak into Compose. Kafka can initialize both exact topics from the broker container, keeping the required service count at five.
- Wrong assumption and correction: on Windows, the mounted Bash script initially had CRLF despite being a new file; the first smoke failed on `pipefail\r`. Normalize the script and enforce `*.sh eol=lf` with `.gitattributes`.
- Verification pattern: rendered Compose JSON checks the service count, health checks, dependency conditions, and published ports; a separately named Compose project permits starting and removing the broker smoke test without touching application volumes.
- Remaining integration prerequisite: producer/consumer/API source, backend requirements, and Natural Earth GeoJSON are pending downstream implementation tasks; the full stack has not yet been built or started.
- Learnings consumed: [devops/windows-toolchain-preparation]

## [t13.1] Remediated frontend npm advisories
- Codebase/domain discoveries: the Angular 21 patch releases resolve runtime/compiler advisories without a major upgrade; `npm audit` also identified transitive vulnerabilities in CLI tooling packages.
- Wrong assumption and correction: an incremental install against the old package-lock peer graph failed even after updating the manifest. Regenerating the lock from the pinned manifest (without force flags) resolved it.
- Techniques worth reusing: use exact npm overrides for only the patched-major `glob` and `minimatch` transitive cases, then validate with a clean `npm ci`, full `npm audit`, tests, and build.
- Learnings consumed: [(none)]

## [t17.1] Restored producer and consumer readiness
- Codebase/domain discoveries: the prior runtime had PostgreSQL/API healthy while Kafka and consumer were stopped and producer was absent; the reason for the stop was not established. Recreating the services restored live processing without changing persisted state.
- Operational choice: worker health requires a fresh event-loop heartbeat plus broker reachability; the consumer additionally checks PostgreSQL. Heartbeats run every 10 seconds and expire after 45 seconds, while USGS source availability remains a freshness concern rather than liveness.
- Verification: exact five-service Compose topology, all five healthy, producer/consumer unit suites and health-probe tests, live records persisted, consumer offsets at zero lag, and API health returned 200.
- Learnings consumed: [devops/compose-kafka-runtime]
