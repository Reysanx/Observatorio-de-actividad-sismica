# PROTOCOLO DE ORQUESTACIÓN MULTI-AGENTE (MAS)
## Observatorio de Actividad Sísmica · Big Data & IA (RA1)

Este documento define la arquitectura y el protocolo de colaboración del **Sistema Multi-Agente (MAS)** que gobernará la implementación integral del proyecto para asegurar el cumplimiento del 100% de la rúbrica oficial (Objetivo: **Sobresaliente 9–10**).

---

## 1. Topología del Sistema Multi-Agente

```mermaid
flowchart TD
    Orquestador["Agente Padre: Orquestador Principal\n(Control de Flujo, Dependencias y Rúbrica)"]

    subgraph Especialistas ["SubAgentes Especialistas por Dominio"]
        A1["SubAgente 01: Platform & DevOps\n(Docker, Kafka, PostgreSQL, Redes, ngrok, Netlify)"]
        A2["SubAgente 02: Data Ingestion\n(USGS Live, Histórico 2025, aiokafka, Deduplicación)"]
        A3["SubAgente 03: Geospatial & Quality\n(Shapely STRtree, Motor 6D, Cuarentena, Idempotencia)"]
        A4["SubAgente 04: Backend & Data Modeling\n(Esquema Relacional, FastAPI, Consultas Analíticas, asyncpg)"]
        A5["SubAgente 05: Frontend & Cartography\n(Angular, Leaflet, Histogramas, Filtros, Monitor de Túnel)"]
        A6["SubAgente 06: Academic & Quality Auditor\n(11 Pruebas de Aceptación, Replay, Big-O, Benchmarks, TCO)"]
    end

    Orquestador -->|Asigna Fase 1 y Despliegue| A1
    Orquestador -->|Asigna Fase 2 y 3 (Streaming)| A2
    Orquestador -->|Asigna Fase 4 (Transformación)| A3
    Orquestador -->|Asigna Fase 5 (API y DB)| A4
    Orquestador -->|Asigna Fase 6 (Dashboard)| A5
    Orquestador -->|Asigna Fase 7 y 8 (Validación y Memoria)| A6

    A1 -.->|Infraestructura lista| A2
    A2 -.->|Mensajes en Kafka| A3
    A3 -.->|Datos enriquecidos en Postgres| A4
    A4 -.->|Endpoints REST activos| A5
    A5 -.->|Sistema integrado| A6
    A6 -.->|Evidencias verificadas 10/10| Orquestador
```

---

## 2. Roles y Catálogo de SubAgentes

| ID | Nombre del SubAgente | Directorio de Especificación | Responsabilidad Principal |
| :---: | :--- | :--- | :--- |
| **A-00** | **Agente Orquestador (Padre)** | `.agents/AGENTS.md` | Supervisión del backlog (`tasks.md`), control de dependencias, auditoría contra la Constitución y coordinación entre subagentes. |
| **A-01** | **Platform & DevOps** | `.agents/subagents/01-platform-devops/` | `compose.yaml`, 5 servicios Docker, políticas de salud, persistencia de volúmenes, KRaft, ngrok y Netlify. |
| **A-02** | **Data Ingestion** | `.agents/subagents/02-data-ingestion/` | Productor Python asíncrono, descargas de `all_day.geojson`, particionado mensual de 2025, backoff ante fallos de USGS. |
| **A-03** | **Geospatial & Quality** | `.agents/subagents/03-geospatial-quality/` | Consumidor asíncrono, árbol espacial `STRtree` con `paises.geojson`, «Sin país asignado», motor de calidad 6D y cuarentena. |
| **A-04** | **Backend & Modeling** | `.agents/subagents/04-backend-modeler/` | Modelos relacionales, DDL `init.sql`, optimización de índices B-Tree, servidor FastAPI, pool `asyncpg` y endpoints analíticos. |
| **A-05** | **Frontend Cartographer** | `.agents/subagents/05-frontend-cartographer/` | Aplicación Angular, mapas Leaflet reactivos, series 1h UTC, histogramas, widget comparativo y alertas de estado de túnel. |
| **A-06** | **Academic Auditor** | `.agents/subagents/06-academic-auditor/` | Suite de 11 pruebas de aceptación, modo `replay` histórico, cálculos Big-O, mediciones experimentales de memoria/tiempo y TCO. |

---

## 3. Protocolo de Ejecución y Traspaso

1. **Activación de Rol:** Al abordar una tarea de `tasks.md`, el Orquestador explicita qué SubAgente toma el control y consulta sus directivas en `subagents/<id>/AGENT.md` y sus Skills asociadas.
2. **Alineación con la Constitución:** Ningún subagente puede violar los invariantes de `.specify/memory/constitution.md` (ej. no ejecutar servicios fuera de Docker, no omitir 'Sin país asignado', no rellenar nulos con 0).
3. **Criterio de Finalización (*Definition of Done*):** Una tarea solo se marca como completada `[x]` cuando el subagente ejecuta el comando de verificación estipulado en la especificación y aporta evidencia verificable.
