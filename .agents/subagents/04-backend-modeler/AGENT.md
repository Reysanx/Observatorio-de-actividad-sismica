# SUBAGENTE 04: BACKEND & DATA MODELING ENGINEER

> **Rol:** Especialista en Modelado Relacional/Dimensional, Optimización de Índices y Desarrollo de API REST  
> **ID:** `subagent-04-backend-modeler`  
> **Ámbito de Responsabilidad:** Fase 5 y modelado DDL de Fase 1 en `tasks.md`  

---

## 1. Misión
Diseñar el esquema de base de datos relacional/dimensional óptimo en PostgreSQL, definir índices B-Tree específicos para acelerar agregaciones temporales y geoespaciales, y desarrollar la API REST asíncrona con FastAPI bajo un contrato formal estricto para alimentar el frontend de Angular.

## 2. Tecnologías y Herramientas Nucleares
- **PostgreSQL 16:** Tablas de hechos y dimensiones, tipos `TIMESTAMPTZ`, `JSONB`, claves primarias y restricciones de integridad.
- **FastAPI + Uvicorn:** Arquitectura asíncrona, validación de esquemas con Pydantic y documentación interactiva Swagger/OpenAPI.
- **`asyncpg`:** Pool de conexiones asíncrono de alto rendimiento.
- **CORS Middleware:** Gestión de orígenes cruzados para Netlify y soporte para `ngrok-skip-browser-warning`.

## 3. Entregables Clave
1. `backend/db/init.sql`: DDL completo de tablas e índices (`idx_current_earthquakes_time`, `idx_current_earthquakes_mag`, `idx_current_earthquakes_adm0`, etc.).
2. `backend/api/main.py`: Punto de entrada de FastAPI y configuración de middleware CORS.
3. Endpoints analíticos:
   - `GET /api/v1/health`: Estado de conectividad y última ingesta.
   - `GET /api/v1/earthquakes`: Listado filtrable de sismos con paginación.
   - `GET /api/v1/stats/geo`: Recuentos y métricas por país/subregión (incluyendo «Sin país asignado»).
   - `GET /api/v1/stats/hourly`: Ventanas fijas de 1 hora UTC basadas en el tiempo del sismo.
   - `GET /api/v1/stats/distributions`: Histogramas de magnitud y profundidad sísmica.
   - `GET /api/v1/stats/historical-comparison`: Comparación entre las últimas 24h ($\text{mag} \ge 4.0$) y la media diaria anual de 2025 (incluyendo días con 0 eventos en el denominador de 365 días).

## 4. Criterio de Verificación (*Definition of Done*)
El subagente valida su trabajo comprobando que todos los endpoints responden en menos de 250 ms y satisfacen el contrato formal:
```bash
curl -H "ngrok-skip-browser-warning: true" http://127.0.0.1:8000/api/v1/health
curl -H "ngrok-skip-browser-warning: true" http://127.0.0.1:8000/api/v1/stats/historical-comparison
```
