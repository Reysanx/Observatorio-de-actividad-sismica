# Despliegue del frontend con Netlify y ngrok

La aplicación mantiene los cinco servicios de backend en Docker Compose local. Netlify publica solamente la SPA Angular; ngrok proporciona HTTPS hacia la API local. Kafka y PostgreSQL no se publican.

## Requisitos

- Docker Desktop y Docker Compose funcionando con la API disponible en `http://127.0.0.1:8000`.
- Una cuenta/sitio Netlify conectado al repositorio.
- Una cuenta ngrok y el agente instalado en el equipo que ejecuta Docker Compose.
- La URL HTTPS de ngrok que usarás para la API. Reutiliza el dominio de desarrollo asignado a tu cuenta si permanece estable; si la URL cambia, actualiza la variable de Netlify y vuelve a desplegar.

## 1. Crear el sitio en Netlify

Conecta el repositorio a Netlify y deja que tome la configuración de [netlify.toml](../netlify.toml). Puedes crear el sitio antes de tener la URL de ngrok, pero define `NGROK_API_URL` antes de que termine el primer build; si el build automático comienza antes, fallará con un error claro y podrás reintentarlo después de configurar la variable. La configuración fija:

- Directorio base: `frontend`.
- Comando de build: `npm run build && npm run configure:netlify`.
- Directorio publicado: `dist/observatorio-sismico-frontend/browser`.
- Node.js: `22.12.0`.

En las variables de entorno de Netlify, para el contexto **Production**, define la URL HTTPS de la API. Puedes volver a Deploy settings después de que Netlify asigne el dominio del sitio:

```text
NGROK_API_URL=https://<dominio-estable>.ngrok.app
```

Debe ser el origen HTTPS de ngrok, sin `/api/v1`, ruta adicional, parámetros ni credenciales. No es un secreto. El build escribe esa dirección en `config.json` dentro del artefacto publicado; el valor local de `frontend/public/config.json` no se modifica. Los deploy previews requieren que su origen Netlify también esté permitido por CORS en el backend.

## 2. Permitir el origen de Netlify en la API

Tras conocer el dominio de producción del sitio, agrega su origen exacto a `.env` (archivo local ignorado por Git), separado por comas de los orígenes que necesites:

```text
CORS_ORIGINS=http://localhost:4200,https://<nombre-del-sitio>.netlify.app
```

`CORS_ORIGINS` contiene el **origen de la página Netlify**, no la URL de ngrok. No uses `*`. Para permitir un deploy preview, agrega también el origen exacto de ese preview.

Aplica el cambio recreando únicamente la API:

```powershell
docker compose up -d --force-recreate api
docker compose ps api
```

Comprueba que la API local responde antes de abrir el túnel:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

## 3. Abrir el túnel ngrok

Instala el agente de ngrok para Windows desde su [guía oficial](https://ngrok.com/docs/share-localhost/quickstart/) o la [descarga oficial](https://download.ngrok.com/). Abre PowerShell y comprueba la instalación:

```powershell
ngrok version
```

En el [dashboard de ngrok](https://dashboard.ngrok.com/get-started/your-authtoken), copia el authtoken y configúralo una sola vez (no guardes el token en el repositorio ni lo compartas):

```powershell
ngrok config add-authtoken <NGROK_AUTHTOKEN>
```

Inicia el túnel hacia el puerto de la API:

```powershell
ngrok http 8000
```

Usa el origen HTTPS que ngrok muestra como `NGROK_API_URL` en Netlify. ngrok ofrece un dominio de desarrollo asignado a la cuenta; si se mantiene igual al reiniciar el agente, puedes reutilizarlo. Si la URL cambia, actualiza la variable de Netlify y vuelve a desplegar. Mantén esta terminal abierta mientras uses la SPA. No reenvíes puertos de Kafka, PostgreSQL ni otros servicios.

## 4. Publicar y comprobar

Guarda `NGROK_API_URL` en Netlify y ejecuta un nuevo deploy de producción. Abre el sitio publicado y verifica:

1. `https://<dominio-estable>.ngrok.app/api/v1/health` responde correctamente.
2. En las herramientas de desarrollo del navegador, las llamadas API se dirigen a ese origen y no a `127.0.0.1`.
3. Las llamadas no fallan por CORS y el dashboard actualiza datos.
4. El sitio funciona con `https://`; no uses una URL HTTP para el backend.

Si la URL de ngrok cambia, actualiza `NGROK_API_URL` y vuelve a desplegar Netlify. Detener ngrok interrumpe temporalmente las llamadas remotas, pero no detiene la API ni los servicios Compose.

## Consideraciones de exposición

El túnel hace que la API sea accesible desde Internet. CORS limita qué páginas pueden leer respuestas desde un navegador, pero no es autenticación ni bloquea clientes HTTP directos. Expón solamente la API prevista, conserva los puertos de Kafka y PostgreSQL en la red local y no uses esta configuración para publicar datos o funciones que requieran control de acceso sin añadirlo primero.
