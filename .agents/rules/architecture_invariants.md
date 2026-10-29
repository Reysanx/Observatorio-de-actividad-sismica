# REGLAS ARQUITECTÓNICAS E INVARIANTES OBLIGATORIOS

> **Ámbito:** Todos los agentes y submódulos del Observatorio de Actividad Sísmica.  
> **Prioridad:** Máxima / Violación Bloqueante.  

---

## 1. Regla de Contenedores y Servicios Separados
- **5 Servicios Aislados en Docker Compose:** El backend se compone única y exclusivamente de 5 contenedores orquestados mediante `compose.yaml`:
  1. `productor` (Python)
  2. `broker` (Kafka)
  3. `consumidor` (Python)
  4. `almacenamiento` (PostgreSQL)
  5. `api` (FastAPI)
- **Prohibido Ejecutar Servicios Locales Fuera de Docker:** Toda ejecución de productor, consumidor o API debe residir en su contenedor. La palabra «local» en el enunciado refiere a la máquina anfitriona del alumno, no a ejecución nativa en el host.
- **Comprobaciones de Salud Obligatorias:** Cada servicio debe disponer de directivas `healthcheck` y `depends_on: { condition: service_healthy }`. El orden de arranque no es suficiente para garantizar la conectividad de red.

## 2. Regla de Red y Seguridad Perimetral
- **Prohibido Exponer Kafka o PostgreSQL:** Los puertos de base de datos (`5432`) y broker (`9092`) **jamás** se exponen al túnel público ni a Internet.
- **Acceso Exclusivo mediante Túnel HTTPS:** La API FastAPI escucha internamente en `0.0.0.0:8000` y el acceso externo se canaliza únicamente a través de **ngrok**.
- **Frontend Desacoplado en Netlify:** La aplicación Angular debe consumirse como SPA independiente desde Netlify, conectándose a la API mediante la URL pública HTTPS provista por ngrok y leyendo `apiUrl` desde `config.json`.
- **Cero Secretos en Git:** Prohibido subir tokens de ngrok, contraseñas de PostgreSQL o archivos `.env` al repositorio. Se provee estrictamente `.env.example`.

## 3. Regla de Idempotencia y Procesamiento
- **At-Least-Once Delivery:** El productor publica con clave `event_id` y espera el ack del broker.
- **Commit Posterior a Persistencia:** El consumidor confirma el offset en Kafka (`commit()`) **única y exclusivamente tras confirmar la transacción SQL en PostgreSQL**.
- **Sentencia UPSERT con Validación Temporal:** Las revisiones recibidas solo actualizan el estado actual si `EXCLUDED.updated_utc > current_earthquakes.updated_utc`.
