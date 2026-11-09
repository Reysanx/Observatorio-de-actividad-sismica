# Despliegue reproducible con Netlify y ngrok

Guía para desplegar el frontend en Netlify y ejecutar el backend en un equipo Windows local, incluso al preparar un ordenador nuevo.

> **Alcance:** Netlify aloja únicamente la SPA Angular. Los cinco servicios de backend se ejecutan en Docker local. ngrok expone temporalmente la API por HTTPS; Kafka y PostgreSQL nunca se exponen. El equipo que ejecuta Docker debe permanecer encendido y conectado para que el sitio tenga datos.

## Requisitos

- Git for Windows, Docker Desktop con Compose v2 y conexión a Internet.
- Node.js 22 para ejecutar el frontend localmente o sus pruebas. Netlify compila con Node `22.12.0`.
- Acceso al repositorio GitHub, una cuenta Netlify y una cuenta ngrok.

## 1. Clonar y configurar el backend

Abre PowerShell y clona el repositorio:

```powershell
git clone https://github.com/Reysanx/Observatorio-de-actividad-s-smica.git
Set-Location Observatorio-de-actividad-s-smica
Copy-Item .env.example .env
```

Edita `.env`; cambia `POSTGRES_PASSWORD` por una contraseña local y configura `CORS_ORIGINS` con el origen exacto del sitio Netlify, sin barra final:

```text
POSTGRES_PASSWORD=<contraseña-local>
CORS_ORIGINS=http://localhost:4200,https://<nombre-del-sitio>.netlify.app
```

`.env` es local y está excluido de Git. No copies credenciales de otro dispositivo ni subas este archivo.

Con Docker Desktop abierto, desde la raíz del proyecto:

```powershell
docker compose config -q
docker compose up --build -d
docker compose ps
docker compose ps -a historical-bootstrap
```

Espera a que los cinco servicios permanentes (`productor`, `broker`, `consumidor`, `almacenamiento` y `api`) estén saludables y que `historical-bootstrap` termine correctamente. La primera descarga del catálogo USGS 2025 puede tardar. Si falla, consulta `docker compose logs historical-bootstrap`. Comprueba la API:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Si cambias `CORS_ORIGINS` después del primer arranque, aplica el cambio recreando la API:

```powershell
docker compose up -d --force-recreate api
```

## 2. Conectar Netlify con GitHub

En Netlify, crea un sitio desde GitHub y conecta `Reysanx/Observatorio-de-actividad-s-smica`. Autoriza el acceso al repositorio si se solicita. Netlify lee [netlify.toml](../netlify.toml), que configura:

- Base: `frontend`.
- Comando de build: `npm run build && npm run configure:netlify`.
- Directorio publicado: `dist/observatorio-sismico-frontend/browser`.
- Node.js: `22.12.0`.

Cuando Netlify asigne la URL de producción (`https://<nombre-del-sitio>.netlify.app`), añade ese origen a `CORS_ORIGINS` en `.env` y recrea la API como se indicó arriba. El origen debe coincidir exactamente, sin ruta ni barra final. No uses `*`. Para deploy previews, permite también cada origen preview exacto que necesites.

## 3. Instalar ngrok y abrir el túnel

Instala el agente de ngrok para Windows siguiendo la [guía oficial](https://ngrok.com/docs/share-localhost/quickstart/) o la [descarga oficial](https://download.ngrok.com/). En PowerShell:

```powershell
ngrok version
ngrok config add-authtoken <NGROK_AUTHTOKEN>
ngrok http 8000
```

El authtoken se configura una vez por dispositivo. No lo compartas ni lo guardes en el repositorio. Copia la URL HTTPS que muestra `ngrok http 8000` y deja esa terminal abierta mientras uses la aplicación. Esta es la URL pública de la API; no expongas Kafka ni PostgreSQL.

## 4. Configurar y desplegar el frontend

En Netlify abre **Project configuration → Environment variables** y agrega:

```text
Key:     NGROK_API_URL
Value:   https://<origen-https-mostrado-por-ngrok>
Scope:   Builds
Context: Production
```

Usa solo el origen HTTPS, sin `/api/v1`, ruta adicional ni barra final. Guarda la variable y ejecuta **Deploys → Trigger deploy**. El build genera el `config.json` del artefacto con ese endpoint. Si reinicias ngrok y cambia su URL, actualiza la variable y vuelve a desplegar.

El primer deploy fallará si se ejecuta antes de definir `NGROK_API_URL`; configura la variable y vuelve a lanzarlo.

## 5. Verificar el despliegue

1. Comprueba `https://<origen-https-de-ngrok>/api/v1/health`; debe devolver JSON de estado.
2. Abre el sitio de Netlify y confirma que carga el dashboard.
3. En el navegador (F12 → **Network**), verifica que las llamadas usan el dominio ngrok y llevan `ngrok-skip-browser-warning: true`.
4. Comprueba que las respuestas son JSON y no una página HTML de advertencia de ngrok.

La SPA añade automáticamente la cabecera `ngrok-skip-browser-warning` a las llamadas API para que ngrok no sustituya la respuesta con su página intermedia.

### Diagnóstico de CORS/ngrok

- En `.env`, `CORS_ORIGINS` debe incluir el origen exacto de Netlify, por ejemplo `https://<nombre>.netlify.app`, sin barra final. Después de editarlo, ejecuta `docker compose up -d --force-recreate api`.
- `NGROK_API_URL` debe ser la URL HTTPS actual del túnel. Si cambió, actualízala en Netlify y vuelve a desplegar.
- Si F12 muestra `200 OK` pero informa que falta `Access-Control-Allow-Origin`, revisa el tipo de contenido y el cuerpo de la respuesta. Si es HTML o la petición no tiene `ngrok-skip-browser-warning: true`, probablemente respondió la página intermedia de ngrok, no la API. Despliega la versión actual del frontend.
- Revisa los logs de la API con `docker compose logs --tail 100 api`.

## Detener y reiniciar

Para detener el túnel, usa `Ctrl+C` en su terminal. Para parar los contenedores sin borrar datos:

```powershell
docker compose down
```

Para volver a iniciar otro día, arranca Docker Desktop, ejecuta `docker compose up -d` desde la carpeta del proyecto y vuelve a abrir `ngrok http 8000`. Si la URL ngrok se mantiene, no necesitas redeplegar; si cambia, actualiza `NGROK_API_URL` y lanza un nuevo deploy de Netlify.

No uses `docker compose down --volumes` salvo que quieras eliminar deliberadamente la base de datos, el estado de Kafka y la caché histórica.

## Seguridad y alcance

El túnel hace que la API sea accesible desde Internet. CORS limita qué páginas pueden leer respuestas desde un navegador, pero no es autenticación ni bloquea clientes HTTP directos. Este despliegue está pensado para demostración/desarrollo; publica solo la API prevista y conserva Kafka y PostgreSQL en la red local. No uses esta configuración para datos o funciones que requieran control de acceso sin añadirlo primero.
