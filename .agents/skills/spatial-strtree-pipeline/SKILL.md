---
name: spatial-strtree-pipeline
description: >-
  Procedimiento para indexar el catálogo cartográfico de Natural Earth en un árbol espacial
  STRtree de Shapely y resolver operaciones punto-en-polígono con manejo de sismos marítimos.
---

# Procedimiento de Enriquecimiento Espacial con STRtree

Esta habilidad guía la integración geoespacial eficiente entre las coordenadas del terremoto y los polígonos de países.

## 1. Carga e Indexación de `paises.geojson`
1. Al iniciar el consumidor, cargar `frontend/public/datos/paises.geojson` mediante `geopandas` o `shapely`.
2. Validar que las geometrías estén en coordenadas **WGS84 (EPSG:4326)**.
3. Construir un índice espacial en memoria con `shapely.strtree.STRtree(geometrias)`.

## 2. Búsqueda Punto-en-Polígono en $O(\log N)$
1. Crear el punto con las coordenadas del evento: `pt = Point(geom_lon, geom_lat)`.
2. Consultar candidatos en el árbol: `candidate_indices = tree.query(pt)`.
3. Filtrar intersección exacta: `polygon.contains(pt)` o `polygon.intersects(pt)`.

## 3. Reglas de Asignación Obligatorias
- **Caso A (Interior de País):** Asignar atributos `ADM0_A3`, `NAME_ES`, `ADMIN`, `CONTINENT` y `SUBREGION`.
- **Caso B (Océano o Dorsal Marina):** Si ningún polígono contiene el punto:
  - `adm0_a3 = "N/A"`
  - `country_name = "Sin país asignado"`
  - *Prohibición:* No aproximar al país más cercano ni extraer país del texto descriptivo `place`.
- **Caso C (Frontera Compartida):** En caso de coincidencia múltiple por tolerancia, seleccionar el país con menor orden lexicográfico en `ADM0_A3`.
