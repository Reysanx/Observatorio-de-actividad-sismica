# GUÍA DE DESPLIEGUE Y OPERACIÓN LOCAL
## Observatorio de Actividad Sísmica

Este documento contiene las instrucciones precisas paso a paso para levantar, verificar y operar el sistema completo en local (los 5 servicios Docker y la interfaz Angular).

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

El archivo `.env` ya se encuentra configurado en la raíz del proyecto. Si necesitas recrearlo, se basa en `.env.example`:

```powershell
Copy-Item .env.example .env
```

Parámetros clave de `.env`:
* `POSTGRES_DB=observatorio`
* `POSTGRES_USER=observatorio`
* `POSTGRES_PASSWORD=observatorio_local_dev_secret_2026`
* `API_PORT=8000`
* `USGS_POLL_INTERVAL_SECONDS=60`
* `LOG_LEVEL=INFO`

---

## 3. Levantar los 5 Servicios de Backend con Docker Compose

Abre una terminal PowerShell en la raíz del repositorio y ejecuta:

```powershell
# 1. Validar la configuración del compose
docker compose config

# 2. Construir y levantar los 5 contenedores en segundo plano
docker compose up --build -d

# 3. Comprobar que los 5 servicios están en estado 'healthy'
docker compose ps
```

### Servicios levantados:
| Contenedor | Rol | Puerto Local / Red |
| :--- | :--- | :--- |
| `broker` | Apache Kafka 3.7 (KRaft) | Interno (`broker:9092`) |
| `almacenamiento` | PostgreSQL 16.4 Alpine | Interno (`almacenamiento:5432`) |
| `productor` | Ingesta asíncrona de USGS cada 60s | Red interna `sismos-network` |
| `consumidor` | Calidad 6D, STRtree (Shapely) e idempotencia | Red interna `sismos-network` |
| `api` | FastAPI REST + asyncpg | Expuesto en `http://127.0.0.1:8000` |

> [!NOTE]
> Por seguridad y cumplimiento de la arquitectura, ni PostgreSQL ni Kafka exponen puertos al host exterior. Solo la API está publicada en el puerto 8000 del loopback local.

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
