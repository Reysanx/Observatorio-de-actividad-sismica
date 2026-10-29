# CONSTITUCIÓN DEL PROYECTO: OBSERVATORIO DE ACTIVIDAD SÍSMICA

> **Metodología SDD (Spec-Driven Development) · GitHub Spec Kit**  
> **Ámbito:** Sistemas de Big Data · Consolidación Sesiones 1–8 · RA1  
> **Versión de la Constitución:** 1.0.0  
> **Estado:** Aprobado / Inmutable salvo enmienda explícita  

---

## 1. Misión y Propósito Fundamental

El **Observatorio de Actividad Sísmica** es un sistema de ingeniería de datos integral diseñado para responder con rigor y en tiempo cuasi-real a la pregunta:  
*«¿Dónde se está registrando actividad sísmica en el mundo y cómo se compara analíticamente con un periodo histórico equivalente?»*

El sistema no es un mero visor o proxy de la API de USGS. Debe demostrar un ciclo de vida completo de ingeniería de datos:
1. **Extracción automatizada y resiliente** de múltiples orígenes (feed live, histórico masivo y catálogo geoespacial).
2. **Evaluación y gobierno de calidad de datos** formal bajo 6 dimensiones.
3. **Integración espacial** punto-en-polígono contra cartografía oficial.
4. **Modelado dimensional e idempotente** con gestión de versiones y revisiones.
5. **Servicio y visualización analítica** desacoplada mediante API y SPA.
6. **Análisis crítico de complejidad computacional, rendimiento a escala y costes totales de propiedad (TCO)**.

---

## 2. Invariantes Arquitectónicos (Reglas No Negociables)

Toda implementación generada o modificada debe cumplir estrictamente con los siguientes mandatos:

### 2.1 Aislamiento en 5 Contenedores Docker Locales Obligatorios
El backend debe estar compuesto por exactamente **cinco servicios separados** orquestados mediante un único `compose.yaml`:
1. `productor`: Servicio Python (`aiokafka`) de extracción y publicación.
2. `broker`: Apache Kafka para transporte y retención de mensajes.
3. `consumidor`: Servicio Python (`aiokafka`, `shapely`/`geopandas`) para validación, enriquecimiento espacial y persistencia.
4. `almacenamiento`: PostgreSQL para datos preparados, histórico, cuarentena y estado persistente.
5. `api`: FastAPI para consulta analítica y exposición de datos.

*Mandato:* La ejecución conjunta debe realizarse mediante:
```bash
docker compose up --build -d
```
*Prohibición:* Queda terminantemente prohibido ejecutar productor, consumidor o API en el host fuera de Docker. Los cinco servicios son contenedores locales coordinados.

### 2.2 Política de Red y Seguridad Perimetral
- **Red interna Docker:** La comunicación entre productor, Kafka, consumidor, PostgreSQL y API se realiza mediante nombres de servicio DNS de Docker Compose (ej. `kafka:9092`, `postgres:5432`, `api:8000`).
- **Exposición exclusiva de API:** Únicamente el servicio `api` puede ser accesible desde el exterior mediante túnel seguro. Kafka y PostgreSQL **jamás** se exponen al túnel ni al exterior.
- **Acceso mediante Túnel HTTPS:** El acceso a la API se expone a través de **ngrok** mediante HTTPS. No se configuran certificados SSL/TLS dentro de FastAPI; ngrok gestiona la terminación TLS.
- **Frontend Desacoplado:** El panel (Angular + Leaflet) se despliega exclusivamente como SPA en **Netlify**, consumiendo la API a través de la URL HTTPS pública provista por ngrok.
- **Gestión de Secretos:** Prohibido subir tokens de ngrok, credenciales de base de datos o claves API a Git. Toda configuración sensible se gestiona con `.env` y `.env.example`.

### 2.3 Idempotencia y Procesamiento At-Least-Once
- El productor publica con garantía *at-least-once*, utilizando el `id` del terremoto de USGS como clave de particionado en Kafka.
- El consumidor debe ser estrictamente **idempotente**: el reenvío de un mensaje o el reinicio del consumidor no debe duplicar registros ni corromper agregaciones.
- La confirmación de offset en Kafka (`commit`) debe producirse **únicamente después** de que la transacción en PostgreSQL se haya consolidado exitosamente (`commit` en BD antes de `commit` en Kafka).
- Las actualizaciones de eventos revisados deben cumplir la condición temporal: solo se actualiza el estado actual si la versión recibida tiene un timestamp `updated` estrictamente más reciente que el almacenado.

### 2.4 Integridad de los Datos y Realidad Física
- **Prohibido rellenar nulos con ceros:** Un terremoto sin magnitud o sin profundidad no debe rellenarse arbitrariamente con 0. Las magnitudes negativas y profundidades negativas son fenómenos físicos reales y válidos en sismología; no deben ser descartadas sin análisis.
- **Categoría «Sin país asignado»:** Los terremotos marítimos o en zonas fuera de la simplificación de polígonos deben clasificarse explícitamente como «Sin país asignado». No deben imputarse al país más cercano ni considerarse errores.
- **Cuarentena estricta:** Registros con anomalías insalvables (ej. coordenadas inválidas no numéricas o fuera de rango WGS84) deben enviarse a una tabla de cuarentena con trazabilidad del motivo y copia del mensaje original.

### 2.5 Aislamiento de Reproducción Histórica (Replay)
- La demostración debe incluir un modo de **reproducción histórica acelerada** (`replay`).
- Los datos de reproducción deben transitar por un topic y/o tablas claramente segregadas del flujo en vivo (`live`), y la interfaz gráfica debe identificarlos de forma inequívoca con la etiqueta **«REPRODUCCIÓN»**.

---

## 3. Estándar Tecnológico y Límites de Alcance

### 3.1 Tecnologías Adoptadas
| Componente | Tecnología Seleccionada | Justificación / Restricción |
| :--- | :--- | :--- |
| **Lenguaje Backend** | Python 3.11+ | Ecosistema estándar para ingeniería de datos y ML/IA. |
| **Cliente Kafka** | `aiokafka` (asíncrono) | Máximo rendimiento y bajo consumo de recursos en I/O. |
| **Base de Datos** | PostgreSQL 16 | Motor relacional robusto con soporte JSONB e índices avanzados. |
| **Backend API** | FastAPI + Uvicorn | Rendimiento asíncrono, OpenAPI nativo y validación Pydantic. |
| **Geometría** | `shapely` / `geopandas` | Procesamiento espacial estándar WGS84 (EPSG:4326). |
| **Frontend** | Angular + Leaflet | SPA reactiva con renderizado cartográfico optimizado. |
| **Túnel** | ngrok | Proveedor HTTPS seguro efímero para demostración. |
| **Hosting SPA** | Netlify | CDN global optimizada para aplicaciones estáticas. |

### 3.2 Tecnologías Excluidas Explícitamente (Fuera de Alcance)
- **Apache Spark / Apache Flink:** Innecesarios para el volumen del reto; las ventanas y agregaciones se gestionan con SQL y Python.
- **Kubernetes / Clústeres Cloud:** No requeridos; el entorno objetivo es Docker Compose local reproducible.
- **Modelos de Aprendizaje Automático:** El alcance es de ingeniería de datos y análisis exploratorio; no se debe presentar este sistema como un modelo predictivo o de riesgo sísmico.

---

## 4. Estándar de Excelencia y Rúbrica de Evaluación (Objetivo: Sobresaliente 9–10)

El desarrollo del proyecto debe orientarse en todo momento a satisfacer el nivel **Sobresaliente (9–10)** de la rúbrica oficial RA1:

```
+------------------------------------------------------------------------------------------------------+
|                                 RÚBRICA DE EVALUACIÓN - RA1 (9–10)                                   |
+-------------------+----------------------------------------------------------------------------------+
| Criterio          | Evidencia Obligatoria para Nivel Sobresaliente                                   |
+-------------------+----------------------------------------------------------------------------------+
| 1. Extracción     | Pipeline automatizado de histórico (2025 particionado), feed live (60s) y        |
|                   | catálogo Natural Earth; análisis exhaustivo de tipos, unidades, límites y logs.  |
+-------------------+----------------------------------------------------------------------------------+
| 2. Calidad        | Análisis formal de 6 dimensiones (Completitud, Unicidad, Validez, Consistencia,   |
|                   | Actualidad, Exactitud), acciones de limpieza justificadas, cuarentena y notebook.|
+-------------------+----------------------------------------------------------------------------------+
| 3. Modelado       | Integración espacial punto-en-polígono, grano fino, claves primarias y foráneas, |
|                   | historial de versiones, idempotencia comprobada e índices optimizados.           |
+-------------------+----------------------------------------------------------------------------------+
| 4. Análisis       | Ventanas horarias UTC, distribuciones, comparación rigurosa con histórico 2025   |
|                   | (días con 0 eventos incluidos) y mínimo 3 conclusiones cuantitativas sólidas.    |
+-------------------+----------------------------------------------------------------------------------+
| 5. Reflexión      | Justificación Big-O (3 operaciones), benchmarks con 3 tamaños de datos, análisis |
|                   | de escalabilidad a 100M registros, auditoría TCO realista y mejoras futuras.    |
+-------------------+----------------------------------------------------------------------------------+
```

---

## 5. Protocolo de Modificación y Trabajo en Pareja

1. **Prioridad de la Especificación:** Ninguna línea de código debe escribirse sin que su comportamiento esté respaldado por las especificaciones de `specs/001-observatorio-sismico/`.
2. **Validación Automática:** Cada incremento debe validarse contra las 11 pruebas de aceptación recogidas en `acceptance-tests.md`.
3. **Registro de Decisiones (ADRs):** Cualquier desviación o decisión de diseño de impacto debe documentarse con sus alternativas y justificación técnica.
