"""Natural Earth country lookup backed by an in-memory Shapely STRtree."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from shapely import make_valid
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.strtree import STRtree

UNASSIGNED = "N/A"
UNASSIGNED_NAME = "Sin país asignado"


@dataclass(frozen=True)
class Country:
    """Country metadata kept alongside each indexed boundary."""

    adm0_a3: str
    name_es: str | None
    admin_name: str
    display_name: str
    continent: str | None
    subregion: str | None
    source_props: dict[str, Any]


class SpatialIndex:
    """Point-in-polygon index; boundary ties resolve by ADM0_A3."""

    def __init__(
        self,
        countries: Sequence[Country],
        geometries: Sequence[BaseGeometry],
    ) -> None:
        if not countries or len(countries) != len(geometries):
            raise ValueError("country features and geometries must be non-empty and aligned")
        self.countries = tuple(countries)
        self._geometries = tuple(geometries)
        self._tree = STRtree(list(self._geometries))

    @classmethod
    def from_geojson(cls, path: str | Path) -> "SpatialIndex":
        """Load a WGS84/CRS84 Natural Earth FeatureCollection."""
        source = Path(path)
        try:
            collection = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"unable to load country GeoJSON: {source}") from exc

        if not isinstance(collection, dict) or collection.get("type") != "FeatureCollection":
            raise ValueError("country data must be a GeoJSON FeatureCollection")
        _validate_crs(collection.get("crs"))
        features = collection.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("country FeatureCollection must contain features")

        countries: list[Country] = []
        geometries: list[BaseGeometry] = []
        seen_codes: set[str] = set()
        for position, feature in enumerate(features):
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise ValueError(f"country feature {position} is malformed")
            properties = feature.get("properties")
            geometry_data = feature.get("geometry")
            if not isinstance(properties, dict) or not isinstance(geometry_data, dict):
                raise ValueError(f"country feature {position} lacks properties or geometry")

            code = properties.get("ADM0_A3")
            admin = properties.get("ADMIN")
            if not isinstance(code, str) or not code.strip():
                raise ValueError(f"country feature {position} lacks ADM0_A3")
            if code == UNASSIGNED:
                raise ValueError("Natural Earth ADM0_A3 must not use the reserved N/A code")
            if len(code) > 8:
                raise ValueError(f"country {code} exceeds the database code width")
            if code in seen_codes:
                raise ValueError(f"duplicate Natural Earth ADM0_A3 code: {code}")
            if not isinstance(admin, str) or not admin.strip():
                raise ValueError(f"country {code} lacks ADMIN")
            if geometry_data.get("type") not in {"Polygon", "MultiPolygon"}:
                raise ValueError(f"country {code} has unsupported geometry type")
            geometry = shape(geometry_data)
            if geometry.is_empty:
                raise ValueError(f"country {code} has an empty geometry")
            if not geometry.is_valid:
                # Keep the source properties untouched while repairing invalid
                # polygon topology for the in-memory predicate/index only.
                geometry = make_valid(geometry)
                if geometry.geom_type == "GeometryCollection":
                    polygon_parts = [
                        part
                        for part in geometry.geoms
                        if part.geom_type in {"Polygon", "MultiPolygon"}
                    ]
                    if not polygon_parts:
                        raise ValueError(f"country {code} has no polygonal geometry after repair")
                    geometry = unary_union(polygon_parts)
                if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
                    raise ValueError(f"country {code} repair did not produce polygonal geometry")
                if geometry.is_empty or not geometry.is_valid:
                    raise ValueError(f"country {code} geometry remains invalid after repair")

            name_es = _optional_text(properties.get("NAME_ES"))
            continent = _optional_text(properties.get("CONTINENT"))
            subregion = _optional_text(properties.get("SUBREGION"))
            countries.append(
                Country(
                    adm0_a3=code,
                    name_es=name_es,
                    admin_name=admin,
                    display_name=name_es or admin,
                    continent=continent,
                    subregion=subregion,
                    source_props=properties,
                )
            )
            geometries.append(geometry)
            seen_codes.add(code)

        return cls(countries, geometries)

    def find_country(self, longitude: float, latitude: float) -> Country:
        """Return the intersecting country or the ocean/unassigned sentinel."""
        if (
            isinstance(longitude, bool)
            or isinstance(latitude, bool)
            or not isinstance(longitude, (int, float))
            or not isinstance(latitude, (int, float))
            or not math.isfinite(longitude)
            or not math.isfinite(latitude)
            or not -180 <= longitude <= 180
            or not -90 <= latitude <= 90
        ):
            raise ValueError("point must contain finite WGS84 longitude/latitude")

        point = Point(float(longitude), float(latitude))
        matches: list[Country] = []
        # Shapely 2 STRtree returns integer indices into the geometry sequence.
        for candidate in self._tree.query(point):
            geometry_index = int(candidate)
            if self._geometries[geometry_index].intersects(point):
                matches.append(self.countries[geometry_index])
        if matches:
            return min(matches, key=lambda country: country.adm0_a3)
        return Country(
            adm0_a3=UNASSIGNED,
            name_es=None,
            admin_name=UNASSIGNED_NAME,
            display_name=UNASSIGNED_NAME,
            continent=None,
            subregion=None,
            source_props={"kind": "unassigned"},
        )


def _validate_crs(crs: Any) -> None:
    """Accept RFC 7946's implicit WGS84 or explicitly declared WGS84/CRS84."""
    if crs is None:
        return
    name: Any = None
    if isinstance(crs, dict):
        properties = crs.get("properties")
        if isinstance(properties, dict):
            name = properties.get("name")
    if not isinstance(name, str):
        raise ValueError("country GeoJSON declares an unsupported or malformed CRS")
    normalized = name.upper()
    if not any(marker in normalized for marker in ("4326", "CRS84", "WGS84")):
        raise ValueError(f"country GeoJSON must use WGS84/CRS84, got {name!r}")


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("country attributes must be strings or null")
    value = value.strip()
    return value or None
