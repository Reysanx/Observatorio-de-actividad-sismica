# Protocolo de benchmark reproducible

## Pregunta y alcance

Medir el coste de construir/cargar el índice de país y ejecutar la operación
real `SpatialIndex.find_country` sobre 500, 10.000 y 100.000 coordenadas de
Features del caché 2025. No se realizan escrituras de negocio. No es un
benchmark de extremo a extremo ni un benchmark SQL.

## Fuente y tratamiento

- Se requiere el manifest `2025_manifest.json` y exactamente doce archivos
  `2025_m??.geojson`.
- El runner falla explícitamente ante entradas ausentes, JSON inválido, una
  Feature/ID/posición malformada o coordenadas no finitas.
- Se ordenan los nombres de archivo y se recorre el conjunto en orden
  determinista.
- Para un lote mayor que la caché se reutilizan coordenadas en orden cíclico;
  la salida registra `source_events_reused`. Repetir ubicaciones controla el
  número de llamadas, pero no simula la distribución ni variedad de una
  población de eventos independiente.

## Repetición y métricas

Por defecto se realizan tres repeticiones después de hasta 1.000 búsquedas de
calentamiento por tamaño (acotadas por el número de coordenadas fuente). Se
registran valores individuales y mediana de:

- Tiempo transcurrido de pared con `time.perf_counter()`.
- CPU del proceso con `time.process_time()`.
- Asignaciones Python máximas con `tracemalloc`.
- Búsquedas por segundo y número de resultados «Sin país asignado».
- Tiempo/pico trazado de carga del GeoJSON de países e inicialización de
  `SpatialIndex`.

No se ejecuta GC manualmente ni se fijan afinidad/CPU: se preserva el entorno
normal y se registran plataforma, versión de Python, versión de Shapely y
hashes de entrada. Para comparar cambios de código se recomienda la misma
máquina, mismos ficheros, misma configuración y varias ejecuciones completas.

`tracemalloc` no mide RSS, estructuras C/GEOS, bibliotecas cargadas ni las
coordenadas que el runner ya leyó. Los datos de carga de índice y el pico
trazado del lote son ámbitos de memoria diferentes y no deben sumarse como
«RAM total del consumidor».

## Interpretación

La primera ejecución puede estar afectada por lectura de disco y cachés frías;
las repeticiones ocurren en el mismo proceso y tienen cachés calientes. La
mediana ayuda a limitar el efecto de valores extremos, pero no sustituye un
estudio de variabilidad. La llamada Python mide lookup más filtrado exacto
GEOS, no la ingesta Kafka, DB o API.

No se reporta comparación “con/sin índice” en PostgreSQL a partir de este
runner. Para medir otros subsistemas se necesita un procedimiento específico,
misma consulta/datos, plan y entorno documentados.
