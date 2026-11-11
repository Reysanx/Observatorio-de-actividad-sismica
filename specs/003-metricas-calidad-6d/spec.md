# Feature Specification: Métricas Reproducibles de Calidad 6D

**Feature Branch**: No creada; se conserva la rama actual por petición del usuario.

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "Empezar la spec-003-metricas-calidad-6d para cerrar el Criterio 2 y E-04: producir métricas reproducibles para las seis dimensiones, indicando datos de entrada, consultas o código y resultados antes/después. Para exactitud, definir qué se puede medir y sus limitaciones; no inventar una verdad de referencia. No crear una nueva rama."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evaluar la calidad con evidencia reproducible (Priority: P1)

Como analista o evaluador, quiero revisar métricas calculadas sobre una población sísmica identificada y reproducible para las seis dimensiones de calidad, de modo que pueda comprobar qué datos entraron, qué reglas se aplicaron y qué cambió después del tratamiento.

**Why this priority**: El Criterio 2 y el entregable E-04 requieren un análisis cuantitativo completo, con acciones justificadas y resultados antes/después, no únicamente una lista de reglas.

**Independent Test**: Seleccionar y fijar un extracto de datos fuente con su periodo, filtros e identidad; ejecutar las comprobaciones documentadas sobre los mismos registros antes y después del tratamiento; confirmar que una segunda ejecución produce los mismos numeradores, denominadores y resultados, y que cada registro queda contabilizado o tiene una exclusión explicada.

**Acceptance Scenarios**:

1. **Given** un extracto fuente identificado y reglas de calidad versionadas, **When** el analista ejecuta las comprobaciones, **Then** obtiene resultados para completitud, unicidad, validez, consistencia, actualidad y exactitud, con numerador, denominador, fórmula, unidad y resultado.
2. **Given** la misma población de entrada, **When** se comparan los estados anterior y posterior al tratamiento, **Then** el informe explica las variaciones y acciones aplicadas, distingue registros aceptados, en cuarentena y excluidos, y reconcilia sus totales con el número de entradas.
3. **Given** un segundo analista con el extracto y el procedimiento documentados, **When** repite el cálculo, **Then** reproduce los resultados deterministas y puede identificar cualquier diferencia ligada a una nueva extracción o versión de reglas.
4. **Given** cifras 6D previas sin población o procedimiento reproducible, **When** se actualiza la memoria de calidad, **Then** esas cifras se retiran o se etiquetan explícitamente como no sustentadas y no se presentan como resultados vigentes.

---

### User Story 2 - Interpretar exactitud sin afirmar una verdad no disponible (Priority: P2)

Como evaluador, quiero saber qué aspectos de la exactitud se pueden comprobar con las fuentes disponibles y cuáles no, para distinguir la fidelidad del procesamiento de la exactitud real del dato sísmico.

**Why this priority**: Las fuentes del proyecto no proporcionan una verdad independiente y completa contra la que validar cada observación. Presentar una tasa de exactitud como si existiera tal referencia produciría una conclusión engañosa.

**Independent Test**: Revisar la sección de exactitud y verificar que cada cifra se identifica como comparación observable o proxy, que su origen y denominador están definidos, que sus limitaciones aparecen junto al resultado y que no se presenta como exactitud científica global.

**Acceptance Scenarios**:

1. **Given** que no existe un conjunto de referencia independiente, **When** se evalúa exactitud, **Then** el informe declara que la exactitud absoluta no es verificable con los recursos disponibles y no inventa etiquetas de verdad ni porcentajes de exactitud.
2. **Given** comparaciones de campos de entrada con valores persistidos o de coordenadas con el catálogo cartográfico, **When** se presentan como evidencia, **Then** se denominan fidelidad de transformación o concordancia espacial, se cuantifican con su población y no se confunden con verdad física independiente.

### Edge Cases

- Si un campo opcional no está presente, su completitud se calcula sobre la población elegible del campo y se distingue de un error de validez.
- Una magnitud nula se conserva como desconocida, no como cero; magnitudes y profundidades negativas no se clasifican automáticamente como inválidas.
- Dos mensajes con igual identificador y revisión idéntica son reenvíos; revisiones distintas del mismo evento no se cuentan como eventos independientes al medir unicidad del estado actual.
- Los eventos sin polígono coincidente se contabilizan como «Sin país asignado» y no como errores de exactitud por defecto.
- Valores no finitos, fechas inválidas, coordenadas fuera de rango o incoherencias entre sobre y carga útil se contabilizan según la regla aplicada y el destino correspondiente.
- Si faltan tiempos comparables o los relojes producen latencias negativas, la actualidad se declara parcial/no verificable para esos registros; no se recortan los valores sin documentarlo.
- Las pruebas con registros dañados artificialmente se identifican y reportan por separado; no se mezclan con tasas observadas en los datos reales.
- Si el extracto no permite reconstruir el estado anterior al tratamiento, el informe no inventa un antes; identifica el faltante y produce una medición comparable a partir de un extracto reproducible adecuado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El análisis MUST identificar cada población evaluada mediante fuente, periodo UTC de extracción o ingestión, filtros, número de registros, fecha de ejecución e identidad verificable del extracto y de las reglas.
- **FR-002**: El análisis MUST evaluar las seis dimensiones —completitud, unicidad, validez, consistencia, actualidad y exactitud— y para cada métrica MUST indicar definición, fórmula, numerador, denominador, unidad, fuente de evidencia y resultado.
- **FR-003**: El análisis MUST documentar consultas, código o pasos de cálculo suficientes para que otra persona reproduzca cada resultado sin depender de cifras ilustrativas.
- **FR-004**: El análisis MUST comparar el estado anterior y posterior al tratamiento sobre la misma población de entrada siempre que los datos disponibles lo permitan; MUST enumerar cada transformación observable y el número de registros afectados sobre su población elegible. MUST indicar para cada recuento su etapa, denominador y evidencia; MUST declarar como no verificables las transformaciones sin trazabilidad suficiente y explicar el motivo. Los recuentos por transformación no se suman como categorías exclusivas salvo que se demuestre que son disjuntos; cuando puedan solaparse, MUST señalarlo.
- **FR-005**: Para la población histórica, el análisis MUST reconciliar únicamente el extracto cacheado con sus filas persistidas y MUST informar registros emparejados, faltantes y no emparejados. MUST declarar que los registros filtrados o deduplicados antes de guardarse en caché y sus disposiciones de cuarentena no son medibles si no existe auditoría de esas etapas. Los recuentos live de aceptados, excluidos y cuarentenados MUST presentarse como una población de observabilidad separada, con denominadores propios; no MUST atribuirse al extracto histórico ni afirmarse como reconciliación completa si la auditoría no cubre todas las etapas.
- **FR-006**: La completitud MUST informar disponibilidad por campo sobre denominadores explícitos, diferenciando campos opcionales, nulos legítimos y faltantes que infringen una regla obligatoria.
- **FR-007**: La unicidad MUST diferenciar eventos distintos, versiones legítimas y retransmisiones duplicadas, e informar la unicidad del estado final por evento.
- **FR-008**: La validez MUST cubrir tipos y estructura, fechas interpretables, finitud y rango de coordenadas y valores numéricos, así como las reglas aplicables a geometría y cuarentena. Los recuentos de cuarentena MUST limitarse a eventos directamente observables en una población auditada separada; si no existe trazabilidad completa desde la entrada, MUST declararse esa limitación.
- **FR-009**: La consistencia MUST medir las reglas internas verificables entre identificadores, marcas temporales, unidades, claves geográficas, revisiones y valores derivados; las categorías geográficas sin asignación MUST permanecer diferenciadas de errores.
- **FR-010**: La actualidad MUST informar latencias observables entre los tiempos disponibles de ocurrencia, actualización, recepción e ingesta, con población, zona horaria y estadísticos descriptivos; MUST declarar insuficiente cualquier población sin los tiempos requeridos.
- **FR-011**: Para exactitud, el análisis MUST declarar si existe una referencia independiente. Si no existe, MUST señalar la exactitud absoluta como no verificable y limitar los resultados a proxies explícitos, como fidelidad de campos persistidos o concordancia con el catálogo espacial, sin llamarlos verdad de referencia.
- **FR-012**: El análisis MUST justificar las reglas de tratamiento, conservar los nulos legítimos, no rechazar automáticamente valores físicos negativos y explicar los motivos de cuarentena y las limitaciones de las fuentes.
- **FR-013**: Los registros artificiales de prueba MUST estar identificados como sintéticos y permanecer separados de las métricas de los extractos reales.
- **FR-014**: El entregable MUST incorporarse a la memoria de calidad o a un notebook reproducible vinculado desde ella, y MUST dejar explícitos los resultados, limitaciones y procedimiento necesarios para evaluar Criterio 2 y E-04.
- **FR-015**: La memoria MUST retirar o etiquetar como no sustentadas las cifras 6D anteriores que no puedan reproducirse desde una población de entrada y un procedimiento identificados.

### Key Entities *(include if feature involves data)*

- **Extracto de evaluación**: Población inmutable o identificable de registros fuente, con periodo, filtros, procedencia, número de entradas e identidad verificable.
- **Regla de calidad**: Comprobación versionada con dimensión, población aplicable, fórmula/condición, acción y destino del registro.
- **Resultado 6D**: Métrica con resultado, numerador, denominador, unidad, periodo y evidencia antes/después.
- **Disposición del registro**: Clasificación del registro procesado como aceptado, cuarentenado, excluido u otra categoría explícitamente definida.
- **Proxy de exactitud**: Comparación observable que mide fidelidad o concordancia limitada y que no equivale a una verdad de referencia independiente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Las seis dimensiones cuentan con al menos una métrica reproducible o, cuando no sea medible, una declaración explícita de no verificabilidad con la causa y evidencia requerida para resolverla.
- **SC-002**: El 100 % de las métricas cuantitativas publicadas incluye población, numerador, denominador, fórmula, unidad y procedimiento de reproducción.
- **SC-003**: Para el extracto histórico cacheado, las entradas se reconcilian con las filas persistidas o se identifican y cuantifican como ausentes/no emparejadas; cualquier paso anterior a la caché sin auditoría se declara no verificable. Los recuentos de aceptación, exclusión y cuarentena de poblaciones live se presentan aparte y solo se consideran reconciliados si la auditoría cubre explícitamente todas las etapas.
- **SC-004**: Una repetición sobre el mismo extracto y versión de reglas reproduce exactamente todos los recuentos y porcentajes deterministas, y los estadísticos temporales dentro de la precisión publicada.
- **SC-005**: El informe diferencia claramente resultados de datos reales y pruebas sintéticas, no atribuye exactitud absoluta cuando no existe referencia independiente y no presenta como vigentes cifras 6D previas no reproducibles.
- **SC-006**: Una persona revisora puede seguir el procedimiento documentado y localizar el código/consulta, datos de entrada y resultado antes/después de las seis dimensiones sin inferir valores ausentes.

## Assumptions

- El entregable se integrará en `docs/memoria_calidad.md` o se enlazará desde ella; no se requiere un panel de calidad en la aplicación.
- La población y el periodo se escogerán en la planificación a partir de fuentes reproducibles ya disponibles; el histórico descargado y el feed observado pueden requerir tratamientos distintos y resultados separados.
- “Antes” significa el mismo extracto fuente antes de las reglas de calidad, no una comparación retrospectiva inventada contra un sistema previo.
- No se dispone de una verdad de referencia sísmica independiente para todas las observaciones; cualquier proxy de exactitud se presentará con alcance limitado.
- Esta feature mide y documenta calidad y decisiones; no modifica el comportamiento de ingesta salvo que la planificación identifique una carencia imprescindible y la añada con alcance explícito.
- Se trabaja en la rama existente; esta especificación no autoriza crear ni cambiar de rama.
