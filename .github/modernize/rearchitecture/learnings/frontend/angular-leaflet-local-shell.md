# Angular Leaflet Local Shell

Pin a Node-compatible Angular CLI, load the API URL at runtime, and keep the first Leaflet view focused on live map data and clear offline behavior.

## What Happened

For the Observatorio de actividad sísmica MVP (t13), Node 22.15.0 met Angular 21's published engine range but not Angular 22's; Angular 21.2.4 was pinned. The standalone map loads its API base from `public/config.json`, requests only live events, renders Natural Earth country polygons and depth-coded Leaflet markers, and retains the last valid data after request failures. In this Windows workspace, Angular CLI's Vitest worker timed out on a path containing `&`; a small Node built-in test suite over shared `.mjs` helpers passed from the real path. Vite dependency prebundling also failed at dev-server startup, so the local `start` script disables prebundling.

After t13.1 advanced Angular CLI/build tooling to 21.2.29, the existing `--prebundle=false` start argument failed with “Unknown argument: prebundle”; the separated boolean form `--prebundle false` started correctly. Rechecking the live API also found its health timestamp is `last_event_ingested_at`, not the earlier frontend guess `latest_live_event_ingestion_utc`, so the UI was aligned to the observed contract and backend was notified.

## Takeaway

Check Angular's official Node compatibility table before pinning versions. Keep API origin as a runtime config value; use `127.0.0.1` when the backend publishes only on IPv4 loopback. On Windows paths with shell metacharacters, prefer direct Node script invocations and test runners that do not depend on shell worker startup. Keep map rendering helpers in one module shared by the UI and unit tests.
When Angular CLI parses a boolean option unexpectedly after a patch update, check `ng serve --help` and invoke the boolean as a separate value (`--prebundle false`) before assuming the option was removed. Use runtime API JSON as evidence for field spelling when architecture artifacts specify semantics only, and notify backend when reconciling a contract.

## History
- 2026-11-02 (Observatorio-de-actividad-s-smica/t13): initial
- 2026-11-02 (Observatorio-de-actividad-s-smica/t13): rechecked remediated Angular CLI arguments and aligned health DTO to live response
