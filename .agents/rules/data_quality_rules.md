# REGLAS Y DIRECTIVAS DE CALIDAD DE DATOS (6D)

> **Ámbito:** Ingesta, Consumidor, Modelado y Consultas Analíticas.  
> **Prioridad:** Obligatoria / Requisito para Sobresaliente (9–10).  

---

## 1. Respeto a la Realidad Física de la Sismología
- **Prohibido rellenar nulos con 0:** Si `mag` es `null`, se conserva como `NULL` en base de datos y se muestra como **«ND»** (No Disponible) en la interfaz gráfica. Asignar 0.0 falsearía las estadísticas y medias de magnitud.
- **Validez de Magnitudes Negativas:** Una magnitud negativa (ej. $-0.5$ o $-1.2$) es físicamente posible y válida (sismos de energía microscópica registrados por sismógrafos ultrasensibles). **No deben descartarse ni modificarse**.
- **Validez de Profundidades Negativas:** Una profundidad negativa (ej. $-1.5$ km) indica que el foco del sismo ocurrió por encima del nivel del mar (en elevaciones montañosas o edificios volcánicos). **No deben rechazarse sin estudio**.

## 2. Reglas de Integración Espacial y Fronteras
- **Categoría «Sin país asignado»:** Si las coordenadas del sismo no caen dentro de ningún polígono de país en `paises.geojson` (ej. sismos en dorsales oceánicas o zonas marítimas), se le asigna obligatoriamente `adm0_a3 = 'N/A'` y `country_name = 'Sin país asignado'`.
- **Prohibido Imputar al País Cercano:** No se debe asignar un sismo oceánico al país más próximo ni inferir el país mediante el campo de texto libre `properties.place`.
- **Resolución Determinista de Límites:** Si un punto coincide con una frontera compartida, se asigna la entidad de menor código lexicográfico en `ADM0_A3`.

## 3. Protocolo de Cuarentena
- Todo registro con errores insalvables (coordenadas fuera del rango $[-180, 180] \times [-90, 90]$, valores `NaN` o `Inf`, o JSON corrupto) debe enviarse inmediatamente a la tabla `quarantine_events`.
- Se debe almacenar: identificador origen, motivo explícito (`failure_reason`), carga útil completa en formato JSON y timestamp de aislamiento.
