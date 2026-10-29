# RÚBRICA DE EVALUACIÓN Y GUÍA DE ENTREGABLES (OBJETIVO: 10/10 SOBRESALIENTE)

> **Feature ID:** `001-observatorio-sismico`  
> **Fase:** Alineación de Rúbrica y Entregables (`evaluation-rubric.md`)  
> **Origen del documento:** Secciones 12 y 13 de [`Fuente_inicial.md`](../../Fuente_inicial.md)  
> **Estado:** Aprobado / Estándar de Máxima Calificación  

---

## 1. Alineación Exhaustiva con la Rúbrica Oficial (Sesión 8 · RA1)

Para garantizar la calificación máxima (**Sobresaliente 9–10**) en la evaluación académica, el proyecto debe aportar evidencias específicas e inobjetables en los 5 criterios evaluados:

```
+------------------------------------------------------------------------------------------------------------------+
|                                    MATRIZ DE EVIDENCIAS PARA SOBRESALIENTE (9–10)                                |
+------------------+-----------------------+-----------------------------------------------------------------------+
| Criterio         | Nivel Sobresaliente   | Evidencias Concretas Obligatorias en este Proyecto                    |
+------------------+-----------------------+-----------------------------------------------------------------------+
| 1. Extracción    | Carga + análisis      | - Pipeline automatizado para las 3 fuentes (Histórico, Live, Catálogo)|
|                  | exhaustivo de tipos   | - Documentación exhaustiva de tipos, unidades, campos opcionales,     |
|                  |                       |   frecuencia de muestreo, límites de API y latencia observada.        |
|                  |                       | - Partición mensual del histórico 2025 para sortear el límite de      |
|                  |                       |   20.000 registros y deduplicación en fronteras temporales.           |
+------------------+-----------------------+-----------------------------------------------------------------------+
| 2. Calidad       | Análisis completo con | - Apartado formal en memoria o Jupyter Notebook con código ejecutable.|
|                  | acciones justificadas | - Evaluación cuantitativa de 6 dimensiones de calidad (Completitud,   |
|                  |                       |   Unicidad, Validez, Consistencia, Actualidad, Exactitud).            |
|                  |                       | - Demostración de resultados ANTES y DESPUÉS de la limpieza.          |
|                  |                       | - Reglas físicas justificadas: no rellenar nulos con 0; aceptación   |
|                  |                       |   de magnitudes y profundidades negativas justificadas.               |
|                  |                       | - Tabla quarantine_events con aislamiento de registros anómalos.      |
+------------------+-----------------------+-----------------------------------------------------------------------+
| 3. Modelado      | Modelo optimizado     | - Modelos conceptual (ER), lógico (estrella/copo) y físico formal.    |
|                  |                       | - Integración geoespacial punto-en-polígono con Natural Earth.        |
|                  |                       | - Tratamiento explícito de la categoría «Sin país asignado».          |
|                  |                       | - Historial de versiones y estado actual desacoplados.                |
|                  |                       | - Idempotencia demostrada mediante UPSERT condicionado en PostgreSQL. |
|                  |                       | - Índices B-Tree justificados formalmente con planes EXPLAIN ANALYZE. |
+------------------+-----------------------+-----------------------------------------------------------------------+
| 4. Análisis      | Análisis riguroso     | - Ventanas temporales fijas de 1 hora UTC basadas en time_utc.        |
|                  | con insights          | - Distribuciones estadísticas de magnitud y profundidad.              |
|                  |                       | - Comparación histórica con 2025 rigurosa (denominador de 365 días    |
|                  |                       |   incluyendo explícitamente días con 0 eventos; filtros simétricos).  |
|                  |                       | - Redacción de al menos 3 conclusiones fundamentadas con cifras       |
|                  |                       |   precisas, periodos contrastados y limitaciones metodológicas.       |
+------------------+-----------------------+-----------------------------------------------------------------------+
| 5. Reflexión     | Excelente reflexión   | - Justificación formal de complejidad algorítmica Big-O (mejor, medio |
|                  | y propuestas          |   y peor caso) para 3 operaciones críticas.                           |
|                  |                       | - Benchmarks empíricos midiendo tiempo y memoria en 3 tamaños de lote.|
|                  |                       | - Razonamiento de escalabilidad y cuello de botella ante 100M sismos. |
|                  |                       | - Auditoría económica realista de TCO (hardware, energía, storage,    |
|                  |                       |   transferencia de red y coste de desarrollo humano).                 |
+------------------+-----------------------+-----------------------------------------------------------------------+
```

---

## 2. Lista de Comprobación de Entregables (Checklist de Entrega)

La entrega final debe contener de forma verificable los 9 entregables especificados en la Sección 12 del enunciado:

- [ ] **E-01: Repositorio de Código Completo y Reproducible**
  - Código fuente completo y modular (`backend/`, `frontend/`).
  - `compose.yaml` funcional con los 5 servicios obligatorios (`productor`, `broker`, `consumidor`, `almacenamiento`, `api`).
  - `Dockerfile` reproducibles para cada servicio Python con dependencias fijadas (`requirements.txt`).
  - `.env.example` documentado sin ninguna credencial real.
  - Comprobado que levanta de forma limpia con `docker compose up --build -d`.

- [ ] **E-02: Despliegue de Panel en Netlify y Túnel ngrok**
  - URL pública de Netlify accesible para el evaluador.
  - Procedimiento documentado y probado para levantar el túnel ngrok local durante la defensa técnica.
  - El frontend consume la URL HTTPS pública provista por ngrok y maneja caídas de conexión con gracia.

- [ ] **E-03: Diccionario de Datos y Registro de Consultas / Procedencia**
  - Documento formal (`data-spec.md` o anexo en memoria) con tipos, unidades, restricciones y orígenes.
  - Registro de auditoría de consultas (`ingestion_audit`) implementado en base de datos.

- [ ] **E-04: Apartado de Calidad de Datos (Notebook o Memoria)**
  - Documento o Jupyter Notebook ejecutable analizando las 6 dimensiones de calidad.
  - Código de comprobación, métricas cuantitativas antes y después de aplicar reglas.
  - Explicación fundamentada del no relleno de nulos con cero y de la tabla de cuarentena.

- [ ] **E-05: Modelado Conceptual, Lógico y Físico de Base de Datos**
  - Diagrama Entidad-Relación y justificación del grano.
  - Script SQL de creación (`init.sql`) con restricciones de clave primaria, unicidad y claves foráneas.
  - Justificación técnica y evidencia empírica de optimización de índices.

- [ ] **E-06: Análisis Sísmico con Mínimo 3 Conclusiones Fundamentadas**
  - Apartado en la memoria con 3 conclusiones analíticas con cifras cuantitativas exactas.
  - Capturas de pantalla del panel Angular mostrando los filtros aplicados y los gráficos resultantes.

- [ ] **E-07: Informe de Complejidad Computacional, Benchmarks y Costes (TCO)**
  - Estudio Big-O de las 3 operaciones nucleares.
  - Gráficos y tablas de mediciones empíricas de tiempo y consumo de memoria con 3 tamaños de dataset.
  - Proyección y arquitectura de escalado para 100 millones de terremotos.
  - Estimación realista del Coste Total de Propiedad (TCO) desglosado.

- [ ] **E-08: Evidencias de Pruebas de Aceptación y Demostración de Replay**
  - Registro de ejecución exitosa de las 11 pruebas de aceptación (`acceptance-tests.md`).
  - Procedimiento para ejecutar la simulación de reproducción histórica acelerada con su distintivo «REPRODUCCIÓN» en pantalla.

- [ ] **E-09: Explicación Individual y Decisión Técnica Propia**
  - Documento individual justificando el flujo completo de datos extremo a extremo.
  - Defensa razonada de una decisión técnica de diseño propia (ej. elección de KRaft frente a Zookeeper, uso de STRtree frente a PostGIS pesado, o política de commit offset tras commit de BD).

---

## 3. Guía de Redacción de las 3 Conclusiones Analíticas Mínimas

Para obtener la máxima nota en el criterio de **Análisis**, las conclusiones no deben ser genéricas (ej. *«hay muchos terremotos en el mundo»*). Deben seguir el estándar científico:

1. **Conclusión 1 (Distribución Geográfica y Dorsales Oceánicas):**
   - *Estructura:* Comparar el porcentaje de sismos que caen en la categoría «Sin país asignado» frente a eventos terrestres en las últimas 24h y en 2025. Cuantificar qué porcentaje de la sismicidad global es submarina y asociarla a límites de placas tectónicas (Cinturón de Fuego del Pacífico vs. Dorsal Mesoatlántica).
2. **Conclusión 2 (Profundidad Hipocentral vs. Tectónica de Subducción):**
   - *Estructura:* Analizar la correlación entre profundidad y región geográfica (ej. sismos superficiales $<30$ km en fallas transformantes como San Andrés vs. sismos profundos $>300$ km en zonas de subducción en América del Sur o Japón). Reportar el percentil 90 de profundidad.
3. **Conclusión 3 (Tasa Sísmica Actual frente a la Media Histórica 2025):**
   - *Estructura:* Comparar cuantitativamente el recuento de eventos $\text{mag} \ge 4.5$ de las últimas 24 horas frente a la media diaria calculada sobre los 365 días de 2025 (ej. $\mu = 38.2$ sismos/día). Determinar si el día analizado se desvía en más de $\pm 1$ o $\pm 2$ desviaciones típicas, aclarando explícitamente que esto mide variabilidad estadística y **no** constituye una predicción de riesgo inminente.
