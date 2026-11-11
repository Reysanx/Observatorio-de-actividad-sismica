# Implementation Plan: Métricas Reproducibles de Calidad 6D

**Branch**: `main` (se conserva la rama actual; no se crea una rama nueva) | **Date**: 2026-11-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-metricas-calidad-6d/spec.md`

## Summary

Entregar un análisis 6D reproducible basado en la caché histórica USGS 2025 y los registros correspondientes de PostgreSQL, incorporando el estado anterior (Feature de entrada disponible) y posterior (campos canónicos persistidos) solo para la misma población trazable. El procedimiento genera resultados con numeradores, denominadores, reglas, procedencia e identidad de datos; la memoria de calidad enlaza el informe y retira afirmaciones antiguas no reproducibles. Cada dimensión tendrá una entrada y podrá contener varias submétricas (por campo, regla, latencia o estadístico) para no colapsar resultados con denominadores distintos. La caché ya aplica filtros y deduplicación, por lo que las conclusiones no se extenderán al feed USGS bruto no conservado: las etapas anteriores a caché se marcarán no verificables si no hay auditoría. Cada transformación observable se informará con etapa, afectados, denominador, evidencia y política de solapamiento; las etapas sin trazabilidad se marcarán no verificables. Los recuentos live disponibles de aceptados, excluidos y cuarentenados se reportarán como población separada y solo se reconciliarán si la auditoría cubre todas las etapas. La exactitud absoluta no se afirmará: solo se medirán fidelidad de transformación y concordancia espacial como proxies limitados.

## Technical Context

**Language/Version**: Python 3.11+ (runtime backend actual).

**Primary Dependencies**: Python standard library, `asyncpg` y PostgreSQL existentes; pytest para las pruebas. No se prevén nuevas dependencias.

**Storage**: Caché mensual GeoJSON USGS 2025 con manifest y hash; lectura de `historical_2025`, `ingestion_audit`, `current_earthquakes` y, para contexto separado, tablas de cuarentena/versiones. Sin cambios de esquema previstos.

**Testing**: Pytest unitario para fórmulas, denominadores, límites y clasificación de proxies; prueba de integración de solo lectura contra el esquema PostgreSQL del proyecto; reproducción del informe y comparación de resultados deterministas.

**Target Platform**: Contenedores Docker Compose locales existentes; el informe y la memoria quedan versionados en el repositorio.

**Project Type**: Pipeline de datos con memoria de calidad y reporte analítico reproducible; sin cambios de API ni de interfaz.

**Performance Goals**: Procesar el conjunto histórico importado (del orden de decenas de miles de registros) en una ejecución local sin requerir recursos o servicios adicionales.

**Constraints**: No modificar el flujo live/replay ni su esquema. Las consultas son de solo lectura. No rellenar nulos, no invalidar automáticamente magnitudes/profundidades negativas, y no tratar «Sin país asignado» como error. Separar registros sintéticos y live de la población histórica. No inventar población anterior ni referencia de verdad independiente.

**Scale/Scope**: Un extracto histórico USGS 2025 M≥4 de doce particiones mensuales y una instantánea observacional de auditoría/live para actualidad y disposiciones operativas; seis dimensiones con una entrada cada una y submétricas por población, antes/después cuando exista una entrada comparable, además de recuentos por transformación con etapas no verificables y solapamientos declarados. Las categorías de disposición live no se agregan ni se usan para inferir etapas históricas no auditadas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación |
|---|---|
| Cinco servicios Docker y límites de red | PASS. Se reutilizan servicios/contenedores existentes; no se añade servicio ni se expone una interfaz nueva. |
| Idempotencia y transacciones del consumidor | PASS. La evaluación lee datos y no altera offsets, mensajes ni transacciones. |
| Integridad y realidad física | PASS. Se preservan nulos legítimos y magnitudes/profundidades negativas; los eventos no asignados a polígonos permanecen como «Sin país asignado». |
| Cuarentena y trazabilidad | PASS. Se reportan únicamente motivos/recuentos observables en poblaciones auditadas; se explicita cualquier falta de cobertura entre entrada, exclusión y cuarentena sin atribuirla al histórico. |
| Aislamiento live/replay | PASS. Replay y datos sintéticos no se mezclan en la población histórica; cualquier estadística live se rotula como una población aparte. |
| Alcance sin verdad de referencia | PASS. No se declara exactitud geofísica; proxies de fidelidad/concordancia llevan población y limitaciones explícitas. |

No se identifican violaciones constitucionales ni se requiere excepción.

## Project Structure

### Documentation (this feature)

```text
specs/003-metricas-calidad-6d/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── quality-report.schema.json       # Six dimensions, nested submetrics, transformation counts
└── tasks.md              # Se crea en la fase /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── scripts/
│   └── quality_report.py              # Generación determinista en modo solo lectura
├── tests/
│   └── test_quality_report.py         # Fórmulas, casos frontera y esquema de salida
└── consumer/
    └── quality.py                     # Reglas actuales evaluadas; solo cambiar si se demuestra necesario

docs/
├── memoria_calidad.md                 # Método, resultados, límites y enlaces a evidencia
└── evidence/
    └── data-quality/
        ├── quality-report.json        # Salida versionada de una ejecución identificada
        └── README.md                  # Población, procedencia e instrucciones de regeneración
```

**Structure Decision**: Mantener la feature en el backend Python ya existente y en la memoria de calidad. La generación se ejecutará dentro de un contenedor existente con acceso de lectura a caché/BD; los datos de evidencia se guardarán en el repositorio mediante salida controlada del comando. No se crea un notebook ni se instala Jupyter, porque la memoria y un reporte JSON reproducible satisfacen la rúbrica con menos dependencias y mejor automatización.

## Phase 0: Research

Decisiones de fuente, comparabilidad, medidas y límites documentadas en [research.md](./research.md). No quedan decisiones técnicas bloqueantes ni marcadores `NEEDS CLARIFICATION`.

## Phase 1: Design

- Entidades del reporte y reglas de denominador documentadas en [data-model.md](./data-model.md).
- Contrato de salida automatizable documentado en [contracts/quality-report.schema.json](./contracts/quality-report.schema.json).
- Escenarios de reproducción y validación documentados en [quickstart.md](./quickstart.md).
- No se definen contratos de API: esta feature no amplía interfaces externas del servicio.

## Constitution Check (post-design)

PASS. El diseño mantiene la evaluación de solo lectura, no altera los cinco servicios ni sus límites, y distingue poblaciones históricas, live, replay y sintéticas. La identidad del extracto y las limitaciones acompañan resultados; exactitud absoluta permanece no verificable sin referencia independiente. No hay migraciones, nuevas dependencias ni excepciones constitucionales previstas.

## Complexity Tracking

No aplica: no hay violaciones constitucionales que justificar.
