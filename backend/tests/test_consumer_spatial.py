from __future__ import annotations

import os
import unittest
from pathlib import Path

from shapely.geometry import Polygon

from consumer.spatial import Country, SpatialIndex, UNASSIGNED, UNASSIGNED_NAME


def country(code: str, display: str) -> Country:
    return Country(
        adm0_a3=code,
        name_es=display,
        admin_name=display,
        display_name=display,
        continent="Test",
        subregion="Test",
        source_props={"ADM0_A3": code, "ADMIN": display},
    )


class SpatialIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.getenv("NATURAL_EARTH_GEOJSON", "/app/data/paises.geojson")
        path = Path(configured)
        if not path.exists():
            path = Path(__file__).resolve().parents[2] / "frontend/public/datos/paises.geojson"
        cls.index = SpatialIndex.from_geojson(path)

    def test_loads_natural_earth_and_finds_chile(self):
        result = self.index.find_country(-70.0, -30.0)

        self.assertEqual(result.adm0_a3, "CHL")
        self.assertEqual(result.admin_name, "Chile")

    def test_ocean_point_is_not_assigned_to_nearest_country(self):
        result = self.index.find_country(-30.0, 0.0)

        self.assertEqual(result.adm0_a3, UNASSIGNED)
        self.assertEqual(result.display_name, UNASSIGNED_NAME)

    def test_shared_boundary_uses_lexicographically_smallest_code(self):
        a = country("AAA", "A")
        b = country("BBB", "B")
        index = SpatialIndex(
            (b, a),
            (
                Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            ),
        )

        result = index.find_country(1.0, 0.5)

        self.assertEqual(result.adm0_a3, "AAA")

    def test_rejects_non_wgs84_points(self):
        with self.assertRaises(ValueError):
            self.index.find_country(181, 0)


if __name__ == "__main__":
    unittest.main()
