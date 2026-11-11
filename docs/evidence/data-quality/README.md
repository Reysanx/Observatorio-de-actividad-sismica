# Evidencia reproducible de calidad 6D

## Alcance e identidad

El informe [quality-report.json](./quality-report.json) se generó con el comando del quickstart en modo de solo lectura y valida contra el contrato [quality-report.schema.json](../../../specs/003-metricas-calidad-6d/contracts/quality-report.schema.json).

La población histórica es el extracto GeoJSON USGS del 1 de enero de 2025 al 1 de enero de 2026 UTC, filtrado por `type=earthquake` y `M>=4.0`. El informe registra:

- Manifest: `2025_manifest.json`; SHA-256 `55d0e7719f18d7dcbc11b0da937915e529572e2e9e8c924acfe1962e4435dc73`.
- Instantánea de filas históricas persistidas: SHA-256 `b2ff83624cd5166c9b044b74dd929ed1f526b31374582b638db47dee35d4e1a7`.
- Regla y método: `historical.py:1.0;quality.py:1.0` y método `1.0`.
- Ejecución: `2026-11-11T10:52:39.432558Z`; identidad determinista `6afb2e2d3c2675d94c1e51a5af5c6fc7ddff23a81a4fc5eeb9b501498ca1a4a3`.

Los hashes y resultados corresponden a esa ejecución concreta. Una regeneración posterior crea una nueva identidad si cambia la base de datos observada, la caché o su manifest.

## Resultados históricos observados

La caché contenía 18.302 Features únicos y la tabla `historical_2025` tenía 18.302 filas. El emparejamiento por `event_id` encontró 18.302 filas coincidentes, 0 ausentes y 0 filas persistidas sin Feature correspondiente.

| Dimensión | Resultado de esta ejecución |
|---|---|
| Completitud | Los siete campos medidos (`event_id`, `mag`, `magType`, `place`, tiempos y coordenadas) presentaron 18.302/18.302 valores no nulos, tanto en el Feature como en las columnas correspondientes. `magType` y `place` son opcionales: su ausencia no sería por sí sola un error. |
| Unicidad | 18.302/18.302 IDs únicos en la cohorte cacheada y 18.302/18.302 en la tabla. |
| Validez | 18.302/18.302 Features satisfacen las reglas de importación histórica; 18.302/18.302 filas satisfacen las reglas almacenadas evaluadas. |
| Consistencia | 18.302/18.302 filas emparejadas conservan un ID y tiempos coherentes entre el payload y las columnas temporales. |
| Actualidad | Para `updated - time` del catálogo fuente: mínimo 5.164.538.646 ms; mediana 6.649.297.031,5 ms; p90 7.597.780.858,7 ms; máximo 53.162.893.575 ms. Es el intervalo entre ocurrencia y actualización fuente, no latencia de procesamiento del pipeline. |
| Exactitud | Fidelidad payload→`raw_payload`: 18.302/18.302 (100%); fidelidad Feature→columnas canónicas: 18.302/18.302 (100%). Ambas son proxies de persistencia, no verdad sísmica independiente. La exactitud absoluta no es verificable. |

La consulta de normalización histórica ya exige M≥4 y el descargador filtra y deduplica antes de escribir los archivos. El feed bruto previo no se conserva; el informe marca como no verificables los descartes previos a caché y la cuarentena histórica. Los recuentos de transformaciones con etapas distintas no se suman como categorías exclusivas.

## Observabilidad live separada

En esta ejecución, la instantánea incluyó 555 polls live, con 113.942 registros recibidos, 112.110 aceptados y 1.832 excluidos. La tabla de estado actual contenía 693 eventos y `quarantine_events` contenía 0 filas. Estas poblaciones no se mezclan ni se usan para reconciliar la caché histórica. Los polls son observaciones repetidas del feed, no IDs sísmicos únicos; la tabla de estado actual tampoco conserva cada entrega.

La demora `completed_at - requested_at` de esos polls tuvo mínimo 0 ms, mediana 0 ms, p90 1.000 ms y máximo 1.000 ms. Para el estado actual, `ingested_at - updated_utc` tuvo mínimo 4.530 ms, mediana 30.882.260 ms, p90 72.771.079,6 ms y máximo 85.959.750 ms. Los valores negativos, si apareciesen, no se recortan. No se afirma una reconciliación end-to-end de los registros aceptados, excluidos y cuarentenados: la auditoría no relaciona todas esas etapas con una misma entrada.

Los datos live cambian mientras funciona el productor. Al repetir el informe deben compararse las identidades y métricas de la población concreta; los resultados live pueden diferir de esta instantánea.

## Procedimiento

Desde la raíz del repositorio, con la caché histórica completa y los servicios `api` y `almacenamiento` disponibles:

1. Rebuild del servicio API para incluir el módulo del informe: `docker compose up -d --build api`.
2. Ejecutar el comando y capturar su JSON según [quickstart.md](../../../specs/003-metricas-calidad-6d/quickstart.md).
3. Validar `quality-report.json` con el contrato y mantener el archivo junto a esta explicación.

El programa usa una transacción PostgreSQL `REPEATABLE READ READ ONLY`; no descarga datos ni escribe en la base de datos, la caché o Kafka.
