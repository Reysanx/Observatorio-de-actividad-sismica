# Research: decisiones de benchmark y TCO

## Benchmark

- **Fuente primaria**: manifest y GeoJSON mensuales ya cacheados del catálogo
  USGS 2025, no una descarga nueva. Se registran hash del manifest, hash
  agregado de los archivos, conteos mensuales y número de IDs distintos.
- En la ejecución de referencia el caché tuvo 18.302 Features y 18.302 IDs
  distintos; el catálogo Natural Earth produjo 177 entradas del índice. Son
  propiedades de esos ficheros concretos, identificados por sus hashes.
- **Operación medida**: construcción/carga del índice de países Natural Earth
  con el constructor de producción y ejecución repetida de
  `SpatialIndex.find_country` sobre coordenadas de las Features históricas.
- **Tamaños**: 500, 10.000 y 100.000 llamadas. Las coordenadas se recorren de
  forma cíclica y determinista si el conjunto de entrada es menor; la salida
  cuantifica las llamadas que reutilizan la muestra.
- **Métricas**: `time.perf_counter()` (tiempo transcurrido),
  `time.process_time()` (CPU del proceso) y `tracemalloc` (pico de asignaciones
  Python durante el lote). Tres repeticiones tras hasta mil lookups de
  calentamiento. Se informa mediana y valores de cada repetición.
- **Alcance**: microbenchmark de geolocalización en proceso. No incluye
  transporte, deserialización Kafka, validación integral del mensaje,
  transacción/índices PostgreSQL, API ni memoria RSS total.
- **Sin inferencia**: no se estima a partir de este benchmark el throughput de
  producción ni la latencia de base de datos. Para la justificación de índices
  existen planes PostgreSQL independientes en la
  [spec 004](../004-modelado-y-evidencia-indices/quickstart.md).

## Complejidad

- La búsqueda hash del productor tiene O(1) esperado, no garantía determinista
  universal. La inserción/conflicto de PostgreSQL usa búsquedas B-Tree con
  coste logarítmico en el número de entradas del índice.
- STRtree/R-tree es una estructura de búsqueda espacial: el rendimiento
  promedio depende de la distribución espacial y candidatos; en el peor caso
  puede examinar O(M) envolventes. Las comprobaciones geométricas exactas
  dependen además de los vértices de los polígonos candidatos.
- Una agregación temporal indexada puede costar O(log N + K) por localizar y
  recorrer K filas; el planificador puede elegir Seq Scan según selectividad,
  estadísticas y tamaño. La agregación/ordenamiento añade trabajo por filas y
  grupos.

## TCO y fuentes

Las referencias comerciales recuperadas el **2026-11-11** están enlazadas en
[`tco-model.md`](./tco-model.md). Son páginas públicas de planes, no contratos
ni una cotización del despliegue. Los precios eléctricos citados por Eurostat
corresponden a una categoría y periodo estadístico concretos, no a una factura
del proyecto.

Los valores históricos del TCO se evalúan aritméticamente en ese documento.
La resta y multiplicación pueden comprobarse sin que la tarifa, el hardware,
el uso, la amortización ni las horas de mantenimiento se conviertan en hechos
observados.
