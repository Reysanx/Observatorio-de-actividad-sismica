## [t11] Source and attribute Natural Earth countries
- Added the Natural Earth Admin-0 countries file at the exact consumer bind-mount path; kept raw properties/geometries unchanged.
- Natural Earth official terms designate map data public domain; recorded the recommended credit and linked official terms beside the data.
- Pinned the snapshot to v5.1.1 / commit `9380cca83db5f9aef52d5e762765100745f84b27`; GitHub's API reports the same data blob for the approved `master` URL.
- The pinned export has all required country fields and 177 unique `ADM0_A3` values; it includes `NAME_ES`, but the upstream version contract still requires `ADMIN` fallback.
- A first checksum assertion used a mistyped expected digest; corrected the recorded value from `Get-FileHash` and the SHA-256 assertion then passed.
- No host Shapely package was available. GeoJSON structure, coordinates, required attributes, checksum, and Compose config were verified; consumer runtime remains downstream.
- Workflow `context.md`, `decisions.md`, and frontend inbox/history were absent at task start; no conflict was found in the artifacts provided.
- Learnings consumed: [(none)]

## [t13] Build the minimal Angular map shell
- Added a standalone Angular 21 + Leaflet app with runtime API URL loading, live-only event/health polling, stale-data error handling, Natural Earth country polygons, depth-coded event markers, UTC popups, and map attribution.
- Chose Angular 21.2.4 because the active Node 22.15 toolchain meets Angular 21's documented engine range; Angular 22's current engine range did not include this Node patch.
- The t3 API artifact gives DTO semantics but not every JSON property spelling; made the UI expectation explicit (`latest_live_event_ingestion_utc`, event/page snake_case) and notified backend before its API task.
- Angular CLI's Vitest worker could not start reliably in the repo path containing `&`; replaced this minimal utility suite with Node's built-in test runner over the exact `.mjs` mapping helpers, which runs under the real workspace path.
- The first production compile identified a DatePipe import and SVG key-event type mismatch; both were fixed before the passing final build.
- Vite dependency prebundling crashed during local server startup; disabling it in the local `start` script allowed the map to serve. The app binds to localhost and defaults API requests to `127.0.0.1:8000`, matching Compose's loopback binding.
- Verification: 3 Node tests passed; Angular production build passed; `/`, `/config.json`, and `/datos/paises.geojson` returned 200; Playwright Chromium screenshot showed country boundaries and offline-state UI. Backend API remains unimplemented, so live event rendering was not verified.
- `npm install` reported 35 dependency vulnerabilities (including one critical); notified devops for the planned dependency-remediation task; no audit fix applied here.
- Learnings consumed: [frontend/natural-earth-data-provenance]

## [t13] Recheck Angular shell after dependency remediation
- Reinstalled the locked frontend dependencies after t13.1; `npm ci` and `npm audit --audit-level=low` reported zero vulnerabilities.
- The dependency patch advanced the Angular CLI to 21.2.29. The existing `--prebundle=false` syntax failed; `ng serve --help` confirmed the option and `--prebundle false` worked.
- Runtime probes confirmed the live health and earthquake routes return HTTP 200; the current live page is empty. The health field is `last_event_ingested_at`, so the frontend DTO now uses that key. Backend was notified because the API contract only specified semantics.
- Frontend tests (3), production build, four static-asset probes, and Chromium map render passed. Build still reports non-blocking optional `lmdb` and Leaflet CommonJS warnings.
- No replay, dashboard, or non-empty event data behavior was added to this bounded recheck.
- Learnings consumed: [frontend/angular-leaflet-local-shell, frontend/natural-earth-data-provenance]

## [t17] Add synchronized dashboard views
- Added shared UTC date/time, magnitude, depth, country, continent, and subregion filters; successful submissions refresh the event page and supported analytics from one snapshot.
- The comparison API is intentionally passed only geographic filters because its backend contract fixes the rolling 24-hour M4+ interval and supports no date/magnitude/depth parameters.
- Added SVG/CSS histogram and hourly charts plus a paginated, searchable loaded-page table; map markers and table rows share selection.
- Browser `datetime-local` inputs are explicitly interpreted as UTC by appending `Z`; never convert these user-entered values through the browser's local timezone.
- Initial API dataset is empty, so marker/pop-up behavior with real rows remains pending; API endpoints and empty/loading states rendered successfully.
- `docker compose --env-file .env.example ps` showed only `almacenamiento` and `api` healthy; alerted coordinator because ingestion services were down while the UI/API smoke still worked.
- A first dev-server launch with appended `--host` failed because the package's Angular CLI script rejected argument parsing; plain `npm start` starts on localhost as configured.
- The first implementation build caught a keydown callback variable shadowing the earthquake DTO; renamed the callback parameter and the final Angular build passed.
- Learnings consumed: [frontend/angular-leaflet-local-shell, frontend/natural-earth-data-provenance]
