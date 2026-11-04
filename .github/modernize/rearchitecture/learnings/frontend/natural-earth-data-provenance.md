# Natural Earth data provenance

Pin the Natural Earth countries asset and keep attribution, public-domain terms, and schema caveats beside it.

## What Happened

For the Observatorio de actividad sísmica MVP (t11), the approved Natural Earth Vector repository supplied the Admin-0 GeoJSON. The official Natural Earth terms identify its raster/vector data as public domain and suggest an optional citation. A v5.1.1 release reference at commit `9380cca83db5f9aef52d5e762765100745f84b27` resolved to the same Git blob as the approved mutable `master` path, allowing the asset's provenance to remain aligned with the approved source while pinning an immutable snapshot. The checked-in file had 177 features and unique `ADM0_A3` values; the snapshot included `NAME_ES`, but consumers still need the documented `ADMIN` fallback.

## Takeaway

For public geographic datasets, document the upstream source URL, immutable version/commit, official license terms, recommended credit, file checksum, and any source-field guarantees next to the asset. Do not rely on a mutable branch or assume optional fields are guaranteed by future releases.

## History
- 2026-11-02 (Observatorio-de-actividad-s-smica/t11): initial
