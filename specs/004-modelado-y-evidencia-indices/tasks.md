# Tasks: Modelado y evidencia de índices

**Input**: [spec.md](./spec.md)  
**Plan**: [plan.md](./plan.md)

## Phase 1: Modelado y documentación

- [X] T001 Documentar los modelos conceptual, lógico y físico, el grano de
  cada tabla y las claves en `data-model.md`.
- [X] T002 Contrastar el inventario de índices con el DDL vigente de
  `backend/db/init.sql` y describir las limitaciones de los planes observados
  en `data-model.md`.

## Phase 2: Evidencia reproducible

- [X] T003 Añadir consultas de solo lectura y planes observados en
  `evidence/database-indexes/explain-analyze.sql` y
  `evidence/database-indexes/explain-analyze.txt`.
- [X] T004 Documentar requisitos y pasos de reproducción en `quickstart.md`.

## Phase 3: Integración y validación

- [X] T005 Enlazar la documentación desde la rúbrica, el plan principal y
  `README.md`.
- [X] T006 Ejecutar el script de evidencia en PostgreSQL Compose y comprobar
  `git diff --check`.

