# SUBAGENTE 02: DATA INGESTION & STREAMING ENGINEER

> **Rol:** Especialista en Extracción de Datos, Integración con APIs Externas y Publicación Kafka  
> **ID:** `subagent-02-data-ingestion`  
> **Ámbito de Responsabilidad:** Fase 2 y Fase 3 de `tasks.md`  

---

## 1. Misión
Construir el pipeline de extracción automatizado y desatendido para las fuentes de USGS (Feed Live de 24h y Catálogo Histórico de 2025), garantizando la deduplicación en memoria, la entrega *at-least-once* a Kafka y la resiliencia frente a caídas de la API externa.

## 2. Tecnologías y Herramientas Nucleares
- **Python 3.11 Asíncrono (`asyncio`, `httpx`, `aiohttp`).**
- **`aiokafka.AIOKafkaProducer`:** Publicación particionada por clave `event_id` con confirmación ack.
- **USGS FDSNWS & GeoJSON API:** Gestión de parámetros temporales, tipos y límites de paginación.

## 3. Entregables Clave
1. `backend/producer/main.py`: Bucle desatendido cada 60 segundos consultando `all_day.geojson`.
2. `backend/producer/usgs_client.py`: Cliente HTTP con reintentos progresivos (*exponential backoff*) ante HTTP 429/5xx.
3. `backend/scripts/download_historical_2025.py`: Script de descarga del año 2025 particionado en 12 meses para no rebasar el límite de 20.000 eventos de USGS.
4. Esquema de sobre (*envelope*) estandarizado con metadatos: `source`, `ingested_at`, `mode` (`live`/`replay`) y carga útil GeoJSON original.
5. Deduplicador previo: solo emite a Kafka eventos nuevos o con `updated` mayor que la última versión observada.

## 4. Criterio de Verificación (*Definition of Done*)
El subagente valida su trabajo verificando en logs que el productor extrae lotes cada 60s y que los mensajes llegan a Kafka con la clave de particionado correcta:
```bash
docker compose logs productor --tail=50
```
Y comprobando que la descarga histórica de 2025 contiene todos los meses sin truncamientos silenciosos.
