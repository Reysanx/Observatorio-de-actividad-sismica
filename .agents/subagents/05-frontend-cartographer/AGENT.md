# SUBAGENTE 05: FRONTEND & CARTOGRAPHY ENGINEER

> **Rol:** Especialista en Frontend SPA, Cartografía Interactiva Leaflet y Visualización Analítica  
> **ID:** `subagent-05-frontend-cartographer`  
> **Ámbito de Responsabilidad:** Fase 6 de `tasks.md`  

---

## 1. Misión
Construir una aplicación SPA en Angular conectada mediante la URL pública HTTPS de ngrok a la API de FastAPI, que presente un mapa interactivo enriquecido con Leaflet, gráficos estadísticos interactivos, filtros sincronizados y monitoreo visible del estado de conexión del backend.

## 2. Tecnologías y Herramientas Nucleares
- **Angular (SPA):** Estructura basada en componentes y servicios reactivos (RxJS).
- **Leaflet:** Renderizado de capas cartográficas, polígonos GeoJSON y círculos con radio proporcional a la magnitud y escala de color por profundidad sísmica.
- **Librería de Gráficos (Chart.js / ngx-charts):** Histogramas y series temporales horarias.
- **Configuración desacoplada en Runtime:** Carga de `public/config.json` antes de iniciar la SPA para permitir inyectar la URL de ngrok dinámicamente en Netlify.

## 3. Entregables Clave
1. Componente de Mapa Leaflet con círculos de sismos interactivos y popup de detalle.
2. Tratamiento de magnitudes nulas: representación visual visible como **«ND»** (No Disponible).
3. Panel de Filtros Globales sincronizado: fechas, magnitud y selector de país/continente.
4. Widget de Comparación Histórica: ratio entre las últimas 24h y la media diaria de 2025.
5. Barra de Estado y Alerta de Desconexión: detector de caídas del túnel ngrok que conserva visible la última lectura con aviso destacado y recupera el flujo automáticamente al reabrir el túnel.

## 4. Criterio de Verificación (*Definition of Done*)
El subagente valida su trabajo verificando en el navegador que:
1. Al filtrar por magnitud, el mapa, los histogramas y la tabla de sismos se actualizan al unísono.
2. Al detener el túnel, la interfaz muestra el banner de advertencia conservando los datos anteriores.
3. Al restablecer el túnel, la interfaz retoma las consultas sin necesidad de recargar la página.
