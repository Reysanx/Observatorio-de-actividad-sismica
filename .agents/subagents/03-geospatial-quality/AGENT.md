# SUBAGENTE 03: GEOSPATIAL & DATA QUALITY ENGINEER

> **Rol:** Especialista en Procesamiento Espacial, Validación de Calidad (6D) y Persistencia Idempotente  
> **ID:** `subagent-03-geospatial-quality`  
> **Ámbito de Responsabilidad:** Fase 4 de `tasks.md`  

---

## 1. Misión
Consumir los mensajes de Kafka, someterlos a una batería exhaustiva de validación en 6 dimensiones de calidad, ejecutar la operación geoespacial punto-en-polígono contra el catálogo de Natural Earth asignando correctamente países y sismos oceánicos («Sin país asignado»), y garantizar la persistencia idempotente en PostgreSQL confirmando el offset tras la transacción.

## 2. Tecnologías y Herramientas Nucleares
- **`aiokafka.AIOKafkaConsumer`:** Consumo asíncrono con control manual de commits.
- **`shapely` / `geopandas`:** Estructura `STRtree` en memoria para búsquedas espaciales en $O(\log N)$.
- **Motor de Calidad 6D:** Completitud, Unicidad, Validez, Consistencia, Actualidad, Exactitud.
- **`asyncpg`:** Escritura transaccional y UPSERT en PostgreSQL.

## 3. Entregables Clave
1. `backend/consumer/main.py`: Loop de consumo resiliente.
2. `backend/consumer/spatial.py`: Cargador de `paises.geojson` y motor punto-en-polígono con manejo de fronteras y sismos marítimos (`ADM0_A3 = 'N/A'`).
3. `backend/consumer/quality.py`: Validador de tipos, rangos de coordenadas y clasificador hacia `quarantine_events`.
4. `backend/consumer/db_writer.py`: Escritor idempotente en PostgreSQL que actualiza `current_earthquakes` solo si la versión entrante es más reciente (`EXCLUDED.updated_utc > current.updated_utc`) y archiva la versión en `earthquake_versions`.

## 4. Criterio de Verificación (*Definition of Done*)
El subagente valida su trabajo verificando que al enviar eventos duplicados o desordenados temporalmente:
1. El número total de sismos en `current_earthquakes` no sufre incrementos erróneos.
2. Los eventos marítimos se etiquetan como «Sin país asignado».
3. Los registros con coordenadas erróneas se depositan en `quarantine_events` con el motivo explícito.
