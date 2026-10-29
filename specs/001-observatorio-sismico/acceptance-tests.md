# MATRIZ DE PRUEBAS DE ACEPTACIÓN Y PROTOCOLO DE DEMOSTRACIÓN

> **Feature ID:** `001-observatorio-sismico`  
> **Fase:** Pruebas de Aceptación y Demostración (`acceptance-tests.md`)  
> **Origen del documento:** Sección 11 de [`Fuente_inicial.md`](../../Fuente_inicial.md)  
> **Estado:** Aprobado / Suite de Pruebas de Aceptación  

---

## 1. Matriz de Pruebas de Aceptación Obligatorias

El sistema debe superar sin excepción los 11 escenarios de prueba definidos en el enunciado oficial:

| ID | Nombre de la Prueba | Carga de Entrada / Acción | Comportamiento del Sistema | Resultado Esperado en Base de Datos y UI |
| :---: | :--- | :--- | :--- | :--- |
| **TC-01** | **Recibir un evento nuevo** | Llega un mensaje Kafka con un `event_id` inédito (ej. `test_001`, $M 5.2$, Chile). | El consumidor valida tipos, calcula punto-en-polígono y ejecuta `INSERT` en PostgreSQL. | Se inserta exactamente 1 fila en `current_earthquakes`. El sismo es visible de inmediato en la API, en el mapa Leaflet y en los recuentos agregados. |
| **TC-02** | **Reenviar la misma versión** | Se reenvía a Kafka el mismo mensaje de `test_001` con idéntico timestamp `updated`. | El consumidor procesa el mensaje pero la sentencia `UPSERT` detecta que `EXCLUDED.updated <= current.updated`. | **No** aumenta el número de terremotos. No se duplican registros en `current_earthquakes` ni en agregaciones. Idempotencia verificada. |
| **TC-03** | **Recibir una versión posterior** | Llega `test_001` con un timestamp `updated` superior (ej. magnitud revisada de $M 5.2$ a $M 5.6$). | El consumidor detecta que es una revisión válida, actualiza `current_earthquakes` y guarda registro en `earthquake_versions`. | Cambian los datos en la tabla actual, la ficha del sismo en el mapa refleja $M 5.6$ y se recalculan las agregaciones afectadas sin incrementar el recuento de eventos. |
| **TC-04** | **Recibir después una versión antigua** | Llega `test_001` con un timestamp `updated` anterior al que ya está guardado (desorden en red). | El consumidor evalúa la condición `EXCLUDED.updated > current.updated`, la cual resulta falsa. | La versión antigua **no** sustituye a la más reciente en `current_earthquakes`. Se ignora o se registra en auditoría sin corromper el estado. |
| **TC-05** | **Magnitud nula** | Llega un evento con `properties.mag = null` (ej. sismo recién detectado pendiente de análisis). | El motor de calidad verifica que no es un error de formato, asigna `NULL` en base de datos. | Se conserva en `current_earthquakes` con `mag = NULL`. En la interfaz y mapa se representa visualmente como **«ND»** (No Disponible). Queda prohibido mostrar 0.0. |
| **TC-06** | **Coordenadas inválidas** | Llega un evento con coordenadas fuera de rango (ej. $\text{lat} = 95.0$) o no numéricas (`NaN`). | El motor de calidad rechaza el registro para evitar corromper la cartografía. | El registro se envía a la tabla `quarantine_events` indicando el motivo (`INVALID_COORDINATES_OUT_OF_BOUNDS`). No aparece ningún punto falso o corrupto en el mapa. |
| **TC-07** | **Evento marítimo** | Llega un sismo en dorsal oceánica (ej. Dorsal Mesoatlántica) fuera de polígonos de países. | La operación punto-en-polígono no encuentra intersección en `paises.geojson`. | Se almacena con `adm0_a3 = 'N/A'` y `country_name = 'Sin país asignado'`. Permanece en el mapa y en el análisis general con dicha categoría. |
| **TC-08** | **Reiniciar consumidor** | Se detiene el contenedor consumidor (`docker compose stop consumidor`) y se reanuda (`start`). | El consumidor reanuda desde el último offset confirmado en Kafka. Si re-procesa algún mensaje pendiente, la idempotencia previene efectos duplicados. | La base de datos no sufre duplicidades ni saltos de conteo. El servicio continúa procesando la cola normalmente. |
| **TC-09** | **Cerrar el túnel ngrok** | Se corta el proceso de ngrok durante la navegación del usuario en el panel. | La SPA en Angular detecta timeout o error de red en la llamada cíclica (60s). | El panel muestra un aviso claro de desconexión (banner de pérdida de backend) pero **conserva en pantalla la última lectura válida** con su marca temporal. |
| **TC-10** | **Volver a abrir el túnel ngrok** | Se restablece el túnel ngrok (con la misma URL reservada o actualizando `config.json`). | La llamada cíclica del frontend vuelve a responder exitosamente. | El panel recupera el estado activo automáticamente, oculta la alerta de error y actualiza los sismos sin necesidad de recargar la pestaña del navegador. |
| **TC-11** | **Reproducción histórica (Replay)** | Se activa el comando de simulación histórica acelerada de 2025. | Los eventos transitan por Kafka a alta velocidad marcados con `mode = 'replay'` en topic aislado (`earthquakes.replay`). | El panel muestra el distintivo visual obligatorio **«REPRODUCCIÓN»**. No se mezclan recuentos con los datos del feed en vivo. Se observan revisiones y sismos marítimos controlados. |

---

## 2. Procedimiento de Verificación Automatizada

Para cada caso de prueba se provee un fixture de prueba JSON y un comando de verificación ejecutable:

```bash
# Ejemplo: Ejecución de la suite completa de pruebas de aceptación
docker compose exec api pytest tests/test_acceptance.py -v
```

### Protocolo para Pruebas Manuales durante la Defensa:
1. **Comprobar Idempotencia (TC-02):**
   ```sql
   -- Contar antes del reenvío
   SELECT COUNT(*), COUNT(DISTINCT event_id) FROM current_earthquakes;
   -- Ejecutar script de reenvío forzado de 10 eventos
   -- Contar después: los valores deben ser idénticos
   SELECT COUNT(*), COUNT(DISTINCT event_id) FROM current_earthquakes;
   ```
2. **Inspección de Cuarentena (TC-06):**
   ```sql
   SELECT quarantine_id, source_event_id, failure_reason, quarantined_at 
   FROM quarantine_events ORDER BY quarantined_at DESC LIMIT 5;
   ```
3. **Comprobación de Sismos Marítimos (TC-07):**
   ```sql
   SELECT COUNT(*) FROM current_earthquakes WHERE adm0_a3 = 'N/A';
   ```
