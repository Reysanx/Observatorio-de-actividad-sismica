# Límites de las métricas de exactitud

## No hay verdad de referencia independiente

Las fuentes disponibles no incluyen una catalogación sísmica independiente que permita confirmar si cada magnitud, profundidad, tiempo o ubicación representa la realidad instrumental. Por ello, la **exactitud sísmica absoluta no es verificable** y el informe no publica una tasa de exactitud global.

## Proxies publicados

En la ejecución identificada en [quality-report.json](./quality-report.json) se midieron dos comparaciones:

1. **Preservación del payload**: igualdad del Feature GeoJSON cacheado con `historical_2025.raw_payload`, para 18.302 IDs emparejados: 18.302/18.302 (100%).
2. **Fidelidad de columnas canónicas**: igualdad por `event_id` entre magnitud, tipo, profundidad, tiempos, lugar y coordenadas de la Feature y sus columnas persistidas: 18.302/18.302 (100%).

Estos resultados muestran que el valor fue conservado o transformado como se esperaba para esta cohorte; no demuestran que la fuente USGS sea correcta. El segundo proxy depende del mismo Feature como origen, no de una fuente de verdad independiente.

La concordancia espacial con Natural Earth no se cuantificó en esta ejecución. Aunque se puede comparar la asignación del pipeline con el catálogo cartográfico, el resultado solo mediría concordancia con esos polígonos y esa versión del catálogo, no la ubicación física del sismo.

## Interpretación geográfica y otras limitaciones

- «Sin país asignado» (`N/A`) significa que no hubo una asignación de polígono; no es un fallo de exactitud ni prueba por sí solo que el evento sea submarino.
- La caché está filtrada a terremotos M≥4 y deduplicada antes de guardarse; no permite medir errores o eventos descartados antes de la caché.
- La fidelidad del payload y las columnas no valida la calidad de la medición sísmica original.
- Los datos live, replay y sintéticos no son referencia para verificar exactitud histórica y se mantienen fuera de esa cohorte.
