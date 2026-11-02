# Replay mode UI isolation

Show replay run status separately from the dashboard's selected data scope so users can observe a run without mixing replay records into live views.

## What Happened
For the Observatorio de actividad sísmica MVP (t5), the API contract provides a passive replay-state endpoint and requires a `run_id` for replay queries, while live remains the default. Treating “a run is active” as equivalent to “the dashboard is displaying replay” would create scope ambiguity. A persistent run-status banner plus an explicit live/replay view selector preserves visibility and isolation.

## Takeaway
Keep global replay status distinct from selected view scope. Replay queries always include the selected `run_id`; live queries omit it or explicitly use `scope=live`. Never auto-switch the dashboard or fall back from a missing replay run to live data.

## History
- 2026-11-02 (Observatorio-de-actividad-s-smica/t5): initial
