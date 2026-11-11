# Quickstart: generar evidencia de ingesta

Desde la raíz del repositorio, con Compose y los servicios `almacenamiento` y
`consumidor` en ejecución:

```powershell
docker compose build consumidor productor
$report = docker compose run --rm --no-deps consumidor python -m scripts.ingestion_evidence | Out-String
if ($LASTEXITCODE -ne 0) { throw 'Evidence report failed' }
[System.IO.File]::WriteAllText(
  'specs\006-evidencias-de-ingesta-y-auditoria\evidence\ingestion-run.json',
  $report,
  (New-Object System.Text.UTF8Encoding($false))
)
```

El comando solo lee PostgreSQL, el caché ya verificado y el GeoJSON Natural
Earth. No inicia una descarga ni hace cambios en datos. Devuelve error no cero
si faltan archivos, fallan sus checksums, el GeoJSON no valida o PostgreSQL no
está disponible. Guardar junto con el JSON la fecha UTC que devuelve
`database_snapshot_at_utc`; no modificar ni completar resultados manualmente.
Para que el productor continuo empiece a emitir timestamps con precisión
subsegundo tras el cambio del serializador, recrearlo explícitamente con
`docker compose up -d --no-deps productor`. Las filas históricas no cambian.

## Interpretación

- `usgs_live.evidence`: polls de fuente persistidos en `ingestion_audit`;
  `poll_interval_median_seconds` es cadencia, no latencia HTTP.
- `usgs_live.evidence.stored_duration_*`: diferencia de timestamps
  persistidos. Para filas antiguas a segundos se informa cuantización; no
  atribuir cero milisegundos como fetch instantáneo.
- `subsecond_duration_*`: métricas solo de polls cuya marca contiene fracción
  de segundo; excluyen filas históricas cuantizadas.
- `usgs_2025`: Feature counts por mes, SHA-256 y duración local de validación.
  `database_import` compara la fila de `dataset_imports` con conteos de la
  relación histórica. El tiempo de importación no fue persistido.
- `natural_earth_countries`: SHA-256, Features aceptadas y tiempo de carga más
  construcción del STRtree.
- `errors_by_code` cuenta errores de polls. `validation_errors`/`errors`
  vacíos significan que la verificación de esta ejecución terminó sin error.

La tabla `ingestion_audit` no registra consultas de usuarios. Si E-03 requiere
telemetría de lecturas de la API, debe definirse y almacenarse por separado;
no mezclar los dos granos.

## Pruebas dirigidas

```powershell
docker compose run --rm --no-deps consumidor python -m pytest -q `
  /app/tests/test_ingestion_evidence.py /app/tests/test_usgs_live_producer.py
```
