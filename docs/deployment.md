# GUÍA DE DESPLIEGUE Y OPERACIÓN LOCAL
## Observatorio de Actividad Sísmica

Este documento contiene las instrucciones precisas paso a paso para levantar, verificar y operar el sistema en local: cinco servicios Docker permanentes, un inicializador histórico de una sola ejecución y la interfaz Angular.

Para preparar la publicación del frontend en Netlify y conectar desde otro equipo mediante ngrok, sigue la [guía reproducible Netlify/ngrok](deployment-netlify-ngrok.md).

---

## 1. Requisitos Previos

1. **Docker Desktop:**
   * Debe estar **abierto y en ejecución** con el motor Docker activo (icono de ballena verde en la barra de tareas de Windows).
   * Compatible con Docker Compose v2+.
2. **Node.js (v20 o superior):**
   * Necesario para ejecutar el servidor de desarrollo del frontend Angular en local (`http://localhost:4200`).
3. **Conexión a Internet:**
   * El servicio `productor` requiere salida HTTPS para consultar `https://earthquake.usgs.gov/`.

---

## 2. Preparación de la Configuración (.env)

El archivo `.env` es local y no se versiona. En una instalación nueva, créalo desde `.env.example`:

```powershell
Copy-Item .env.example .env
```

Edita `.env` y sustituye la contraseña de ejemplo por una contraseña local propia. No copies credenciales de otro equipo ni compartas el archivo. Parámetros clave:
* `POSTGRES_DB=observatorio`
* `POSTGRES_USER=observatorio`
* `POSTGRES_PASSWORD=<contraseña-local>`
* `API_PORT=8000`
* `CORS_ORIGINS=http://localhost:4200` (añade el origen exacto de Netlify para acceso remoto)
* `USGS_POLL_INTERVAL_SECONDS=60`
* `LOG_LEVEL=INFO`

---

## 3. Levantar el Backend con Docker Compose

Abre una terminal PowerShell en la raíz del repositorio y ejecuta:

```powershell
# 1. Validar la configuración del compose
docker compose config

# 2. Construir y levantar los servicios en segundo plano
docker compose up --build -d

# 3. Comprobar el estado de los servicios permanentes
docker compose ps

# 4. Consultar el inicializador (debe terminar con código 0)
docker compose ps -a historical-bootstrap
```

### Servicios levantados:
| Contenedor | Rol | Puerto Local / Red |
| :--- | :--- | :--- |
| `broker` | Apache Kafka 3.7 (KRaft) | Interno (`broker:9092`) |
| `almacenamiento` | PostgreSQL 16.4 Alpine | Interno (`almacenamiento:5432`) |
| `historical-bootstrap` | Descarga e importa el catálogo USGS 2025 una vez | Red interna `sismos-network` |
| `productor` | Ingesta asíncrona de USGS cada 60s | Red interna `sismos-network` |
| `consumidor` | Calidad 6D, STRtree (Shapely) e idempotencia | Red interna `sismos-network` |
| `api` | FastAPI REST + asyncpg | Expuesto en `http://127.0.0.1:8000` |

> [!NOTE]
> Por seguridad y cumplimiento de la arquitectura, ni PostgreSQL ni Kafka exponen puertos al host exterior. Solo la API está publicada en el puerto 8000 del loopback local.
> El inicializador histórico se ejecuta en segundo plano, sin bloquear la API ni el feed en vivo. Guarda el catálogo descargado en el volumen `usgs_cache` y registra en PostgreSQL que la importación terminó, así que los siguientes arranques no repiten la descarga ni la importación. Si USGS no está disponible, Docker reintenta el servicio hasta 5 veces; consulta `docker compose logs -f historical-bootstrap` para ver el estado.

La carga empieza automáticamente al ejecutar `docker compose up --build -d`. Puedes comprobar su estado y los datos importados con:

```powershell
docker compose ps -a historical-bootstrap
docker compose logs historical-bootstrap
docker compose exec almacenamiento psql -U observatorio -d observatorio -c "SELECT dataset_key, event_count, imported_at FROM dataset_imports;"
```

Si ejecutas `docker compose down --volumes`, se eliminan tanto la base de datos como la caché; el siguiente arranque descargará de nuevo el histórico. Si solo borras la base de datos pero conservas `usgs_cache`, la importación se repetirá usando la caché local.

---

## 4. Levantar la Interfaz Frontend (Angular + Leaflet)

En otra terminal PowerShell:

```powershell
# Iniciar el servidor local de desarrollo de Angular
npm start --prefix frontend
```

Una vez iniciado, abre tu navegador web en:
👉 **`http://localhost:4200`**

El frontend cargará automáticamente los datos desde `http://127.0.0.1:8000` leyendo el archivo `frontend/public/config.json`.

---

## 5. Ejecutar la Suite de Pruebas de Aceptación (11 Escenarios)

Con los contenedores activos, puedes verificar automáticamente los 11 escenarios de la rúbrica oficial (idempotencia, revisiones, magnitud nula ND, cuarentena, sismos oceánicos, etc.):

```powershell
docker compose exec -T api pytest tests/test_acceptance.py -v
```

Para correr la suite de pruebas unitarias del frontend:

```powershell
npm test --prefix frontend
```

---

## 6. Probar el Modo de Reproducción Histórica Acelerada (Replay)

Para simular una oleada de sismos controlados del año 2025 y observar el distintivo visual obligatorio **«REPRODUCCIÓN»** en el panel web:

```powershell
docker compose exec -T api python -m scripts.replay_producer
```

En la interfaz web (`http://localhost:4200`):
1. Pulsa en el conmutador superior sobre **«Reproducción»**.
2. Verás activarse el distintivo animado en rojo **«REPRODUCCIÓN»**, el banner explicativo con los eventos procesados/cuarentena y el mapa mostrando la simulación sin mezclar sus datos con el feed en vivo.

---

## 7. Inspección de Logs y Diagnóstico

Para consultar los logs de los servicios en tiempo real:

```powershell
# Ver el log del productor (consultas a USGS)
docker compose logs -f productor

# Ver el log del consumidor (enriquecimiento espacial y persistencia en PostgreSQL)
docker compose logs -f consumidor

# Ver el log de la API FastAPI
docker compose logs -f api
```

Comprobar el endpoint de salud de la API:
👉 `http://127.0.0.1:8000/api/v1/health`

---

## 8. Detener los Servicios

* **Detener sin perder datos:**
  ```powershell
  docker compose down
  ```
* **Reiniciar limpiando completamente los volúmenes de datos (reset de base de datos y Kafka):**
  ```powershell
  docker compose down --volumes
  ```
