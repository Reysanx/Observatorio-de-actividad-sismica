# Implementation Plan: Modelado y evidencia de índices

**Branch**: `main` (sin crear una rama nueva)  
**Spec**: [spec.md](./spec.md)

## Resumen

Organizar el entregable E-05 como un feature autocontenido bajo
`specs/004-modelado-y-evidencia-indices/`. El feature contiene modelos
conceptual y lógico, explicación del grano, inventario del modelo físico,
consultas reproducibles de PostgreSQL y salidas observadas. No se realizan
cambios de aplicación ni de esquema.

## Decisiones y límites

- PostgreSQL 16 y el DDL existente de `backend/db/init.sql` son la fuente del
  modelo físico.
- El modelo analítico se describe como una constelación lógica; no se crea un
  esquema estrella ni tablas dimensionales nuevas.
- Los planes se obtienen con `EXPLAIN (ANALYZE, BUFFERS)` sobre consultas de
  solo lectura. Las mediciones corresponden a un snapshot local y pueden
  cambiar con los datos, estadísticas, caché y hardware.
- Los índices se justifican según filtros y planes observados. No se cambia ni
  elimina ningún índice a partir de una prueba de escala pequeña.
- Evidencia y comandos se almacenan dentro del directorio del feature.

## Estructura

```text
specs/004-modelado-y-evidencia-indices/
├── spec.md
├── plan.md
├── data-model.md
├── quickstart.md
├── tasks.md
└── evidence/
    └── database-indexes/
        ├── explain-analyze.sql
        └── explain-analyze.txt
```

La comprobación se limita a verificar los enlaces, que el script SQL se
ejecute contra el servicio PostgreSQL Compose y que la salida contenga los
planes esperados. No hay suites de código asociadas a esta feature
documental.

