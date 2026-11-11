# Investigación y decisiones

## Semántica de `ingestion_audit`

El esquema en `backend/db/init.sql` limita `source` a `usgs_live` y
`usgs_2025`; registra `poll_id`, solicitud/respuesta, código HTTP, hash,
conteos, estado y error. El productor crea `record_type=poll_audit` después de
cada intento del feed live. El consumidor llama a `persist_poll_audit` y hace
`ON CONFLICT (poll_id) DO NOTHING`. El health endpoint consulta el último poll
live exitoso.

Por tanto, el grano es **un intento de sondeo de una fuente de ingesta**. No
hay campos para ruta API, usuario, parámetros ni duración/respuesta HTTP de
una consulta de usuario. No reutilizar esta tabla para lecturas API. Si se
requiere ese requisito evaluativo, diseñar una tabla separada y minimizar los
datos personales registrados.

E-03 de `specs/001-observatorio-sismico/evaluation-rubric.md` llama
«auditoría de consultas» a `ingestion_audit`. Esa frase debe interpretarse o
corregirse como «auditoría de ingesta/procedencia» para coincidir con la
implementación actual; de otro modo, el registro de consultas de usuario es un
requisito independiente aún no implementado.

## Tres conjuntos y ejecución verificable

1. **USGS live**: el sondeo continuo queda auditable en la BD. La captura
   (`2026-11-11T12:16:44.768287Z`) consultó 639 polls exitosos (HTTP 200),
   con 130.387 registros recibidos, 128.219 aceptados, 2.168 excluidos, cero
   cuarentenas y cero errores; el
   rango observado fue 2026-11-06 a 2026-11-11 UTC. El intervalo mediano es
   60 s. En los 637 registros anteriores a la corrección, las marcas a segundos
   producen duración mediana 0 ms y p95/máxima 1.000 ms; son valores
   cuantizados. Los 2 polls nuevos con precisión subsegundo miden una mediana de
   195,568 ms (p95 285,172 ms; máximo 295,128 ms).
2. **USGS histórico 2025**: el caché de doce meses tiene 18.302 Features y
   18.302 IDs únicos, y la tabla `dataset_imports` registra la importación
   `usgs_2025_magnitude_4_v1` con 18.302 eventos. El manifest se generó en
   `2026-11-09T17:40:49.385505Z`; la verificación local tardó 0,154 s. El
   bootstrap previo terminó con código 0, pero el esquema no conserva el tiempo
   de descarga ni el de escritura a BD.
3. **Natural Earth**: catálogo local `paises.geojson`, cargado con el
   `SpatialIndex` de producción. Se verificaron 177 Features, sin errores; la
   carga/construcción tardó 0,039 s.

Estos valores son observaciones del estado consultado el 2026-11-11; la salida
JSON es la fuente exacta y reproducible de conteos, timestamps, hashes y
duraciones medibles. No se simulan errores: un cero indica que no se encontró
un error en el conjunto consultado, no una garantía de disponibilidad futura.

## Tratamiento temporal

La función `utc_timestamp` del productor serializaba timestamps a segundos,
aunque PostgreSQL permite microsegundos. Se actualiza a conservar fracciones
de segundo para nuevos mensajes. Las filas existentes permanecen con su
precisión original y no pueden reconstruirse retroactivamente.

## Decisión de alcance

El informe es de solo lectura: verifica fuentes, historial auditado e
importación presente. No re-descarga USGS ni ejecuta otra importación. Los
tiempos de cache-check y carga del catálogo se miden en esta ejecución; las
duraciones del fetch de histórico/import a BD se documentan como no disponibles.
