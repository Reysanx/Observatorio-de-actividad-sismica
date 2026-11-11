# Tasks: Benchmarks y TCO reproducibles

**Input**: [spec.md](./spec.md)  
**Plan**: [plan.md](./plan.md)

## Phase 1: Setup y protocolo

- [X] T001 Definir alcance, entradas identificables, lotes, repeticiones,
  métricas y limitaciones en `benchmark-protocol.md`.
- [X] T002 Crear un runner sin escrituras de negocio en
  `backend/scripts/benchmark_spatial.py`.

## Phase 2: Tests y evidencia

- [X] T003 Añadir pruebas de entradas incompletas y estructura de medición en
  `backend/tests/test_benchmark_spatial.py`.
- [X] T004 Ejecutar las pruebas y generar mediciones en
  `evidence/benchmarks/spatial-benchmark.json`.
- [X] T005 Auditar los números TCO, vincular fuentes fechadas y formular el
  modelo en `tco-model.md`.

## Phase 3: Actualización documental

- [X] T006 Corregir `docs/complexity_and_benchmarks.md` para separar teoría,
  resultados medidos y valores anteriores no verificados.
- [X] T007 Corregir `docs/tco_costs.md` para no presentar supuestos o precios
  sin cotización como TCO real.
- [X] T008 Añadir instrucciones de reproducción y validación en
  `quickstart.md`; enlazar E-07 desde el README.
- [X] T009 Ejecutar las pruebas, el benchmark de referencia, validar JSON y
  enlaces internos y comprobar `git diff --check`.
