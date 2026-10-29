# Observatorio de Actividad Sísmica 🌍⚡

> **Sistemas de Big Data · Consolidación Sesiones 1–8 · Resultado de Aprendizaje 1 (RA1)**  
> **Metodología de Ingeniería:** Spec-Driven Development (SDD) basada en [GitHub Spec Kit](https://github.com/github/spec-kit)  
> **Objetivo de Calificación:** Sobresaliente (10/10)  

---

## 🧭 ¿Qué es este Proyecto?

El **Observatorio de Actividad Sísmica** es una plataforma integral de ingeniería y análisis de datos en tiempo cuasi-real. Su propósito es capturar de forma automatizada y desatendida los datos globales de terremotos, someterlos a control de calidad y enriquecimiento geoespacial, persistirlos de forma idempotente y ofrecer respuestas visuales y cuantitativas a la pregunta:

> **«¿Dónde se está registrando actividad sísmica en el mundo y cómo se compara con un periodo histórico equivalente?»**

---

## 🏛️ Estructura del Proyecto según SDD (GitHub Spec Kit)

Siguiendo la metodología **Spec-Driven Development (SDD)**, el proyecto se encuentra completamente desgranado, modelado y organizado en especificaciones modulares que actúan como la única fuente de verdad (*single source of truth*) antes y durante la implementación:

```text
Observatorio-de-actividad-s-smica/
├── .agents/                    # Arquitectura Multi-Agente (MAS), Roles y Skills operativas
│   ├── AGENTS.md               # Protocolo y jerarquía de orquestación padre-hijo
│   ├── rules/                  # Reglas de observancia obligatoria (arquitectura, calidad 6D)
│   ├── subagents/              # Definición de los 6 SubAgentes especialistas
│   └── skills/                 # Procedimientos técnicos ejecutables (runbooks)
│
├── .specify/
│   └── memory/
│       └── constitution.md     # Invariantes no negociables, principios de ingeniería y reglas arquitectónicas
│
├── specs/
│   └── 001-observatorio-sismico/
│       ├── spec.md             # Especificación funcional de producto, personas, casos de uso y requisitos (FR/NFR)
│       ├── plan.md             # Plan técnico de arquitectura (5 servicios Docker, Kafka, PostgreSQL, FastAPI, ngrok)
│       ├── data-spec.md        # Diccionario de datos, integración punto-en-polígono y marco de calidad 6D
│       ├── tasks.md            # Plan de trabajo granular en 8 fases y checklist de ejecución ordenado
│       ├── acceptance-tests.md # Matriz formal con las 11 pruebas de aceptación obligatorias y protocolo de replay
│       └── evaluation-rubric.md# Mapeo exhaustivo contra la rúbrica oficial RA1 y checklist de entregables (10/10)
│
├── Fuente_inicial.md           # Enunciado base y requisitos iniciales de la práctica (fuente histórica)
└── README.md                   # Índice general y guía de navegación del observatorio
```

---

## 📑 Índice de Navegación de Especificaciones

| Documento de Especificación | Propósito Principal | Enlace Directo |
| :--- | :--- | :--- |
| **Protocolo Multi-Agente (MAS)** | Jerarquía padre-hijo, catálogo de 6 SubAgentes especialistas y ciclo de traspaso. | [`.agents/AGENTS.md`](.agents/AGENTS.md) |
| **Constitución del Proyecto** | Principios inmutables, aislamiento de 5 servicios Docker, política de túneles y seguridad. | [`.specify/memory/constitution.md`](.specify/memory/constitution.md) |
| **Especificación Funcional** | Requisitos funcionales (FR-01 a FR-09), no funcionales (NFR), personas y reglas de negocio. | [`specs/001-observatorio-sismico/spec.md`](specs/001-observatorio-sismico/spec.md) |
| **Plan Técnico y Arquitectura** | Diagramas de flujo, configuración de Kafka KRaft, modelo físico PostgreSQL y DDL de índices. | [`specs/001-observatorio-sismico/plan.md`](specs/001-observatorio-sismico/plan.md) |
| **Especificación de Datos y Calidad** | Diccionario USGS, modelo espacial Natural Earth, «Sin país asignado» y matriz de calidad 6D. | [`specs/001-observatorio-sismico/data-spec.md`](specs/001-observatorio-sismico/data-spec.md) |
| **Desglose de Tareas** | Plan de ejecución en 8 fases lógicas con tareas atómicas, dependencias y criterios de verificación. | [`specs/001-observatorio-sismico/tasks.md`](specs/001-observatorio-sismico/tasks.md) |
| **Pruebas de Aceptación** | Protocolo de validación de los 11 escenarios oficiales de la Sección 11 (idempotencia, túnel, replay). | [`specs/001-observatorio-sismico/acceptance-tests.md`](specs/001-observatorio-sismico/acceptance-tests.md) |
| **Rúbrica de Evaluación y Entregables** | Mapeo detallado para garantizar Sobresaliente (9–10) en los 5 criterios de la sesión 8. | [`specs/001-observatorio-sismico/evaluation-rubric.md`](specs/001-observatorio-sismico/evaluation-rubric.md) |
| **Documento Fuente Original** | Texto original y requerimientos iniciales consolidados. | [`Fuente_inicial.md`](Fuente_inicial.md) |

---

## 🏗️ Resumen de la Arquitectura Obligatoria

```text
[ USGS Feed Live (60s) ] ---> [ Productor Python (aiokafka) ]
                                          |
                                          v
                               [ Broker Apache Kafka ]
                                          |
                                          v
                              [ Consumidor Python (STRtree) ]
                                          |
                 +------------------------+------------------------+
                 |                                                 |
                 v                                                 v
   [ PostgreSQL 16 (Persistencia) ]                    [ quarantine_events ]
                 ^
                 |
        [ API FastAPI ] <========== [ Túnel ngrok (HTTPS) ] <========== [ SPA Netlify (Angular + Leaflet) ]
```

- **5 Servicios Docker obligatorios en local:** `productor`, `broker` (Kafka), `consumidor`, `almacenamiento` (Postgres) y `api` (FastAPI).
- **Frontend SPA desacoplado:** Compilado y publicado en Netlify.
- **Conectividad segura:** Túnel HTTPS gestionado por ngrok hacia la API; Kafka y PostgreSQL jamás se exponen públicamente.

---

## 🚀 Próximos Pasos (Flujo de Trabajo SDD)

1. **Revisar y validar las especificaciones:** Confirmar que todos los requerimientos y decisiones técnicas descritas en `specs/001-observatorio-sismico/` se ajustan a las directrices esperadas.
2. **Iniciar la Fase 1 de Implementación:** Comenzar la ejecución secuencial del backlog de tareas según [`tasks.md`](specs/001-observatorio-sismico/tasks.md).
