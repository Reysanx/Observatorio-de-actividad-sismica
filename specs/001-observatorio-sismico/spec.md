# ESPECIFICACIÓN FUNCIONAL: OBSERVATORIO DE ACTIVIDAD SÍSMICA

> **Feature ID:** `001-observatorio-sismico`  
> **Fase:** Especificación de Requisitos de Producto y Dominio (`spec.md`)  
> **Origen del documento:** Desglose y formalización de [`Fuente_inicial.md`](../../Fuente_inicial.md)  
> **Estado:** Aprobado / Especificación Oficial  

---

## 1. Resumen Ejecutivo y Planteamiento del Reto

El **Observatorio de Actividad Sísmica** tiene por objetivo capturar datos globales de terremotos de forma desatendida, limpiarlos, someterlos a control de calidad riguroso, enriquecerlos con información geopolítica mediante operaciones geoespaciales y almacenarlos de forma idempotente para responder a:
> **¿Dónde se está registrando actividad sísmica y cómo se compara con un periodo histórico equivalente?**

El producto final consta de un pipeline continuo de datos que alimenta una interfaz web accesible globalmente con cartografía interactiva, distribuciones estadísticas, agregaciones por ventanas temporales y contraste contra la serie histórica de 2025.

---

## 2. Personas y Escenarios de Uso

### 2.1 Persona 1: Analista de Datos Sísmicos (Elena)
- **Objetivo:** Analizar tendencias de sismicidad global y evaluar anomalías de frecuencia y profundidad.
- **Escenario:** Elena accede al panel, filtra por magnitud $\ge 4.5$ y subregión «América del Sur». Comprueba el histograma de profundidades, revisa la serie temporal por horas UTC y compara el volumen de las últimas 24 horas frente a la media diaria histórica de 2025 para comprobar si la actividad actual está dentro de los rangos normales.

### 2.2 Persona 2: Usuario General / Ciudadano (Carlos)
- **Objetivo:** Consultar la actividad sísmica reciente tras la noticia de un temblor.
- **Escenario:** Carlos abre la URL en Netlify desde su navegador. Observa el mapa con círculos proporcionales a la magnitud y coloreados por profundidad sísmica. Hace clic sobre un sismo frente a la costa y observa su ficha detallada: magnitud, profundidad en km, hora UTC del sismo, retraso de ingesta y país asignado («Sin país asignado» por ser marítimo).

### 2.3 Persona 3: Evaluador Técnico / Auditor de Calidad (Profesor / Auditor)
- **Objetivo:** Verificar la robustez del sistema, la calidad de datos y la tolerancia a fallos.
- **Escenario:** 
  1. El evaluador corta el túnel ngrok: el panel de Angular debe mostrar inmediatamente un estado de pérdida de conexión y mantener visible la última lectura con sello de tiempo.
  2. Vuelve a encender el túnel: la interfaz se reconecta de manera autónoma sin refrescar la página.
  3. Ejecuta la **Reproducción Histórica** (`replay`): el pipeline procesa eventos de 2025 a alta velocidad sin mezclar datos con el feed en vivo, etiquetando el panel como «REPRODUCCIÓN».
  4. Inspecciona la base de datos para comprobar que los reenvíos de mensajes no han alterado los recuentos (idempotencia demostrada).

---

## 3. Requisitos Funcionales (FR)

### FR-01: Extracción Continua de Feed Reciente (Live Stream)
- **Descripción:** El sistema debe consultar el feed GeoJSON de USGS cada 60 segundos de forma programada:
  `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson`
- **Comportamiento:**
  - Descarga la ventana móvil de las últimas 24 horas (HTTP GET).
  - Almacena el GeoJSON en crudo con metadatos de extracción (`ingested_at`, `source`, `http_status`, `content_hash`).
  - Extrae los campos esenciales: `id`, `properties.time`, `properties.updated`, `properties.mag`, `properties.magType`, `properties.type`, `properties.place`, `geometry.coordinates`.
  - Filtra estrictamente `properties.type == "earthquake"`. Si el tipo es distinto (ej. *quarry blast*, *explosion*), se excluye y se registra el motivo de exclusión.

### FR-02: Extracción y Cacheo del Catálogo Histórico
- **Descripción:** El sistema debe disponer de una carga histórica completa del año 2025 para terremotos de magnitud $\ge 4.0$ a nivel mundial.
- **Comportamiento:**
  - Consulta la API del catálogo de USGS (`fdsnws/event/1/query`).
  - Divide la descarga en bloques mensuales (enero a diciembre de 2025) para no rebasar el límite de 20.000 eventos por petición de USGS.
  - Implementa subdivisión recursiva si algún intervalo mensual llegase a aproximarse al límite de 20.000.
  - Deduplica eventos compartidos en las fronteras de los intervalos temporales.
  - Almacena el histórico en disco local/volumen persistente para su reutilización sin peticiones reiteradas a la API externa.

### FR-03: Integración Espacial con Catálogo de Países (Natural Earth)
- **Descripción:** Cada evento sísmico debe integrarse con el catálogo cartográfico `frontend/public/datos/paises.geojson`.
- **Comportamiento:**
  - Utiliza el sistema de coordenadas geográficas estándar **WGS84 (EPSG:4326)**.
  - Realiza una operación espacial geométrica de **Punto en Polígono** (Point-in-Polygon).
  - Enlaza los atributos: `ADM0_A3` (código de país), `NAME_ES` (nombre en español), `ADMIN`, `CONTINENT` y `SUBREGION`.
  - Queda prohibido deducir el país parseando la cadena de texto de `properties.place`.
  - Si el punto cae en el océano, fuera de las fronteras cartografiadas o en zonas simplificadas, asigna el valor literal **«Sin país asignado»** y `ADM0_A3 = "N/A"`.
  - Si un punto cae en una frontera compartida, aplica una regla documentada y determinista (ej. orden alfabético de `ADM0_A3`).

### FR-04: Gestión de Versiones y Revisiones Sísmicas
- **Descripción:** La fuente USGS revisa continuamente eventos pasados (actualizando magnitud, epicentro o profundidad). El sistema debe gestionar estas revisiones correctamente.
- **Comportamiento:**
  - Una revisión se identifica cuando llega un evento con el mismo `id` pero un `properties.updated` mayor.
  - El sistema actualiza la tabla de «Estado Actual» con los nuevos valores.
  - Se registra la versión anterior en la tabla de «Historial de Versiones» para trazabilidad y auditoría.
  - Si llega una versión antigua con timestamp `updated` menor o igual al ya registrado, **no** sobrescribe el estado actual.

### FR-05: Reglas de Calidad y Cuarentena de Datos
- **Descripción:** Cada registro procesado se evalúa bajo un motor de calidad con reglas explícitas.
- **Comportamiento:**
  - **Validez de coordenadas:** Longitud $\in [-180, 180]$, Latitud $\in [-90, 90]$, Profundidad finita en km. Valores fuera de rango $\rightarrow$ Cuarentena.
  - **Magnitudes nulas:** Se admiten magnitudes vacías/nulas si el cálculo está pendiente en USGS. Se almacenan como `NULL` en base de datos y se representan como «ND» (No Disponible) en la interfaz. Queda prohibido sustituirlas por 0.
  - **Magnitudes negativas / Profundidades negativas:** Se validan y aceptan tras verificación física (en sismología existen magnitudes negativas para sismos microscópicos y profundidades negativas sobre el nivel del mar).
  - **Tabla de cuarentena:** Almacena eventos insalvables con timestamp, motivo del rechazo y carga útil JSON cruda.

### FR-06: Idempotencia en Transporte e Ingesta
- **Descripción:** La ingesta debe garantizar que la recepción repetida de un mismo mensaje no altere el recuento de sismos ni los agregados.
- **Comportamiento:**
  - Se utiliza `id` del terremoto como clave de mensaje en Kafka.
  - Escritura en PostgreSQL mediante sentencia `INSERT ... ON CONFLICT (event_id) DO UPDATE ...`.
  - El commit del offset en Kafka se realiza única y exclusivamente tras el commit exitoso en PostgreSQL.

### FR-07: API REST de Consultas Analíticas (FastAPI)
- **Descripción:** Exposición de endpoints REST bajo contrato formal para alimentar el panel interactivo.
- **Comportamiento:**
  - `GET /api/v1/health`: Estado de los servicios, última consulta y último terremoto ingerido.
  - `GET /api/v1/earthquakes`: Listado filtrable de sismos con paginación, filtros de fecha, magnitud, profundidad y país/subregión.
  - `GET /api/v1/stats/geo`: Recuento y agregados de magnitud agrupados por país y subregión (incluyendo «Sin país asignado»).
  - `GET /api/v1/stats/hourly`: Agregaciones en ventanas fijas de 1 hora UTC basadas en el tiempo del evento (`time`).
  - `GET /api/v1/stats/distributions`: Distribución de magnitudes (bins de 0.5) y profundidades (bins de 20 km).
  - `GET /api/v1/stats/historical-comparison`: Comparación del periodo reciente (últimas 24h, mag $\ge 4$) frente a la media diaria del histórico 2025 bajo los mismos filtros.
  - Habilitación de CORS para el dominio Netlify y local, y soporte de la cabecera `ngrok-skip-browser-warning`.

### FR-08: Panel de Control e Interfaz Cartográfica (Angular + Leaflet)
- **Descripción:** SPA interactiva que representa la sismicidad global y sus análisis.
- **Comportamiento:**
  - **Mapa interactivo:** Capa base cartográfica, polígonos de países, círculos de terremotos (radio proporcional a la magnitud, escala de color por profundidad sísmica: verde $<30$ km, amarillo $30-70$ km, naranja $70-300$ km, rojo $>300$ km).
  - **Ficha de detalle:** Al hacer clic en un sismo, muestra magnitud, profundidad, hora UTC, país asignado y latencia de ingesta.
  - **Filtros sincronizados:** Filtros por rango de fechas, magnitud mínima/máxima y selector de país/continente que actualizan simultáneamente el mapa, los gráficos y las tablas.
  - **Gráficos analíticos:** Histogramas de magnitud/profundidad y series temporales horarias.
  - **Comparación histórica:** Tarjeta destacada con el ratio sismos 24h vs. media diaria 2025.
  - **Monitoreo de estado:** Indicador visual de salud de la API, hora de última ingesta y alerta destacada si se pierde la conexión.
  - **Tabla alternativa:** Vista en tabla de datos consultable con ordenación y búsqueda.

### FR-09: Modo de Reproducción Histórica Acelerada (Replay)
- **Descripción:** Capacidad de simular una secuencia histórica acelerada para propósitos de demostración técnica y pruebas.
- **Comportamiento:**
  - Ingesta un subconjunto ordenado temporalmente del año 2025 a través de Kafka en un topic dedicado (`earthquakes-replay`) o marcado con `mode="replay"`.
  - El panel muestra de forma destacada el cartel **«REPRODUCCIÓN»**.
  - Incluye casos de prueba controlados: duplicados artificiales, revisiones de magnitud y sismos marítimos.

---

## 4. Requisitos No Funcionales (NFR)

### NFR-01: Rendimiento y Latencia
- El tiempo de respuesta de los endpoints de la API FastAPI debe ser inferior a 250 ms para consultas agregadas sobre el estado actual.
- El ciclo de extracción y publicación del productor debe completarse en menos de 5 segundos por cada lote de 24 horas (~150–300 sismos).

### NFR-02: Disponibilidad y Tolerancia a Fallos
- Los servicios deben incorporar directivas de reinicio `restart: unless-stopped`.
- Implementación de `healthchecks` en Docker Compose para PostgreSQL y Kafka, de modo que el consumidor y la API esperen a que la infraestructura esté verdaderamente lista.
- Resiliencia ante caídas temporales de USGS: reintentos con *exponential backoff* y registro de fallos en auditoría sin corromper el estado anterior.

### NFR-03: Seguridad y Confidencialidad
- PostgreSQL y Kafka no exponen puertos fuera de la red de Docker.
- La API atiende exclusivamente solicitudes seguras mediante túnel HTTPS ngrok.
- Prohibida la inclusión de credenciales, tokens o secretos en el repositorio Git.

### NFR-04: Portabilidad y Reproducibilidad
- El despliegue completo del backend debe ser reproducible en cualquier máquina con Docker y Docker Compose mediante `docker compose up --build -d`.
- Dependencias de Python fijadas con precisión (`requirements.txt` o `Pipfile.lock` / `poetry.lock`).

---

## 5. Reglas de Negocio e Invariantes de Dominio

1. **Definición de Terremoto:** Solo los registros con `properties.type == 'earthquake'` forman parte del modelo oficial. Explosiones mineras, erupciones volcánicas o ensayos militares se descartan o se etiquetan en cuarentena.
2. **Normalización Temporal UTC:** Todo cálculo y almacenamiento de fechas debe realizarse en UTC. El tiempo de ocurrencia (`time`) y el de revisión (`updated`) de USGS (en milisegundos Unix epoch) deben convertirse a `TIMESTAMP WITH TIME ZONE`.
3. **Cálculo de la Media Diaria Histórica:**
   $$\text{Media Diaria 2025} = \frac{\text{Total de sismos válidos en 2025 con mag } \ge 4.0}{365}$$
   *Nota crítica:* No deben omitirse del denominador los días con 0 eventos.
4. **Independencia del Backend:** El productor y el consumidor continúan ejecutándose y actualizando la base de datos de manera ininterrumpida, independientemente de si hay usuarios en el panel de Angular.
