# Implementation Plan: Benchmarks y TCO reproducibles

**Branch**: `main` (sin crear una rama nueva)  
**Spec**: [spec.md](./spec.md)

## Resumen

Añadir un benchmark reproducible de búsqueda punto-en-polígono que utiliza
`SpatialIndex.find_country` y el caché histórico 2025 identificado. Medirá
lotes de 500, 10.000 y 100.000 búsquedas, con repeticiones, tiempo de pared,
CPU y pico de memoria Python trazada. No escribirá en PostgreSQL o Kafka.
Auditará y corregirá cómo se presentan los números históricos de benchmarks y
TCO, separando cálculos comprobables de supuestos de planificación.

## Contexto técnico y límites

- Python 3.11 y Shapely 2.0.7 existentes; no se añade dependencia.
- Caché: manifest y doce GeoJSON mensuales montados en el contenedor
  `consumidor`; catálogo de países: `frontend/public/datos/paises.geojson`.
- El lote de 100k itera cíclicamente sobre las coordenadas observadas si la
  fuente tiene menos de 100k filas. No constituye una población de 100k eventos
  distintos.
- `tracemalloc` mide asignaciones Python durante la búsqueda; no incluye RSS,
  memoria nativa de GEOS ni la memoria ya ocupada por entradas cargadas.
- Los resultados puntuales dependen de plataforma, hardware, scheduling,
  versiones y estado de caché.
- La proyección TCO será un modelo paramétrico con referencias oficiales
  enlazadas; no se presenta como cotización o gasto facturado.

## Estructura

```text
specs/005-benchmarks-y-tco-reproducibles/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── tasks.md
├── benchmark-protocol.md
├── tco-model.md
└── evidence/
    └── benchmarks/
        └── spatial-benchmark.json

backend/
├── scripts/benchmark_spatial.py
└── tests/test_benchmark_spatial.py
```

La validación incluye pruebas del cargador/procedimiento, ejecución real sobre
la caché del contenedor Compose y `git diff --check`.

