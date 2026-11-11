# Modelo de datos: Métricas Reproducibles de Calidad 6D

## Entidades

### Evaluación

Representa una ejecución reproducible del cálculo.

| Campo | Descripción |
|---|---|
| `evaluation_id` | Identificador único de la ejecución/report. |
| `generated_at_utc` | Instante UTC en que se produjo el reporte. |
| `method_version` | Versión del método y del contrato de salida. |
| `rule_set_version` | Identidad de las reglas de calidad evaluadas. |
| `limitations` | Límites de población, comparabilidad y referencia disponibles. |

Una ejecución contiene una o más poblaciones; nunca agrega datos live, replay y sintéticos en un denominador histórico común.

### Población de evaluación

| Campo | Descripción |
|---|---|
| `population_id` | Identificador estable en el reporte. |
| `source` | Procedencia concreta (caché histórica USGS, auditoría live, etc.). |
| `period_start_utc`, `period_end_utc` | Intervalo temporal evaluado, con límites declarados. |
| `filters` | Filtros aplicados por el origen o por la consulta. |
| `input_count` | Número de registros de entrada de la población. |
| `input_identity` | Manifest, claves de dataset e identidad SHA-256 disponible. |
| `after_count` | Registros emparejados/persistidos después; no confundir con `input_count` si hay discrepancias. |

La población histórica primaria es la caché USGS 2025 condicionada a M≥4 y los registros `historical_2025` que corresponden a sus Features.

### Resultado de dimensión

Cada población informa exactamente una entrada por dimensión. Cada entrada puede incluir varias submétricas para representar campos, reglas, etapas o estadísticos con distintos denominadores sin agregarlos en un único valor.

| Campo | Descripción |
|---|---|
| `dimension` | `completeness`, `uniqueness`, `validity`, `consistency`, `currency` o `accuracy`. |
| `metrics` | Una o más submétricas cuantificadas o declaradas no verificables para esa dimensión. |

Cada submétrica incluye `metric_id`, `stage`, `numerator`, `denominator`, `value`, `unit`, `formula`, `evidence` y `limitations`. Para exactitud añade `reference_independent` y `proxy`.

**Reglas de cálculo**:
- Cada población contiene exactamente una entrada por dimensión, sin dimensiones ausentes ni repetidas; cada entrada contiene al menos una submétrica.
- Las submétricas `before`, `after` y `comparison` incluyen numerador, denominador, valor, unidad y evidencia. Las submétricas `not_verifiable` usan valor y unidad nulos e incluyen al menos una limitación que explique la causa.
- Un porcentaje de presencia divide valores presentes por el total de registros elegibles para ese campo; campos permitidos en null se informan aparte.
- Unicidad se calcula sobre `event_id` por población final, diferenciando retransmisión, versión y fila; la fuente cacheada ya fue deduplicada antes de la evaluación.
- Validez cuenta reglas satisfechas sobre observaciones elegibles; no impone límites físicos no definidos por las reglas del proyecto.
- Consistencia compara valores derivados persistidos con su campo fuente y relaciones internas; N/A no implica error.
- Completitud informa submétricas por campo cuando los campos tienen distintas reglas de elegibilidad o denominadores.
- Actualidad informa submétricas independientes para cada latencia y estadístico descriptivo; latencia fuente histórica y latencia operacional live son poblaciones diferentes.
- Exactitud absoluta se marca `not_verifiable` si no existe referencia independiente; todo resultado medido de exactitud se marca como proxy, se nombra explícitamente y no se agrega en una tasa de exactitud global.

### Impacto de transformación

Cada población incluye un inventario de transformaciones relevantes. Cada entrada registra `transformation_id`, etapa, estado (`measured` o `not_verifiable`), número de registros afectados, denominador elegible, definición, evidencia, limitaciones y política de solapamiento (`mutually_exclusive`, `may_overlap` o `not_applicable`). Si la etapa no tiene trazabilidad, los recuentos son nulos y la limitación explica qué registro falta. Los recuentos que pueden solaparse no se suman para reconciliar una población.

### Disposición

Registra la reconciliación de cada población por categoría (`matched`, `missing_after`, `unmatched_source`, `accepted`, `excluded`, `quarantined`), con recuento y definición. Las categorías se hacen mutuamente excluyentes por población o se documenta el solapamiento. Las disposiciones de tablas live no se usan para inferir la cantidad de descartes del histórico.

### Proxy de exactitud

Incluye nombre, campos comparados, población/denominador, medida de coincidencia, referencia observacional usada y limitación. Tipos aceptados en el reporte:

- Fidelidad entre valores del payload fuente conservado y columnas canónicas.
- Concordancia de asignación con la versión de Natural Earth usada por el pipeline.

Ninguno de los dos constituye una referencia independiente de verdad sísmica.

## Relación con el esquema existente

- `historical_2025.raw_payload` preserva el Feature original de las filas importadas; `event_id`, tiempos, magnitud, profundidad y coordenadas permiten las comparaciones posteriores.
- `dataset_imports` identifica el dataset histórico importado y su recuento, pero no sustituye al manifest de caché para procedencia de los archivos fuente.
- El manifest de doce archivos mensuales provee la identidad/filtros del extracto; los conteos de caché pueden incluir registros repetidos entre particiones, por lo que deben distinguirse de IDs únicos.
- `ingestion_audit`, `current_earthquakes` y `quarantine_events` fundamentan métricas live aparte. `earthquake_versions` sirve para revisar versiones y no equivale a eventos únicos.
- Las transformaciones previas a la caché solo tienen recuentos medidos si existe evidencia/auditoría de sus entradas y salidas; de lo contrario se incluyen como no verificables, sin extrapolar datos live.
- No se requiere modificar tablas ni persistir resultados en PostgreSQL.
