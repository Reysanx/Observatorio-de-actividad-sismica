# Quickstart: Reproducción del análisis 6D

El módulo `scripts.quality_report` genera el informe reproducible en un contenedor existente. No añade servicios ni modifica el esquema de PostgreSQL.

## Prerrequisitos

- Docker Compose y el archivo `.env` local configurado según `.env.example`.
- Contenedores `almacenamiento` y `api` disponibles.
- Caché completa USGS 2025 montada en `/var/lib/observatorio/cache/historical`, con sus 12 GeoJSON y manifest verificado.
- Importación `usgs_2025_magnitude_4_v1` presente en PostgreSQL.
- Los datos de entrada no se descargan ni modifican durante una reproducción.

## Ejecución esperada

Desde la raíz del repositorio:

1. Rebuild del servicio API para incluir el módulo tras actualizar el repositorio:

   ```powershell
   docker compose up -d --build api
   ```

2. Desde la raíz del repositorio, ejecutar y guardar stdout como UTF-8 sin BOM:

   ```powershell
   $outputPath = 'docs\evidence\data-quality\quality-report.json'
   New-Item -ItemType Directory -Force (Split-Path $outputPath) | Out-Null
   $json = docker compose exec -T api python -m scripts.quality_report | Out-String
   if ($LASTEXITCODE -ne 0) { throw 'No se pudo generar el informe 6D.' }
   [System.IO.File]::WriteAllText(
     (Join-Path (Get-Location) $outputPath),
     $json,
     [System.Text.UTF8Encoding]::new($false)
   )
   ```

3. La ejecución debe terminar con código 0 y producir un único objeto JSON; stderr puede contener errores y no debe guardarse como JSON.
4. Actualizar la memoria de calidad solo con resultados observados y su identidad; nunca reutilizar cifras ilustrativas como mediciones.

## Resultado esperado

- Un objeto JSON que valida contra [quality-report.schema.json](./contracts/quality-report.schema.json).
- Para cada población: filtros, periodo cuando aplica, número de entradas, identidad/hash y resultados de las seis dimensiones.
- Cada cifra tiene numerador, denominador, fórmula, unidad y origen de evidencia, o queda explícitamente no verificable con causa.
- Cada población contiene exactamente una entrada por dimensión y puede incluir varias submétricas (por campo, latencia, estadístico o regla). Cada transformación informa etapa, recuento de afectados, denominador y política de solapamiento; etapas sin auditoría se marcan no verificables y sus recuentos no se inventan.
- La caché y las filas históricas se emparejan por `event_id`; las colisiones de ID conflictivas fallan explícitamente y faltantes/no emparejados se cuantifican.
- Las métricas live de polls, estado actual y cuarentena son poblaciones separadas; no se usan para reconciliar el histórico.
- Exactitud absoluta aparece como no verificable sin referencia independiente. Las comparaciones Feature→payload/columnas se identifican como proxies limitados; Natural Earth no se usa como ground truth.
- `Sin país asignado`, nulos legítimos y magnitudes/profundidades negativas se conservan según las reglas vigentes.
- Ninguna tabla, offset Kafka, caché ni registro de negocio cambia como efecto del comando.

## Validación

- Ejecutar `docker compose exec -T api python -m pytest -q /app/tests/test_quality_report.py`.
- Validar `docs/evidence/data-quality/quality-report.json` contra [quality-report.schema.json](./contracts/quality-report.schema.json).
- Ejecutar el comando dos veces con la misma caché y snapshot de BD: los resultados históricos y su identidad deben coincidir; `generated_at_utc` cambia y los datos live pueden cambiar si avanza el productor.
- Confirmar que historical/current/quarantine no cambian por el reporte. Las filas de auditoría live sí pueden crecer debido al productor que sigue ejecutándose.
- Validar por separado cualquier población live y sintética. No mezclarlas en resultados históricos ni presentarlas como una línea base «antes» inventada.

## Reproducir desde cero

Si la caché o la importación aún no existen, seguir primero el procedimiento de descarga e importación histórica documentado por el proyecto. El proceso de análisis no descarga ni importa datos.
