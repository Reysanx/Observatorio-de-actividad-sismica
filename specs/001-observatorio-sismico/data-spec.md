# ESPECIFICACIÓN DE DATOS, CALIDAD E INTEGRACIÓN ESPACIAL

> **Feature ID:** `001-observatorio-sismico`  
> **Fase:** Especificación de Datos, Contratos y Calidad (`data-spec.md`)  
> **Origen del documento:** Formalización de Secciones 4, 6 y 7 de [`Fuente_inicial.md`](../../Fuente_inicial.md)  
> **Estado:** Aprobado / Contrato de Datos  

---

## 1. Catálogo y Diccionario de Fuentes Externas

### 1.1 Fuente 1: USGS Live Feed (Ventana Móvil 24 Horas)
- **Endpoint:** `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson`
- **Frecuencia y Modo:** HTTP GET cada 60 segundos (Pull continuo).
- **Semántica:** Ventana móvil de los eventos ocurridos o actualizados en las últimas 24 horas respecto al momento de la petición. No es el día natural ni un canal push con websockets. Cada llamada descarga el estado completo de la ventana actual (~150 a 300 eventos).

#### Diccionario de Datos del GeoJSON Feature de USGS
| Campo Origen (JSON Path) | Tipo Origen | Tipo Destino PostgreSQL | Unidad / Formato | Nulable | Descripción y Regla de Negocio |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `id` | `string` | `VARCHAR(32)` | Alfanumérico (ej. `us7000m9xz`) | No | Identificador único universal de USGS. Clave primaria y clave de mensaje en Kafka. |
| `geometry.coordinates[0]` | `float` | `DOUBLE PRECISION` | Grados decimales $[-180, 180]$ | No | Longitud geográfica en datum WGS84. |
| `geometry.coordinates[1]` | `float` | `DOUBLE PRECISION` | Grados decimales $[-90, 90]$ | No | Latitud geográfica en datum WGS84. |
| `geometry.coordinates[2]` | `float` | `DOUBLE PRECISION` | Kilómetros (km) | No | Profundidad del hipocentro. **Puede ser negativa** (eventos sobre el nivel del mar). |
| `properties.mag` | `float` | `REAL` | Escala sísmica (ej. Richter/Mw) | **Sí** | Magnitud del sismo. Puede ser `null` si está en cálculo o negativa. Prohibido rellenar con 0. |
| `properties.magType` | `string` | `VARCHAR(16)` | Código (ej. `mww`, `ml`, `mb`) | Sí | Método/escala empleada para estimar la magnitud. |
| `properties.time` | `integer` (int64) | `TIMESTAMPTZ` | Milisegundos Unix Epoch | No | Momento exacto de ocurrencia del sismo en tiempo UTC. |
| `properties.updated` | `integer` (int64) | `TIMESTAMPTZ` | Milisegundos Unix Epoch | No | Última fecha/hora en que USGS recalculó o validó los datos del sismo. |
| `properties.place` | `string` | `TEXT` | Texto descriptivo | Sí | Descripción humana aproximada (ej. `12 km SSW of Guánica, Puerto Rico`). |
| `properties.type` | `string` | `VARCHAR(32)` | Código de evento | No | Tipo de evento. **Regla de filtro:** Solo se admite `"earthquake"`. |

#### Gestión de Eventos Excluidos por Tipo
USGS incluye eventos no sísmicos naturales en el feed. El productor debe evaluar `properties.type`:
- Si `properties.type != 'earthquake'` (ej. `quarry blast`, `explosion`, `ice quake`, `sonic boom`):
  - Se descarta de la ingesta en el estado actual.
  - Se registra en la tabla `quarantine_events` o en el log de auditoría con `failure_reason = 'EXCLUDED_TYPE: ' || properties.type` para garantizar trazabilidad sin polucionar el modelo analítico.

---

### 1.2 Fuente 2: Catálogo Histórico USGS (Año Completo 2025)
- **Endpoint Base:** `https://earthquake.usgs.gov/fdsnws/event/1/query`
- **Filtros Mandatarios:**
  - `format=geojson`
  - `starttime=2025-01-01T00:00:00Z`
  - `endtime=2026-01-01T00:00:00Z`
  - `minmagnitude=4.0`
  - `eventtype=earthquake`
  - `orderby=time-asc`

#### Estrategia de Particionado y Deduplicación Histórica
1. **Límite de API de USGS:** La API rechaza o trunca silenciosamente consultas que devuelvan más de 20.000 registros.
2. **Partición Mensual:** Se programan 12 peticiones secuenciales:
   - Mes 1: `2025-01-01T00:00:00Z` a `2025-02-01T00:00:00Z`
   - ...
   - Mes 12: `2025-12-01T00:00:00Z` a `2026-01-01T00:00:00Z`
3. **Subdivisión Recursiva:** Si un mes supera los 18.000 registros, el script debe dividir automáticamente el mes en quincenas.
4. **Deduplicación de Fronteras:** Al usar `endtime` igual al `starttime` del mes siguiente, los eventos exactamente en la frontera podrían duplicarse. El pipeline de carga histórica aplica un `DISTINCT ON (event_id)` antes de persistir en `historical_2025`.
5. **Carga Única y Reutilización:** Los archivos descargados se guardan localmente en `data/historical/2025_mXX.geojson` y se cargan a la base de datos en el paso de inicialización.

---

### 1.3 Fuente 3: Catálogo Geográfico Natural Earth
- **Ubicación del archivo:** `frontend/public/datos/paises.geojson`
- **Formato:** GeoJSON estándar con geometrías de tipo `Polygon` y `MultiPolygon`.
- **Datum y Proyección:** Coordenadas geográficas WGS84 (EPSG:4326).

#### Atributos Clave del Catálogo
| Atributo GeoJSON | Tipo | Descripción | Regla de Validación |
| :--- | :--- | :--- | :--- |
| `ADM0_A3` | `string` (3 chars) | Identificador alfanumérico del país | Comprobar unicidad. No asumir que todos son códigos ISO 3166-1 alpha-3 oficiales (contiene códigos internos de Natural Earth como `-99` o `SOL`). |
| `NAME_ES` | `string` | Nombre del país en español | Nombre preferente para visualizaciones y tarjetas. |
| `ADMIN` | `string` | Nombre formal administrativo | Nombre de respaldo si `NAME_ES` estuviese ausente. |
| `CONTINENT` | `string` | Continente geopolítico | Para filtros jerárquicos. |
| `SUBREGION` | `string` | Subregión geopolítica | Para agregaciones analíticas intermedias (ej. `South America`, `Southern Europe`). |

---

## 2. Especificación de la Integración Geoespacial (Punto en Polígono)

```
        Terremoto (Lon, Lat)
               x  [-71.25, -29.80]
              / \
             /   \  Operación Espacial: STRtree (Shapely)
            v     v
   +-----------------------------+-----------------------------+
   | ¿Cae dentro de un Polígono? | ¿Cae en el Océano o Costas? |
   +-----------------------------+-----------------------------+
   | SÍ: Asignar atributos:       | NO: Asignar categoría:      |
   |   - ADM0_A3 = "CHL"         |   - ADM0_A3 = "N/A"         |
   |   - PAIS = "Chile"          |   - PAIS = "Sin país        |
   |   - SUBREGION = "S. America"|            asignado"        |
   +-----------------------------+-----------------------------+
```

### Reglas Algorítmicas de Asociación Geográfica
1. **Punto en Polígono Estricto:** La coordenada `Point(geom_lon, geom_lat)` se contrasta contra los polígonos de `paises.geojson`.
2. **Tratamiento de Terremotos Marítimos:** Los sismos en dorsales oceánicas, zonas de subducción en mar abierto o islas no cartografiadas en la escala simplificada **no** pertenecen a ningún polígono de país.
   - **Regla:** Asignar `adm0_a3 = 'N/A'` y `country_name = 'Sin país asignado'`.
   - **Prohibición:** Queda terminantemente prohibido atribuir el sismo al país más próximo por proximidad euclídea o extraer el país del campo de texto descriptivo `properties.place`.
3. **Puntos en Fronteras Compartidas:** Si un punto cae exactamente sobre la arista límite entre dos polígonos adyacentes o si la tolerancia geométrica detecta múltiple intersección, se selecciona la entidad con el código `ADM0_A3` menor en orden lexicográfico.

---

## 3. Marco de Evaluación y Aseguramiento de Calidad (6 Dimensiones)

Para alcanzar el nivel **Sobresaliente** de la rúbrica oficial, el consumidor y la auditoría deben verificar y registrar cuantitativamente las siguientes 6 dimensiones:

```
+------------------------------------------------------------------------------------------------------+
|                                   MATRIZ DE CALIDAD DE DATOS (6D)                                    |
+-------------------+------------------------------------------+---------------------------------------+
| Dimensión         | Verificación y Regla                     | Acción ante Incumplimiento            |
+-------------------+------------------------------------------+---------------------------------------+
| 1. Completitud    | Porcentaje de valores no nulos en:       | Si mag es null: conservar NULL y      |
|                   | id, time, updated, coords, mag, place.   | rotular 'ND'. Si id/coords es null:   |
|                   |                                          | enviar a cuarentena.                  |
+-------------------+------------------------------------------+---------------------------------------+
| 2. Unicidad       | No duplicidad de event_id en el estado   | El consumidor descarta versiones      |
|                   | actual y unicidad de (event_id, updated) | idénticas ya procesadas mediante      |
|                   | en el historial de revisiones.           | UPSERT idempotente.                   |
+-------------------+------------------------------------------+---------------------------------------+
| 3. Validez        | Coordenadas finitas y en rango:          | Registros no válidos se insertan en   |
|                   | lon in [-180, 180], lat in [-90, 90].    | quarantine_events con el motivo       |
|                   | time_utc <= updated_utc. Fechas válidas. | detallado.                            |
+-------------------+------------------------------------------+---------------------------------------+
| 4. Consistencia   | Clave foránea adm0_a3 referenciada en    | Coherencia de unidades (profundidad   |
|                   | dim_countries (o 'N/A').                 | en km siempre). Secuencia temporal    |
|                   | Coherencia de la escala de magnitud.     | monótona en revisiones.               |
+-------------------+------------------------------------------+---------------------------------------+
| 5. Actualidad     | Latencia observada:                      | Se calcula Delta t_pub y Delta t_pipe.|
|                   | Delta_pub = updated - time.              | La API expone 'last_ingested_at' y    |
|                   | Delta_pipe = now() - updated.            | alerta si antigüedad > 10 minutos.    |
+-------------------+------------------------------------------+---------------------------------------+
| 6. Exactitud      | Contraste y límites conocidos de USGS:   | Se documenta en la memoria la escala  |
|                   | soluciones automáticas preliminares vs.  | simplificada de Natural Earth y los   |
|                   | soluciones revisadas por sismólogos.     | márgenes de error de localización.    |
+-------------------+------------------------------------------+---------------------------------------+
```

---

## 4. Estructura y Esquema de la Tabla de Cuarentena

Cuando un evento no puede ser procesado debido a una violación crítica de integridad o validez física, se aísla en la tabla `quarantine_events`:

```sql
CREATE TABLE IF NOT EXISTS quarantine_events (
    quarantine_id BIGSERIAL PRIMARY KEY,
    source_event_id VARCHAR(64),
    failure_reason VARCHAR(128) NOT NULL,
    raw_payload JSONB NOT NULL,
    quarantined_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Catálogo de Códigos de Falla (`failure_reason`):
1. `INVALID_COORDINATES_OUT_OF_BOUNDS`: Longitud o latitud fuera de rango $[-180, 180] \times [-90, 90]$.
2. `NON_FINITE_COORDINATES`: Valores `NaN`, `null` o `Infinity` en las coordenadas espaciales.
3. `EXCLUDED_EVENT_TYPE`: Evento con `properties.type != 'earthquake'`.
4. `CORRUPT_JSON_SYNTAX`: Error de deserialización en la carga útil recibida de Kafka.
5. `MISSING_MANDATORY_IDENTIFIER`: Falta del campo `id` de USGS.
