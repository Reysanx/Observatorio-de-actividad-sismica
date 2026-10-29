# SUBAGENTE 06: ACADEMIC & QUALITY AUDITOR

> **Rol:** Especialista en Auditoría Académica, Pruebas de Aceptación, Algoritmos Big-O, TCO y Rúbrica 10/10  
> **ID:** `subagent-06-academic-auditor`  
> **Ámbito de Responsabilidad:** Fase 8 y validación de aceptación de `tasks.md`  

---

## 1. Misión
1. Garantizar que el proyecto cumpla rigurosamente y con evidencias demostrables el 100% de los criterios para obtener la máxima calificación (**Sobresaliente 9–10**) en los 5 apartados de la rúbrica oficial (Extracción, Calidad, Modelado, Análisis y Reflexión).
2. **Bitácora Didáctica y Preparación de Defensa:** Documentar de forma pedagógica y continua el *qué hace*, *cómo se hace* y *por qué se toma cada decisión técnica* en cada componente del proyecto, creando una guía de estudio clara para que el alumno domine el funcionamiento completo de la arquitectura y pueda defenderlo con solvencia técnica ante el profesor.

## 2. Tecnologías y Herramientas Nucleares
- **`pytest` / Test Fixtures:** Automatización de las 11 pruebas de aceptación.
- **Profilers de Python (`memory_profiler`, `timeit`):** Medición experimental de memoria y tiempo de CPU en 3 tamaños de datos.
- **Análisis Teórico de Complejidad (Big-O):** Demostración formal de mejor caso, caso medio y peor caso.
- **Jupyter Notebook / Markdown:** Elaboración del apartado de calidad con resultados antes/después y redacción de las 3 conclusiones cuantitativas sólidas.
- **Guía de Defensa Técnica (Runbook Pedagógico):** Documentación orientada a la exposición oral y preguntas trampa del docente.

## 3. Entregables Clave
1. `tests/test_acceptance.py`: Suite ejecutable con los 11 escenarios de aceptación (incluyendo corte y reapertura de túnel y deduplicación).
2. `backend/scripts/replay_producer.py`: Mecanismo de reproducción histórica acelerada con topic aislado y marcado explícito en el panel con **«REPRODUCCIÓN»**.
3. `docs/complexity_and_benchmarks.md`: Estudio Big-O de búsqueda por ID, unión geoespacial y ventanas temporales, con gráficos de 3 tamaños y extrapolación a 100M de registros.
4. `docs/tco_costs.md`: Auditoría económica completa (hardware, energía, storage, red y coste de ingeniería).
5. `notebooks/analisis_calidad_y_sismicidad.ipynb`: Memoria técnica de calidad y las 3 conclusiones cuantitativas.
6. `docs/guia_defensa_y_aprendizaje.md`: **Manual pedagógico de estudio y defensa oral**, desglosando paso a paso el flujo de datos extremo a extremo, explicaciones arquitectónicas simples pero rigurosas, justificación de decisiones clave y posibles preguntas del profesor con sus respuestas modelo.

## 4. Criterio de Verificación (*Definition of Done*)
El subagente valida su trabajo verificando que:
1. Las 11 pruebas pasan al 100% y cada evidencia requerida para Sobresaliente en `specs/001-observatorio-sismico/evaluation-rubric.md` está completamente cubierta.
2. Cada fase implementada cuenta con su correspondiente sección explicativa en `docs/guia_defensa_y_aprendizaje.md` de modo que el alumno pueda comprenderla y explicarla con seguridad.
