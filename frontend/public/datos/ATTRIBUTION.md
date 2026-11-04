# Natural Earth countries data

The local map dataset `paises.geojson` is Natural Earth Admin 0 countries at
1:110m scale, GeoJSON format, release **5.1.1**. It is checked in so the
consumer and frontend can use the same country boundaries without a runtime
download.

## Source and version

- Approved GeoJSON source URL: [Natural Earth Vector,
  `ne_110m_admin_0_countries.geojson`](https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson)
- Reproducible snapshot: [same file at release v5.1.1](https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.1/geojson/ne_110m_admin_0_countries.geojson);
  the repository reports the same Git blob (`1e6ab74c7042f97013be69ceec798be8e1aff27d`) for both refs.
- Repository: [nvkelso/natural-earth-vector](https://github.com/nvkelso/natural-earth-vector)
- Pinned repository commit: `9380cca83db5f9aef52d5e762765100745f84b27`
- Official dataset page: [Admin 0 – Countries, 1:110m](https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/)
- Official terms: [Natural Earth Terms of Use](https://www.naturalearthdata.com/about/terms-of-use/)
- Local file SHA-256: `6866c877d39cba9c357620878839b336d569f8c662d3cfab4cb1dbe2d39c977f`

Natural Earth states that its raster and vector map data are **public domain**
and may be used, modified, and redistributed without permission. Attribution is
not required, but the project includes Natural Earth's suggested citation:

> Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com.

## Data notes

The source declares `urn:ogc:def:crs:OGC:1.3:CRS84` and stores geographic
coordinates in longitude/latitude order (WGS 84 values; used by this project as
EPSG:4326). The checked-in release has 177 Polygon/MultiPolygon features and
includes the country properties `ADM0_A3`, `ADMIN`, `CONTINENT`, `SUBREGION`,
and `NAME_ES`. `NAME_ES` is present in this pinned snapshot, but consumers must
not assume it will exist in every Natural Earth export: use `ADMIN` as the
documented fallback and preserve the source properties.

This is generalized 1:110m boundary data; it is intended for global context,
not authoritative legal boundary determination.
