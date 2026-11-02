# Local Replay Validation Boundaries

For a local-only MVP, validate replay isolation and outage recovery without deploying a public tunnel or conflating the browser tier with Docker availability.

## What Happened

For Observatorio de actividad sísmica task t6, the inherited acceptance matrix named ngrok outages, but approved upstream scope explicitly excluded ngrok/Netlify publication. The plan maps those cases to simulated local API failure/recovery and keeps Playwright independent from Compose/PostgreSQL/Kafka integration. The API contract is unauthenticated, so negative query validation is appropriate instead of inventing an auth flow. The current shell has Node.js but no running Docker daemon.

## Takeaway

Treat Docker infrastructure and browser automation as independent test capabilities. Use run-scoped replay fixtures to prove live counts/state are unchanged; simulate local API loss/recovery in browser tests. If Docker is unavailable, escalate and mark database/Kafka integration unverified—do not skip browser testing when Node/Playwright can still run, and do not claim a public tunnel test.

## History
- 2026-11-02 (Observatorio-de-actividad-s-smica/t6): initial
