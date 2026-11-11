# Spec: Evidencias de ingesta y auditoría

**Feature ID**: `006-evidencias-de-ingesta-y-auditoria`  
**Criterio**: 1  
**Evidencia**: E-03  
**Estado**: Completa (evidencia de ingesta; no incluye auditoría de lecturas API)

## Contexto

El proyecto utiliza tres conjuntos de entrada: el feed USGS de las últimas 24
horas (`usgs_live`), el catálogo histórico USGS 2025 (`usgs_2025`) y el
GeoJSON cartográfico de países Natural Earth. El tercero es un catálogo de
referencia local, no un feed sísmico ni un poll USGS.

La tabla PostgreSQL `ingestion_audit` identifica `poll_id` y `source`, guarda
marcas `requested_at`/`completed_at`, estado HTTP, hash, conteos y errores. El
productor publica un registro `poll_audit` por sondeo del feed live y el
consumidor lo persiste idempotentemente. No representa lecturas de la API por
usuarios. El requisito antiguo de E-03 que llama a esta tabla «registro de
auditoría de consultas» es ambiguo y no coincide con su esquema o escritor.

## Requisitos

- **FR-001**: Producir una salida JSON verificable para los tres conjuntos,
  con identificación de ficheros/manifest, conteos, errores y tiempos
  disponibles.
- **FR-002**: Reportar los sondeos live desde PostgreSQL, incluyendo estado,
  conteos acumulados, duración almacenada y cadencia.
- **FR-003**: Verificar los doce ficheros mensuales 2025 contra el manifest y
  contrastar el recuento importado con `dataset_imports` y las filas
  particionadas.
- **FR-004**: Cargar y validar Natural Earth con el mismo `SpatialIndex` de
  producción e informar hash, número de Features y tiempo de carga/índice.
- **FR-005**: Declarar las limitaciones temporales: las filas históricas de
  sondeo están serializadas a segundos y no permiten inferir latencia exacta;
  la importación histórica no persiste duración de descarga o escritura.
- **FR-006**: Definir `ingestion_audit` como auditoría de intentos de ingesta,
  no de consultas de usuario. La auditoría de lecturas API, si se requiere,
  tendrá una tabla/contrato independiente.
- **FR-007**: La ejecución del informe es de solo lectura y falla explícitamente
  si una fuente no valida o la consulta a PostgreSQL no se puede completar.

## Criterios de aceptación

1. El informe contiene tres entradas identificadas como `usgs_live`,
   `usgs_2025` y `natural_earth_countries`.
2. El histórico declara Feature count, IDs únicos, conteos mensuales, hashes,
   verificación del cache e importación registrada en PostgreSQL.
3. La fuente live declara conteos recibidos/aceptados/excluidos/cuarentena,
   estados, errores, intervalo entre polls y precisión de los tiempos.
4. Natural Earth informa SHA-256, Features indexadas y duración medida.
5. Ninguna duración ausente se inventa: se documenta como no registrada.
6. La documentación separa auditoría de ingesta de auditoría de consultas de
   usuarios y explica la diferencia con el texto existente de E-03.
