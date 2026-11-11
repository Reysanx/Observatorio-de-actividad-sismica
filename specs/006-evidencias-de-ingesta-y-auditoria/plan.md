# Plan: Evidencias de ingesta y auditoría

## Alcance

Generar un reporte JSON de solo lectura con `backend/scripts/ingestion_evidence.py`.
El comando lee `ingestion_audit`, `dataset_imports` y `historical_2025`, valida
el caché 2025 usando el verificador de producción y construye el índice
Natural Earth con `SpatialIndex`.

No descarga de nuevo el histórico, no hace writes a Kafka/PostgreSQL y no añade
telemetría de consultas de usuario. No se altera el grano de
`ingestion_audit`; sus filas siguen siendo un intento de poll identificado por
`poll_id`.

## Evidencia y límites de medición

- Feed live: totales e intervalos calculados sobre todas las filas de
  `ingestion_audit`; su duración se obtiene de `completed_at - requested_at`.
- Histórico: `load_complete_cache` valida checksums y forma; se mide el tiempo
  de validación local. `dataset_imports` y las particiones confirman el estado
  de importación, pero no guardan duración de descarga/import.
- Natural Earth: se mide carga, validación geométrica y construcción de STRtree.
- Se preservará precisión subsegundo en timestamps de nuevos polls. Las filas
  antiguas serializadas con precisión de un segundo se reportan como
  cuantizadas, no como latencias exactas.

## Archivos

```text
backend/
├── producer/main.py
├── scripts/ingestion_evidence.py
└── tests/
    ├── test_ingestion_evidence.py
    └── test_usgs_live_producer.py

specs/006-evidencias-de-ingesta-y-auditoria/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── tasks.md
└── evidence/ingestion-run.json
```

## Validación

Ejecutar pruebas dirigidas en la imagen del consumidor, construir una captura
JSON real con la base y ficheros locales existentes, verificar sus tres
fuentes, enlaces internos y `git diff --check`.
