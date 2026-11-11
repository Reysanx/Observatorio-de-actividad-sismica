# Acceptance evidence TC-01–TC-11

**Run date:** 2026-11-09  
**Automated command:** `docker compose exec -T api python -m pytest tests/test_acceptance.py -v`  
**Result:** 8 passed, 0 failed.

**Post-US2 rerun:** `docker compose exec -T api python -m pytest -q -p no:cacheprovider tests/test_api_contract.py tests/test_acceptance.py` — 23 passed, 0 failed (including all 8 integration acceptance tests).

**Final workspace-source rerun:** `docker compose run --rm --no-deps -v "${PWD}\backend:/app" api python -m pytest -q -p no:cacheprovider tests/test_api_contract.py tests/test_acceptance.py` — 23 passed, 0 failed. The contract test also verifies that the 365-day query preserves dates with zero events.

**Final validation on 2026-11-11:** `docker compose exec -T api python -m pytest tests/test_acceptance.py -v` — 8 passed, 0 failed; repeated for the second delivery record — 8 passed, 0 failed. Focused API contracts plus acceptance tests — 23 passed, 0 failed. Frontend tests — 9 passed, 0 failed; production build succeeded with the existing LMDB, CSS budget, and Leaflet CommonJS warnings.

**Manual tunnel validation on 2026-11-11 (reported by the project owner):** with the Netlify dashboard open, stopping the ngrok tunnel changed the UI to disconnected in about 5 seconds and showed the tunnel connection error while retaining the last displayed data. Restarting the tunnel restored the connected state and refreshed data in about 5 seconds, without reloading the page. No browser screenshots were supplied for this run.

| Case | Result | Evidence |
|---|---|---|
| TC-01 | Passed | `test_tc01_to_tc04_live_insert_idempotency_and_revision_order`: a new event is persisted and visible through the API. |
| TC-02 | Passed | Exact duplicate and same-key re-delivery leave one current row/version; covered by the TC-01–04 and TC-08 tests. |
| TC-03 | Passed | The newer revision becomes the current row and is returned by the API in `test_tc01_to_tc04_live_insert_idempotency_and_revision_order`. |
| TC-04 | Passed | A stale revision does not replace the newer magnitude or add a version in `test_tc01_to_tc04_live_insert_idempotency_and_revision_order`. |
| TC-05 | Passed | `test_tc05_null_magnitude_is_persisted_as_null` verifies DB/API `NULL`; frontend test `missing magnitude and depth are presented as ND` verifies the display formatter. |
| TC-06 | Passed | `test_tc06_out_of_bounds_coordinates_are_quarantined` verifies quarantine reason/payload and absence from the current table. |
| TC-07 | Passed | `test_tc07_ocean_event_is_not_assigned_to_nearest_country` verifies `N/A` / “Sin país asignado” in DB and API. |
| TC-08 | Passed | `test_tc08_duplicate_redelivery_does_not_duplicate_current_state` verifies one current row and one version after re-delivery. |
| TC-09 | Passed | Manual Netlify browser validation reported by the project owner on 2026-11-11: after stopping ngrok, the dashboard showed disconnected/tunnel error in about 5 seconds and retained the last displayed data. |
| TC-10 | Passed | Manual Netlify browser validation reported by the project owner on 2026-11-11: after restarting ngrok, the dashboard reconnected and refreshed data in about 5 seconds without a page reload. |
| TC-11 | Passed | `test_tc11_replay_run_is_visible_but_never_enters_live_state` verifies API/database isolation. Browser check confirmed the “REPRODUCCIÓN” badge and isolated-mode banner when selecting replay. |

The two analysis acceptance tests also passed: report totals and manifest provenance reconcile with the imported 2025 baseline, and missing/incomplete baseline metadata is rejected. The latest report-generation check on 2026-11-11 verified 365 UTC daily rows summing to the historical M≥4.5 cohort (8,559) and matching imported/stored baseline counts (18,302). TC-09/TC-10 are manual observations reported by the project owner; the other acceptance tests are covered by the automated runs above.
