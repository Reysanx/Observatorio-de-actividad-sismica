---
name: benchmarking-tco
description: >-
  Procedimiento para realizar el análisis de complejidad algorítmica Big-O, ejecutar mediciones
  empíricas de tiempo y memoria en 3 tamaños de lote, proyectar a 100M y auditar costes TCO.
---

# Procedimiento de Benchmarking, Complejidad Big-O y Cálculo de TCO

Esta habilidad guía la generación de las evidencias de ingeniería requeridas para el criterio de «Reflexión» (Sobresaliente 9–10).

## 1. Análisis Teórico Big-O (3 Operaciones Nucleares)
1. **Búsqueda e inserción de versiones por ID:**
   - Estructura: B-Tree sobre `(event_id, updated_utc)` en PostgreSQL y HashMap en el deduplicador del productor.
   - Complejidad: Caso medio $O(\log N)$ o $O(1)$; peor caso $O(\log N)$.
2. **Integración espacial Punto-en-Polígono:**
   - Estructura: `STRtree` (R-Tree en memoria).
   - Complejidad: Búsqueda de candidatos en árbol espacial $O(\log M)$ donde $M$ es el número de polígonos ($\approx 250$ países).
3. **Agregación por ventanas temporales horarias:**
   - Estructura: Escaneo de índice B-Tree index-only scan sobre `time_utc`.
   - Complejidad: $O(K + \log N)$ donde $K$ es el número de eventos en la ventana.

## 2. Protocolo de Medición Experimental (3 Tamaños de Datos)
- **Tamaño Pequeño:** 500 registros (feed habitual de 24-48 horas).
- **Tamaño Medio:** 10.000 registros (~1 mes completo de sismos globales $M \ge 4$).
- **Tamaño Grande:** 100.000 registros (simulación sintética extrapolada).
- Registrar:
  - Tiempo de CPU (milisegundos) usando `time.perf_counter()`.
  - Consumo de memoria RAM (MB) usando `memory_profiler` o `tracemalloc`.
  - Comparativa con y sin índices en base de datos (`EXPLAIN ANALYZE`).

## 3. Proyección a Escala Masiva (100 Millones de Sismos)
- Razonar los límites de almacenamiento (aprox. 50 GB de datos y 25 GB de índices).
- Proponer particionado horizontal nativo de PostgreSQL por rango temporal (`PARTITION BY RANGE (time_utc)` mensual o anual).
- Estrategia de compactación y retención en frío (*cold storage* en Parquet/S3).

## 4. Auditoría de Costes Totales de Propiedad (TCO)
- **Hardware y Energía:** Servidor local vs instancia VPS/Cloud equivalente (ej. AWS t3.large, consumo 45W, coste de kWh).
- **Almacenamiento y Red:** Transferencia saliente de la API y peticiones al feed de USGS.
- **Coste Humano:** Horas de desarrollo, mantenimiento preventivo y monitorización.
- *Nota crítica:* Demostrar que una capa gratuita en la nube no equivale a coste cero en producción.
