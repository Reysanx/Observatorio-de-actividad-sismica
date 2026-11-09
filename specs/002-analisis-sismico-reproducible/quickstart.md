# Quickstart: Validate Reproducible Seismic Analysis

This is the validation guide for the feature; it does not replace the implementation task breakdown.

## Prerequisites

- Docker Desktop and Docker Compose v2 are running.
- Node.js supported by the existing Angular project is installed.
- The repository `.env` exists locally and contains a local-only password; never publish it.
- The historical USGS 2025 bootstrap has completed successfully and its dataset import record is present.

## 1. Verify the baseline before analysis

From the repository root in PowerShell:

```powershell
docker compose config -q
docker compose ps
docker compose ps -a historical-bootstrap
docker compose exec -T almacenamiento sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT dataset_key, event_count, imported_at FROM dataset_imports ORDER BY dataset_key;"'
```

Confirm all five long-running services are healthy and the historical bootstrap completed successfully. If the import is missing, incomplete, or failed, stop: do not publish annual comparisons as complete.

## 2. Reproduce the annual daily baseline

Run the analysis report-generation procedure produced by implementation from the API container (the implementation task will define the exact command). It must:

1. Select the historical 2025 population with `mag >= 4.5` and the declared geographic filters.
2. Produce one count for every UTC date from `2025-01-01` through `2025-12-31`.
3. Retain dates with no matches as count zero.
4. Save the 365 date/count pairs with the analysis evidence and verify that their sum is the reported historical total.
5. Compute the mean and population standard deviation using divisor 365.
6. Produce assigned/unassigned counts and shares for both the recent and historical populations, with explicit denominators and a note that “Sin país asignado” does not prove a submarine location.
7. Produce 2025 depth distribution summaries by the declared geographic area, including p90 and the valid-depth population count. The dashboard's live p90 must separately follow the visible event and geographic filters.
8. Classify the recent M≥4.5 count as within one SD, between one and two SD, beyond two SD, or unavailable, using the published comparison contract.

Record the query/method version, dataset import identity/count, exact filters, run time, all 365 counts, and the regional summaries. Do not copy illustrative contract values into evidence.

## 3. Validate the depth p90

Validate both the historical conclusion and the live dashboard response:

1. For the report conclusion, use the historical 2025 population, M≥4.5, the declared geographic filters, and the specified regional grouping. Record the finite, non-null depth count and compute its Type 7 p90 for each region.
2. For the dashboard, confirm p90 and population count use the selected live event and geographic filters, and that the panel shows units, period, and filters.
3. Verify p90 is null for an empty population, equals the only value for a single-value population, and is never produced by filling missing depths with zero.

## 4. Run focused automated checks

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_api_contract.py tests/test_acceptance.py
$testExit = $LASTEXITCODE
Pop-Location
if ($testExit -ne 0) { exit $testExit }

npm test --prefix frontend
npm run build --prefix frontend
```

The API tests must verify the 4.5 threshold, 365 zero-filled dates, identical geography filters, population-standard-deviation semantics, zero-variance handling, depth p90 interpolation/empty population, UTC periods, and live/replay isolation.

At each delivered increment (after User Story 1 and again after User Story 2), run the mandatory TC-01–TC-11 acceptance suite inside the API container:

```powershell
docker compose exec api pytest tests/test_acceptance.py -v
```

Record the result of each TC-01 through TC-11, including failures and their disposition, in `docs/evidence/seismic-analysis/acceptance-tc-01-to-11.md`. Do not declare an increment complete until the suite result has been recorded. The suite covers idempotency, chronological revisions, null magnitude, invalid coordinates/quarantine, unassigned maritime events, ngrok recovery, and replay identification; retain the focused feature tests above as additional checks.

## 5. Capture and reconcile evidence

Run the local dashboard and capture the analysis panels with period, threshold, and geographic filters visible. Save the images and the reproducibility output under `docs/evidence/seismic-analysis/`. Reconcile each conclusion in `docs/memoria_calidad.md` against the generated counts, percentages, depth percentile, and comparison statistics. Remove or clearly supersede any old figure that cannot be reproduced.

The final evidence set should let a reviewer repeat the calculations from the same dataset and filters. A changing recent window must be identified by its exact UTC start/end; it is not expected to remain numerically constant between runs.
