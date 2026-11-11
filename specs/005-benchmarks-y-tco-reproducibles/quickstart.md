# Quickstart: ejecutar las mediciones

## Requisitos

- Docker Compose y servicio `consumidor` disponible.
- Caché histórico 2025 con manifest y doce meses y catálogo Natural Earth
  montados como en `compose.yaml`.
- No se necesita PostgreSQL para el benchmark; el runner no escribe en la BD.

## Ejecutar

Desde la raíz, PowerShell:

```powershell
docker compose build consumidor
docker compose run --rm --no-deps consumidor python -m scripts.benchmark_spatial `
  --input-dir /var/lib/observatorio/cache/historical `
  --countries /app/data/paises.geojson `
  --sizes 500 10000 100000 `
  --repetitions 3 |
  Tee-Object -FilePath 'specs\005-benchmarks-y-tco-reproducibles\evidence\benchmarks\spatial-benchmark.json'
```

La imagen del contenedor instala únicamente dependencias ya declaradas en
`backend/requirements.txt`. La ejecución one-off no reinicia ni detiene el
consumidor permanente. `Tee-Object` guarda stdout JSON y lo muestra; si falla
el comando, comprobar el código de salida antes de considerar válido el
archivo. El JSON contiene fecha UTC, versiones, hashes, conteos por mes,
repeticiones, tiempos y memoria trazada. El proceso de benchmark se ejecuta en
un contenedor one-off y no reinicia ni detiene el consumidor permanente.

En un host con el entorno backend instalado también se puede invocar desde
`backend/`:

```powershell
python -m scripts.benchmark_spatial `
  --input-dir ..\..\cache\historical `
  --countries ..\frontend\public\datos\paises.geojson
```

El artefacto de referencia se genera localmente durante la fase de
implementación; no hay valores esperados codificados en las pruebas. No se
comparan sus milisegundos con los números legados como si provinieran del
mismo hardware o la misma operación.

## Validar

```powershell
docker compose run --rm --no-deps consumidor python -m pytest -q /app/tests/test_benchmark_spatial.py
```

Verificar en la salida: tamaños solicitados, tres repeticiones por lote,
`cache_sha256`/`manifest_sha256`, ambiente, mediana, CPU, throughput y
`tracemalloc_peak_bytes`. En el lote de 100.000, revisar explícitamente
`source_events_reused`; si no es cero, el número indica búsquedas repetidas,
no eventos distintos.
