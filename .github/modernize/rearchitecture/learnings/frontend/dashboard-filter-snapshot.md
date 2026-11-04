# Dashboard Filter Snapshot

Use one validated UTC filter snapshot for the map, event table, and every analytics endpoint that supports those filters.

## What Happened

For the Observatorio de actividad sísmica MVP (t17), the root Angular dashboard sends the event page, geographic summary, hourly buckets, and magnitude/depth distributions concurrently for the same validated filter object, then updates the visible dashboard only after the full response set succeeds. This retains a consistent last-known view on API failure. The historical comparison endpoint is a deliberate exception: its API contract fixes the rolling 24-hour M4+ interval and accepts geographic filters only, so the UI sends only country/continent/subregion and labels the fixed comparison clearly. HTML `datetime-local` values are interpreted as UTC by appending `Z`, not converted from the browser's timezone.

## Takeaway

Keep cross-view filters in one canonical applied snapshot, validate before issuing requests, and use an all-or-nothing response update when the UX must not show mismatched map and analytics data. Apply only parameters supported by each endpoint and explain fixed-window analytics rather than implying they share unsupported date or magnitude filters.

## History

- 2026-11-02 (`Observatorio-de-actividad-s-smica/t17`): initial
