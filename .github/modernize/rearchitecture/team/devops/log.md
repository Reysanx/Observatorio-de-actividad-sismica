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
