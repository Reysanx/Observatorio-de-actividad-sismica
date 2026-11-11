# Quickstart: Evidencia reproducible de índices

## Prerrequisitos

- Docker Compose instalado y servicios del proyecto iniciados.
- Servicio `almacenamiento` saludable y el esquema de `backend/db/init.sql`
  inicializado.
- Datos disponibles para las consultas de la evidencia. La ausencia de filas
  o diferencias en el snapshot puede cambiar el plan elegido y las métricas.

## Ejecutar las consultas

Desde la raíz del repositorio, en PowerShell:

```powershell
Get-Content -Raw 'specs/004-modelado-y-evidencia-indices/evidence/database-indexes/explain-analyze.sql' |
  docker compose exec -T almacenamiento sh -lc 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

El comando devuelve las salidas a la consola; no modifica tablas ni guarda
resultados. `EXPLAIN ANALYZE` ejecuta cada SELECT para medirlo. La captura
versionada de referencia está en
[evidence/database-indexes/explain-analyze.txt](./evidence/database-indexes/explain-analyze.txt).

## Interpretar o actualizar la evidencia

La salida de referencia fue capturada en PostgreSQL 16.4 el 11-11-2026. Los
tiempos y planes pueden variar con el tamaño de las tablas, las estadísticas,
la caché y el hardware. Al generar una nueva captura, anotar fecha, versión y
recuentos de filas; no interpretar diferencias de milisegundos como una
comparación controlada.

Las consultas incluyen filtros temporales, de magnitud, país y ejecución
replay. Los planes ilustran tanto índices utilizados como el escaneo
secuencial preferido para una tabla pequeña. Véase [data-model.md](./data-model.md)
para los índices y sus limitaciones.

