---
name: usgs-ingestion
description: >-
  Procedimiento técnico para descargar, particionar mensualmente y validar el feed
  en tiempo real de 24h y el catálogo histórico de 2025 de USGS sin rebasar límites.
---

# Procedimiento de Ingesta USGS (Feed Live e Histórico 2025)

Esta habilidad guía la descarga resiliente y automatizada de las fuentes oficiales de sismicidad de USGS.

## 1. Feed en Vivo (24 Horas Móvil)
- **Endpoint:** `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson`
- **Frecuencia:** Cada 60 segundos mediante cliente asíncrono `httpx`.
- **Regla de Filtrado:** Descartar si `properties.type != "earthquake"` registrando el motivo en auditoría.
- **Empaquetado:** Adjuntar metadatos de ingesta (`source`, `ingested_at`, `mode="live"`, `content_hash`).

## 2. Catálogo Histórico (Año Completo 2025)
- **Endpoint:** `https://earthquake.usgs.gov/fdsnws/event/1/query`
- **Límite de API:** USGS impone un máximo de 20.000 eventos por petición.
- **Particionamiento Mensual Obligatorio:**
  Realizar 12 consultas secuenciales con parámetros:
  `format=geojson&starttime=2025-MM-01T00:00:00Z&endtime=2025-(MM+1)-01T00:00:00Z&minmagnitude=4.0&eventtype=earthquake&orderby=time-asc`
- **Subdivisión Recursiva:** Si una respuesta mensual supera los 18.000 registros, dividir en intervalos quincenales.
- **Deduplicación de Fronteras:** Al solaparse el fin de mes con el inicio del siguiente, ejecutar deduplicación por `event_id`.
- **Almacenamiento Local:** Guardar las respuestas en `data/historical/2025_mXX.geojson` para no reiterar llamadas.
