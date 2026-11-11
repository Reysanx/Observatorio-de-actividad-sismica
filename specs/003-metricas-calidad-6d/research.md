# Research: Métricas Reproducibles de Calidad 6D

**Fecha**: 2026-11-11  
**Spec**: [spec.md](./spec.md)

## Decisión 1: Población primaria de medición

**Decision**: Usar como población principal las Features GeoJSON de la caché mensual USGS 2025 (M≥4), identificada mediante el manifest completado y sus hashes, y comparar cada Feature con el registro canónico correspondiente en `historical_2025` mediante `raw_payload` y `event_id`.

**Rationale**: Es una fuente existente, persistente, verificable y separada del flujo live/replay. El modelo almacena el payload original y permite comprobar las conversiones de campos sin inventar una captura histórica nueva.

**Alternatives considered**:
- Medir exclusivamente `current_earthquakes`: estado cambiante y no reproducible por sí solo; se reserva una instantánea rotulada para observaciones operativas.
- Tratar `historical_2025` como si fuera el feed bruto de USGS: rechazado; la tabla es el resultado posterior del pipeline.
- Inventar o reconstruir un lote «antes» a partir de cifras documentales: rechazado por falta de registros de origen.

**Limitación obligatoria**: El descargador ya solicita `eventtype=earthquake` y `minmagnitude=4.0`, limita la consulta a intervalos mensuales, filtra fuera de intervalo y deduplica por `id`. Por tanto, este extracto no permite medir completitud ni duplicados del universo bruto anterior a esos pasos, ni cuantificar registros que nunca quedaron en caché. Los resultados se describen como evaluación del extracto cacheado y su normalización/persistencia.

## Decisión 2: Definición operativa de antes/después

**Decision**: «Antes» es la Feature original disponible en la caché verificada, y «después» son los valores canónicos de la fila histórica persistida para el mismo `event_id`. Comparar únicamente registros emparejados de esa misma población y documentar explícitamente los campos sin correspondencia o los registros ausentes.

**Rationale**: Evita comparar poblaciones diferentes y usa `raw_payload` como evidencia de procedencia en lugar de una versión hipotética previa.

**Alternatives considered**:
- Comparar dos cohortes temporales o dos fuentes distintas: rechazado, porque confunde cambios de composición con cambios de calidad.
- Aplicar transformaciones destructivas para producir errores «antes»: rechazado; las pruebas sintéticas quedan fuera de resultados reales.
- Afirmar una tasa completa de cuarentena del histórico a partir de `historical_2025`: rechazado; el importador histórico valida/rechaza y no usa la cuarentena live para toda la población.

## Decisión 3: Medición por dimensión

**Decision**:
- **Completitud**: presencia/no nulidad por campo sobre su población elegible; mostrar por separado nulos permitidos. El campo `mag` del histórico está condicionado por el filtro M≥4, así que no representa la completitud de magnitud del catálogo general.
- **Unicidad**: duplicidad de `event_id` en estado histórico final y colisiones en la correspondencia caché→tabla. La deduplicación previa del descargador se declara como limitación, no como logro medido por el reporte.
- **Validez**: forma/tipo GeoJSON, parseabilidad y límites/rangos de las reglas existentes, informando si la fuente cacheada ya excluyó casos.
- **Consistencia**: igualdad verificable entre campos de la Feature y columnas canónicas; coherencia temporal y de fuente; integridad de asignación geográfica según el catálogo, con categoría N/A separada.
- **Actualidad**: medir por separado la demora fuente (`updated`−`time`) del extracto histórico y la demora operacional observable (`ingested_at`−`updated_utc` y `completed_at`−`requested_at`) en una ventana live identificada. No combinar las dos poblaciones ni atribuir al histórico una latencia del pipeline live.
- **Exactitud**: no hay ground truth independiente. Medir solo fidelidad de representación Feature→columnas persistidas y, opcionalmente, concordancia con la regla espacial Natural Earth; identificar ambos resultados como proxies con alcance limitado.

**Rationale**: Las fórmulas respetan semántica física y límites reales de la evidencia almacenada.

**Alternatives considered**:
- Puntuar cada dimensión con una nota única sin denominadores: rechazado por no ser auditable.
- Considerar todos los valores null como fallos, asignar cero a nulos o rechazar magnitudes/profundidades negativas: rechazado por la Constitución.
- Usar coincidencia con Natural Earth como verdad geofísica: rechazado, porque el catálogo cartográfico no verifica la ubicación instrumental del sismo.

## Decisión 4: Artefacto reproducible

**Decision**: Un comando Python de solo lectura genera un JSON versionado con población, regla/método, resultados de las seis dimensiones, numeradores/denominadores, limitaciones, fecha de ejecución e identidad/hash del manifest. La memoria documenta interpretación y enlaza el JSON y el comando.

**Rationale**: El reporte es revisable por máquina y los métodos ejecutables evitan introducir un entorno Jupyter adicional; la rúbrica admite la memoria o notebook con código ejecutable.

**Alternatives considered**:
- Añadir API/UI para mostrar métricas: rechazado; no es necesario para E-04 y aumentaría el alcance.
- Crear tabla de métricas o migración: rechazado; el reporte puede reproducirse sin mutar el modelo.
- Guardar solo porcentajes narrativos: rechazado por pérdida de método y trazabilidad.

## Decisión 5: Lecturas, pruebas y límites de reproducibilidad

**Decision**: Ejecutar lectura y cálculo en un contenedor ya existente con acceso a base de datos y caché. Probar fórmulas como funciones deterministas y validar el reporte con su contrato. Almacenar la salida versionada fuera del volumen temporal.

**Rationale**: Respeta la prohibición de ejecutar backend en el host, conserva la arquitectura de cinco servicios y no requiere acceso externo durante la repetición si la caché está disponible.

**Alternatives considered**:
- Añadir un sexto servicio o exponer PostgreSQL/Kafka: rechazado por la Constitución.
- Consultar USGS en cada reproducción: rechazado como requisito de reproducibilidad; un cambio remoto alteraría la entrada.
- Usar datos sintéticos para publicar resultados observados: rechazado; solo sirven para tests separados.
