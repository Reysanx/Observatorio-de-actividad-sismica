# Quickstart: Reproducción del análisis 6D

Esta guía define cómo ejecutar el análisis una vez implementado. El nombre final del módulo y sus opciones se fijarán en las tareas; la validación debe mantener el flujo y las garantías siguientes.

## Prerrequisitos

- Docker Compose y el archivo `.env` local configurado según `.env.example`.
- Servicios `almacenamiento` y `api` disponibles; para el análisis histórico, caché USGS 2025 completa con manifest verificado y dataset importado.
- Los datos de entrada no se descargan ni modifican durante una reproducción.

## Ejecución esperada

Desde la raíz del repositorio:

1. Comprobar disponibilidad sin modificar los datos: validar salud de PostgreSQL, existencia del dataset 2025 y manifest íntegro.
2. Ejecutar el comando de reporte en un contenedor existente (por ejemplo, `api`) en modo solo lectura.
3. Guardar la salida JSON bajo `docs/evidence/data-quality/quality-report.json` y registrar el stdout/stderr o código de salida sin incorporar credenciales.
4. Actualizar la sección de resultados de [memoria_calidad.md](../../docs/memoria_calidad.md) con vínculo a la evidencia, población exacta y limitaciones.

El comando concreto se incorporará aquí cuando quede definido en `tasks.md`; no se debe inventar una ejecución exitosa ni reutilizar resultados de ejemplo.

## Resultado esperado

- Un objeto JSON que valida contra [quality-report.schema.json](./contracts/quality-report.schema.json).
- Para cada población: filtros, periodo cuando aplica, número de entradas, identidad/hash y resultados de las seis dimensiones.
- Cada cifra tiene numerador, denominador, fórmula, unidad y origen de evidencia, o queda explícitamente no verificable con causa.
- Cada población contiene exactamente una entrada por dimensión y puede incluir varias submétricas (por campo, latencia, estadístico o regla). Cada transformación informa etapa, recuento de afectados, denominador y política de solapamiento; etapas sin auditoría se marcan no verificables y sus recuentos no se inventan.
- La entrada caché y el estado canónico posterior se emparejan por `event_id`; el reporte cuantifica faltantes/colisiones sin cruzar poblaciones.
- Exactitud absoluta aparece como no verificable sin referencia independiente. Las comparaciones Feature→columnas y Natural Earth se identifican como proxies limitados.
- `Sin país asignado`, nulos legítimos y magnitudes/profundidades negativas se conservan según las reglas vigentes.
- Ninguna tabla, offset Kafka, caché ni registro de negocio cambia como efecto del comando.

## Validación

- Ejecutar pruebas unitarias del cálculo con casos de nulo legítimo, duplicado/versiones, fecha/latencia no disponible, frontera de coordenadas y N/A geográfico.
- Ejecutar la prueba de integración en la base de datos local y confirmar que las consultas son de solo lectura.
- Repetir con el mismo manifest y conjunto de reglas: comparar todos los recuentos, tasas y campos deterministas; los timestamps de generación se excluyen de la comparación.
- Validar por separado cualquier población live y sintética. No mezclarlas en resultados históricos ni presentarlas como una línea base «antes» inventada.

## Reproducir desde cero

Si la caché o la importación aún no existen, seguir primero el procedimiento de descarga e importación histórica documentado por el proyecto. El proceso de análisis no debe bajar datos automáticamente: el manifest, parámetros de consulta, hashes y la ejecución de importación deben estar disponibles antes de producir resultados.
