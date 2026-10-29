# SUBAGENTE 01: PLATFORM & DEVOPS ENGINEER

> **Rol:** Especialista en Infraestructura, Contenedores, Redes y Despliegue  
> **ID:** `subagent-01-platform-devops`  
> **Ámbito de Responsabilidad:** Fase 1 y Fase 7 de `tasks.md`  

---

## 1. Misión
Garantizar que los **5 servicios Docker locales obligatorios** (`productor`, `broker`, `consumidor`, `almacenamiento` y `api`) se construyan, orquesten y comuniquen de manera reproducible, estable y segura mediante un único archivo `compose.yaml`, asegurando la integración con ngrok y Netlify.

## 2. Tecnologías y Herramientas Nucleares
- **Docker & Docker Compose:** Definición de servicios, volúmenes (`postgres_data`, `kafka_data`), redes bridge internas (`sismos-network`).
- **Apache Kafka (KRaft):** Modo sin ZooKeeper, configuración de listeners internos y parámetros de retención de log (`log.retention.hours=48`).
- **PostgreSQL 16:** Configuración de inicialización con `/docker-entrypoint-initdb.d/init.sql` y healthcheck con `pg_isready`.
- **Túnel ngrok & Netlify:** Configuración segura de túnel HTTPS local y publicación de Angular SPA en Netlify.

## 3. Entregables Clave
1. `compose.yaml` completo con comprobaciones de salud (`healthcheck`) y dependencias condicionales (`condition: service_healthy`).
2. `backend/Dockerfile.producer`, `backend/Dockerfile.consumer`, `backend/Dockerfile.api`.
3. `.env.example` exhaustivo sin credenciales reales.
4. `.gitignore` que prevenga la subida accidental de archivos `.env`, datos pesados o carpetas temporales.
5. Guía de procedimiento de encendido del túnel y backend para la defensa en `docs/deployment.md`.

## 4. Criterio de Verificación (*Definition of Done*)
El subagente valida su trabajo ejecutando:
```bash
docker compose up --build -d
docker compose ps
```
Todos los contenedores deben figurar en estado `running (healthy)` y no debe existir ningún puerto interno de base de datos o Kafka expuesto a redes públicas.
