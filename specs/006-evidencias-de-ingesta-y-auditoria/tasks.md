# Tasks: Evidencias de ingesta y auditoría

**Input**: [spec.md](./spec.md)  
**Plan**: [plan.md](./plan.md)

## Fase 1: Auditoría de semántica y precisión

- [X] T001 Confirmar el grano de `ingestion_audit` desde DDL, productor,
  consumidor y endpoint de health; documentar la discrepancia con E-03.
- [X] T002 Preservar precisión subsegundo en marcas temporales nuevas del
  productor y cubrir timestamp con y sin fracciones.

## Fase 2: Informe reproducible

- [X] T003 Crear informe de solo lectura para polls, caché histórica e índice
  Natural Earth con conteos, errores, hashes y tiempos disponibles.
- [X] T004 Cubrir agregaciones de polls, errores y precisión temporal con
  pruebas unitarias.
- [X] T005 Capturar una salida real y contrastar el histórico con PostgreSQL.

## Fase 3: Documentación y cierre

- [X] T006 Documentar procedimiento, limitaciones y auditoría de usuario
  separada en esta spec.
- [X] T007 Enlazar la spec desde el README y validar JSON, enlaces, pruebas y
  `git diff --check`.
