# t11 — Natural Earth countries GeoJSON

## Summary

Added the Natural Earth Admin-0 countries GeoJSON at the exact public asset path
expected by the consumer and documented its source, public-domain terms,
attribution, pinned release, and data-field caveats. The source properties and
geometries are preserved without transformation.

## Deliverables

- `frontend/public/datos/paises.geojson` — Natural Earth 1:110m countries,
  release v5.1.1 (838,726 bytes).
- `frontend/public/datos/ATTRIBUTION.md` — source URLs, immutable version
  reference, official public-domain terms, suggested attribution, coordinate
  reference, and `NAME_ES`/`ADMIN` fallback note.

The approved upstream `master` URL and pinned v5.1.1 reference currently resolve
to the same Natural Earth Git blob. The local SHA-256 is
`6866c877d39cba9c357620878839b336d569f8c662d3cfab4cb1dbe2d39c977f`.

## Source and Naming Resolution

Followed the approved `nvkelso/natural-earth-vector` source at
`https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson`.
For reproducibility, documented release v5.1.1 and commit
`9380cca83db5f9aef52d5e762765100745f84b27`; Natural Earth's official download
page lists version 5.1.1. The official terms describe Natural Earth map data as
public domain and recommend (but do not require) the attribution included in
`ATTRIBUTION.md`.

Kept the canonical filename `paises.geojson`, the source `ADM0_A3` property,
and all other source properties unchanged. This pinned snapshot has `NAME_ES`
on its 177 features; consumers must still use `ADMIN` as fallback because the
upstream export does not guarantee that field across versions.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t7-devops.md` — verified toolchain
  assumptions and local-only boundaries.
- `.github/modernize/rearchitecture/artifacts/t8-devops.md` and
  `t8-devops-runtime.md` — confirmed the required bind-mount path and the
  consumer's read-only dataset mount.
- `.github/modernize/rearchitecture/artifacts/t5-ux.md` — required map/footer
  attribution and fallback handling for source country names.
- `.github/modernize/rearchitecture/artifacts/t1-teamlead.md` and
  `t3-architect.md` — approved source repository, public-domain attribution,
  canonical data path, and field fallback.
- `specs/001-observatorio-sismico/{spec.md,plan.md,tasks.md,data-spec.md,acceptance-tests.md}`
  and `.specify/memory/constitution.md` — GeoJSON path, WGS84/CRS84 coordinates,
  required country properties, maritime behavior, and no fabricated metadata.
- `.agents/AGENTS.md`, `.agents/rules/{architecture_invariants.md,data_quality_rules.md}`,
  `.agents/subagents/05-frontend-cartographer/AGENT.md`, and
  `.agents/skills/acceptance-testing/SKILL.md` — role, data, and UI constraints.
- `.agents/skills/spatial-strtree-pipeline/SKILL.md` — geometry contract and
  spatial-assignment requirements.

`context.md`, `decisions.md`, `team/frontend/log.md`, and
`team/frontend/inbox.md` did not exist at task start. No project-topology
fanout artifact or checklist directory was present.

## Evidence Mapping

- `t8-devops-runtime.md#Summary` (read-only consumer bind mount at
  `frontend/public/datos/paises.geojson`) → the checked-in file at that exact
  path; Compose config validation passed.
- `t5-ux.md#Product Decisions` item 5 → `ATTRIBUTION.md` contains the exact
  recommended Natural Earth citation and public-domain terms link.
- `t1-teamlead.md#Country boundaries and attribution` and
  `t3-architect.md#Risks and Handoff` → source repository recorded, Natural
  Earth fields preserved, and `ADMIN` fallback documented.
- `data-spec.md#1.3` and `spec.md#FR-03` → validation confirmed CRS84
  longitude/latitude coordinates, Polygon/MultiPolygon geometries, required
  country properties, and unique `ADM0_A3` codes.
- `data-spec.md#2` and `acceptance-tests.md#TC-07` → dataset remains an
  unmodified country-boundary catalog; ocean points are not inferred or assigned
  by nearest-country logic in this task.

## Test Results

- Command: `py -3.11 -` (inline JSON/schema/coordinate validation)
  - Passed: 1 validation suite — 177 features, Polygon/MultiPolygon geometries,
    10,654 coordinate positions in longitude/latitude bounds, required
    `ADM0_A3`/`ADMIN` properties, 177 unique codes, and declared CRS84.
  - Failed: 0
  - Skipped: 0
- Command: `py -3.11 -` (inline SHA-256 assertion)
  - Passed: 1; Failed: 0; Skipped: 0. Checksum matches the documented asset
    digest.
- Command: `docker compose --env-file .env.example config --quiet`
  - Passed: 1; Failed: 0; Skipped: 0. This validates Compose syntax only, not
    application startup.
- Command: `git check-ignore -v frontend/public/datos/paises.geojson frontend/public/datos/ATTRIBUTION.md`
  - Passed: 1; Failed: 0; Skipped: 0. Neither asset is ignored.
- Shapely STRtree smoke test: skipped; `py -3.11 -c "import shapely"` showed
  `ModuleNotFoundError`. This frontend data task does not install backend
  dependencies; consumer integration remains for the spatial-processing task.
- Overall: Passed 5 checks; Failed 0; Skipped 1. An initial checksum assertion
  exposed a transcription typo in the expected digest; the documentation was
  corrected and the checksum assertion passed on rerun.

## Scope and Handoff

This task supplies and documents the country asset only. It does not claim that
the Angular map, database country loader, full Compose application, or point-in-
polygon consumer has been implemented or runtime-verified. The map footer should
use the attribution recorded in `frontend/public/datos/ATTRIBUTION.md`.
