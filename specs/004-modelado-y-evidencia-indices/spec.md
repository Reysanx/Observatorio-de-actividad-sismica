# Feature Specification: Modelado y evidencia de índices

**Feature ID**: `004-modelado-y-evidencia-indices`  
**Status**: Implemented  
**Scope**: Documentación del modelo y evidencia del esquema PostgreSQL existente; no modifica tablas, índices ni comportamiento de la aplicación.

## Contexto

El Criterio 3 de la rúbrica requiere modelos conceptual, lógico y físico, y el
entregable E-05 requiere diagramas, explicación del grano y justificación
técnica y empírica de los índices creados por `backend/db/init.sql`.

## Requisitos

- **FR-001**: Documentar un modelo conceptual Entidad-Relación y diferenciar
  las poblaciones live, histórica, replay y operativa.
- **FR-002**: Documentar la proyección lógica de análisis y el modelo relacional
  vigente, identificando explícitamente la categoría «Sin país asignado».
- **FR-003**: Explicar el grano y la clave de cada tabla lógica persistente,
  incluidas las claves compuestas y la unicidad de posiciones Kafka.
- **FR-004**: Vincular el modelo físico al DDL real y explicar particiones,
  restricciones e índices sin inventar entidades ni mejoras de rendimiento.
- **FR-005**: Entregar consultas SELECT reproducibles con `EXPLAIN ANALYZE` y
  la salida observada, indicando versión, escala del snapshot y limitaciones.
- **FR-006**: Mantener enlazados los artefactos desde la rúbrica, el plan
  principal y el índice general del proyecto.

## Criterios de aceptación

1. Los diagramas están versionados junto al feature y reflejan el esquema
   implementado en `backend/db/init.sql`.
2. Todas las tablas lógicas del esquema tienen una descripción de grano y su
   clave correspondiente.
3. Las consultas y la salida asociada se pueden localizar y reproducir desde
   `quickstart.md`.
4. Los planes muestran tanto índices elegidos como al menos un caso de
   escaneo secuencial; los planes no se presentan como aceleraciones
   universales.
5. La documentación deja claro que «Sin país asignado» no equivale por sí solo
   a un dato inválido y que las poblaciones no se mezclan.

