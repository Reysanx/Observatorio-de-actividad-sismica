# Feature Specification: Análisis Sísmico Reproducible

**Feature Branch**: `[002-analisis-sismico-reproducible]`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User request, following the read-only rubric audit: specify the first bounded improvement to make the seismic analysis reproducible and resolve unsupported or contradictory conclusions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Revisar conclusiones sísmicas trazables (Priority: P1)

Como analista o evaluador, quiero consultar conclusiones cuantitativas respaldadas por datos y cálculos reproducibles, para verificar qué muestran los registros sin depender de cifras sin fuente o inconsistentes.

**Why this priority**: Las conclusiones analíticas son un entregable explícito de la rúbrica y la auditoría encontró cifras incompatibles o sin evidencia suficiente.

**Independent Test**: Seleccionar la ventana de observación y los datos históricos definidos, repetir los cálculos documentados y comprobar que las cifras del informe y las visualizaciones coinciden con los resultados obtenidos.

**Acceptance Scenarios**:

1. **Given** que se ha seleccionado una ventana reciente de 24 horas y existe el catálogo histórico de 2025, **When** el analista compara los eventos con magnitud igual o superior a 4,5, **Then** el resultado presenta el recuento reciente y la media diaria histórica calculada sobre los 365 días del año, incluidos los días sin eventos, usando el mismo umbral y filtros geográficos en ambos periodos.
2. **Given** los eventos del periodo y los filtros geográficos seleccionados, **When** el analista revisa la distribución de profundidades, **Then** puede identificar el percentil 90 y los recuentos y proporciones empleados para sustentar la conclusión.
3. **Given** los datos, filtros y periodo de referencia utilizados, **When** un evaluador repite los cálculos descritos, **Then** obtiene los mismos valores publicados o una diferencia explicada por la actualización del periodo reciente.

---

### User Story 2 - Verificar la evidencia visual del análisis (Priority: P2)

Como evaluador, quiero ver capturas del panel con los filtros y resultados correspondientes, para contrastar las conclusiones escritas con la información que presenta el observatorio.

**Why this priority**: La rúbrica solicita capturas que muestren los filtros aplicados y las visualizaciones resultantes.

**Independent Test**: Abrir el panel, aplicar los filtros descritos en el informe y verificar que las capturas muestran el periodo, el umbral, los filtros geográficos y los valores usados en las conclusiones.

**Acceptance Scenarios**:

1. **Given** que el informe identifica sus filtros y periodos, **When** se capturan las visualizaciones asociadas, **Then** cada captura permite reconocer los filtros, el alcance temporal y las cifras relevantes sin inferirlos del texto circundante.
2. **Given** que el panel no puede mostrar uno de los indicadores requeridos, **When** se prepara la evidencia, **Then** esa limitación se registra explícitamente y no se presenta una captura como prueba de un indicador que no aparece.

### Edge Cases

- Si el histórico de 2025 está vacío o incompleto, el análisis debe señalarlo y no presentar la media ni las comparaciones como completas.
- Si un día del periodo histórico no tiene eventos que cumplan el umbral, debe contribuir con cero al cálculo de los 365 días.
- Si no hay datos recientes que cumplan los filtros, el recuento reciente debe ser cero y las métricas que no se puedan calcular deben indicarse como no disponibles, no como cero.
- Si la desviación estándar histórica es cero, el informe no debe dividir por cero ni producir una puntuación estandarizada ficticia.
- Si los filtros geográficos dejan un subconjunto vacío en el histórico o en el periodo reciente, debe indicarse qué lado carece de datos.
- Si el periodo reciente cambia entre ejecuciones, deben conservarse su fecha y límites temporales para contextualizar cualquier variación.
- Si los totales o porcentajes no coinciden entre tabla, gráficos y conclusiones, la publicación debe considerarse inválida hasta reconciliar las cifras.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El análisis debe identificar la fuente, fecha de extracción, periodo temporal, población de eventos y filtros utilizados para cada resultado publicado.
- **FR-002**: El análisis comparativo debe contrastar los eventos de las últimas 24 horas con la media diaria de los 365 días de 2025, utilizando el mismo umbral de magnitud igual o superior a 4,5 y los mismos filtros geográficos en ambos conjuntos.
- **FR-003**: El cálculo de la referencia diaria de 2025 debe incluir explícitamente los 365 días, asignando recuento cero a cada día sin eventos que cumplan los filtros.
- **FR-004**: El análisis comparativo debe informar los recuentos observados, la media diaria histórica, la desviación estándar de los recuentos diarios históricos y la desviación del recuento reciente respecto a esa referencia. Si una métrica no está definida, debe explicarse el motivo.
- **FR-005**: El análisis de profundidad debe informar población válida, percentil 90, unidades, periodo y filtros aplicados. Los valores ausentes no deben imputarse como cero.
- **FR-006**: El informe debe contener al menos tres conclusiones cuantitativas: distribución de eventos por país asignado frente a «Sin país asignado» en las poblaciones reciente e histórica; distribución de profundidad por región con percentil 90 sobre el histórico 2025; y comparación del recuento reciente frente a la media y desviación estándar diaria de 2025. Las tres conclusiones usarán magnitud igual o superior a 4,5 y filtros geográficos declarados. Cada conclusión debe vincularse a datos, cálculos, periodos y filtros.
- **FR-007**: Las conclusiones deben distinguir los resultados observados de su interpretación. Las explicaciones tectónicas o geológicas deben identificarse como hipótesis o apoyarse en fuentes externas citadas; los datos por sí solos no demuestran causalidad tectónica.
- **FR-008**: Las cifras publicadas deben ser internamente coherentes: numeradores, denominadores, porcentajes, totales y etiquetas deben poder reconciliarse mediante los datos y cálculos documentados.
- **FR-009**: El analista debe poder revisar visualmente los filtros y resultados que sustentan el informe; la evidencia debe incluir capturas del panel cuando los indicadores estén disponibles en él.
- **FR-010**: Si la interfaz o el análisis existente no permite obtener el umbral, estadístico o filtro exigido, el faltante debe quedar identificado como una necesidad funcional verificable antes de declarar el entregable completo.
- **FR-011**: El informe debe documentar las limitaciones de comparar una ventana móvil reciente con un año natural histórico y no debe describir la variabilidad observada como predicción de riesgo sísmico.
- **FR-012**: No deben conservarse como resultados confirmados cifras previas de documentación que no puedan reproducirse desde los datos identificados.

### Key Entities *(include if feature involves data)*

- **Periodo de análisis**: Intervalo de observación reciente o histórico, expresado con límites temporales y zona horaria inequívocos.
- **Población analizada**: Eventos que cumplen el umbral, los filtros de calidad y los filtros geográficos declarados.
- **Referencia diaria histórica**: Serie de 365 recuentos diarios de 2025, incluidos los días con recuento cero.
- **Resultado estadístico**: Recuento, porcentaje, media, desviación estándar o percentil con unidad, población, periodo y método de cálculo.
- **Conclusión**: Afirmación analítica asociada a uno o más resultados y a las limitaciones pertinentes.
- **Evidencia visual**: Captura del panel que identifica los filtros y resultados representados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El informe presenta las tres conclusiones requeridas —asignación geográfica, profundidad por región y comparación de recuentos— y cada cifra puede rastrearse a un periodo, población, filtros y cálculo identificados.
- **SC-002**: La comparación de magnitud usa el mismo umbral de 4,5 o superior en la ventana reciente y en los 365 días históricos.
- **SC-003**: La referencia anual contiene exactamente 365 recuentos diarios y los días sin eventos válidos aparecen como cero.
- **SC-004**: El percentil 90 de profundidad se acompaña de la población, periodo, filtros, unidad y método de cálculo, y puede reproducirse.
- **SC-005**: Los totales y porcentajes del informe son aritméticamente coherentes con sus numeradores y denominadores, con diferencias de redondeo explícitas.
- **SC-006**: Un evaluador puede repetir los cálculos documentados sobre la misma instantánea de datos y obtener los mismos resultados, salvo redondeo explícitamente indicado.
- **SC-007**: Cada captura usada como evidencia permite identificar los filtros y el periodo aplicados; los indicadores no visibles en el panel se declaran como limitaciones.
- **SC-008**: La comparación indica si el recuento reciente se encuentra a más de una o dos desviaciones estándar de la media histórica, según corresponda; si la desviación no está definida, lo indica sin clasificarlo.
- **SC-009**: Ninguna conclusión presenta una asociación tectónica, una desviación estadística o una cifra histórica sin indicar su base y sus limitaciones.

## Assumptions

- La rúbrica de evaluación vigente es la fuente de los requisitos de este análisis; cuando la documentación anterior o el comportamiento actual difieran, se deberá hacer visible la discrepancia y no asumir que la cifra antigua es correcta.
- El umbral de comparación exigido por la rúbrica y por el contrato actualizado en `specs/001-observatorio-sismico/spec.md` es M ≥ 4,5. El catálogo histórico puede conservar eventos desde M ≥ 4,0; el endpoint actual aún compara con M ≥ 4,0 y esta feature implementa el cambio simétrico a M ≥ 4,5.
- El periodo reciente es una ventana móvil de las últimas 24 horas en UTC, no un día natural.
- El año 2025 tiene 365 días y su comparación utiliza el mismo umbral y filtros disponibles para la ventana reciente.
- El conjunto histórico debe poder identificarse y comprobarse como completo antes de publicarse una conclusión como definitiva.
- Las conclusiones y cifras existentes en la documentación son hipótesis por verificar, no resultados aceptados de antemano.
- La especificación cubre el análisis reproducible y sus evidencias; no incluye despliegue público, rediseño general del dashboard ni cambios de infraestructura que no sean necesarios para cumplir los requisitos anteriores.
- Cualquier reflexión individual sobre la interpretación de resultados debe ser revisada y asumida por el estudiante.
