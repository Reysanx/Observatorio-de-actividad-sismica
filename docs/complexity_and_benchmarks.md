# Complejidad algorítmica y benchmarks

> **Estado de evidencia (2026-11-11):** Las cifras heredadas de ingesta,
> throughput, memoria de consumidor, latencia API, series horarias y
> `EXPLAIN ANALYZE` que antes aparecían aquí no tenían salidas, entorno ni
> procedimiento reproducible asociados. Se retiran como resultados
> confirmados. La auditoría y el procedimiento vigente están en
> [specs/005-benchmarks-y-tco-reproducibles/](../specs/005-benchmarks-y-tco-reproducibles/).

## Complejidad teórica

Sean `N` las filas indexadas, `M` las geometrías de países, `K` las filas
elegibles de una ventana y `G` los grupos de agregación:

| Operación | Complejidad orientativa | Condiciones y límites |
|---|---|---|
| Búsqueda/deduplicación por hash del productor | O(1) esperada por acceso a `dict`; peor caso dependiente de colisiones | No es una garantía estricta de peor caso O(1). El productor es además una caché local, no el árbitro de unicidad durable. |
| `INSERT ... ON CONFLICT` de PostgreSQL | O(log N) para la búsqueda en el B-Tree, además del coste de escribir filas/WAL cuando hay cambios | Las PK/índices reales y reglas de UPSERT están en `backend/db/init.sql`; contención, disco y escritura añaden costes no expresados por esa cota. |
| `SpatialIndex.find_country` | En promedio, consulta del STRtree más pruebas exactas de los candidatos; peor caso O(M) candidatos, multiplicado por el coste geométrico correspondiente | El rendimiento depende de la distribución espacial, tamaño y solapamiento de los polígonos, y sus vértices. No se presupone que todo punto consulte solo uno o dos candidatos. |
| Agregación por ventana | O(log N + K) para localizar y recorrer un rango indexado, más agregación y posible ordenamiento de grupos | El planificador puede elegir Seq Scan; no se garantiza que toda consulta use el B-Tree ni latencia sub-10 ms. |

Estas son cotas/modelos de estructuras, no mediciones de velocidad ni
promesas SLA. Para la indexación PostgreSQL con planes observados y
reproducibles, véase la
[evidencia de la spec 004](../specs/004-modelado-y-evidencia-indices/data-model.md).

## Benchmarks

No se confirman las cifras antiguas de `48/890/8.740 ms`, `10.416/11.235/
11.441 eventos/s`, `42,3/43,8/49,1 MB`, latencias API/serie horaria ni las
comparaciones de consultas `8,6 ms` frente a `184 ms`: no se conservó el lote
ni su hash, código exacto, hardware, repeticiones, versión, consulta ejecutada
o salida de memoria/`EXPLAIN ANALYZE`.

El procedimiento que sí puede repetirse mide la operación real
`SpatialIndex.find_country` con los datos cacheados identificados, tres
tamaños, repeticiones y salida JSON:

- [Protocolo de medición](../specs/005-benchmarks-y-tco-reproducibles/benchmark-protocol.md)
- [Comando y validación](../specs/005-benchmarks-y-tco-reproducibles/quickstart.md)
- [JSON generado](../specs/005-benchmarks-y-tco-reproducibles/evidence/benchmarks/spatial-benchmark.json)

| Cifra publicada anteriormente | Resultado de la verificación |
|---|---|
| Ingesta STRtree: 48 ms / 890 ms / 8.740 ms para 500 / 10k / 100k | Sin salida, lote o entorno identificables: no verificable. |
| Throughput: 10.416 / 11.235 / 11.441 eventos/s | Cociente derivable aproximadamente de los tiempos anteriores; aritmética coherente, pero no verificación independiente ni conteo de IDs distintos. |
| RAM del consumidor: 42,3 / 43,8 / 49,1 MB | Sin definición de memoria, proceso o perfil: no verificable. |
| API Geo: 2,1 / 3,8 / 14,2 ms; serie horaria: 1,4 / 2,1 / 8,6 ms | Sin request/consulta, datos, cardinalidad o salida: no verificable. |
| `EXPLAIN ANALYZE (cost)`: `8.42..12.30`, `14.15..45.20`, `28.50..112.40` | `cost` son unidades estimadas del planificador, no milisegundos. Sin SQL/plan completo/dataset, no prueban rendimiento por lote. |
| Con índice 8,6 ms vs Seq Scan 184 ms (~21×) en 100k | El cociente `184 / 8,6 ≈ 21,4` es correcto; los tiempos/planes carecen de evidencia reproducible y se retiran como observación. |
| ~250 geometrías Natural Earth | No coincide con el catálogo medido de esta ejecución: 177 entradas. Usar recuento y hash del catálogo de cada reporte. |

El lote de 100.000 es un número de llamadas; si el caché contiene menos
coordenadas se recorren cíclicamente y el reporte cuantifica la reutilización.
No se etiqueta como 100.000 eventos únicos. `tracemalloc` es pico de
asignaciones Python durante la operación, no RSS total ni memoria nativa de
GEOS. El microbenchmark no mide Kafka, PostgreSQL, API o el pipeline completo.

## Proyección a 100 millones

Los antiguos `212 bytes/fila`, `10,4 GB` de índices, `31,6 GB` totales y
`~42 GB` con margen son **supuestos no medidos**, no un dimensionamiento
confirmado. La aritmética es consistente bajo esos supuestos:
`100M × 212 B = 21,2 GB` (decimal), `21,2 + 10,4 = 31,6 GB` y
`31,6 × 1,30 = 41,08 GB`, redondeado a 42 GB. Para planificar capacidad se
requieren tamaños de tabla/índice medidos con el esquema y datos representativos,
más WAL, backups, bloat, retención y margen de crecimiento.

El particionado temporal y archivado en almacenamiento columnar son
alternativas de diseño a evaluar, no garantías de mantener índices en RAM,
latencia submilisegundo o compresión de >75%. El esquema actual particiona la
línea histórica y versiones; `current_earthquakes` no está particionada,
deliberadamente, para conservar el conflicto global por `event_id`.
