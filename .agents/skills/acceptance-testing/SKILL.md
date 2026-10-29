---
name: acceptance-testing
description: >-
  Procedimiento para ejecutar la suite de 11 pruebas de aceptación obligatorias,
  validar la recuperación de caídas de túnel ngrok y activar el modo replay con distintivo visual.
---

# Protocolo de Ejecución de Pruebas de Aceptación (TC-01 a TC-11)

Esta habilidad establece el procedimiento formal para verificar cada escenario de prueba exigido por el evaluador.

## 1. Suite Automatizada con PyTest
Ejecutar desde el contenedor API o consumidor:
```bash
docker compose exec api pytest tests/test_acceptance.py -v
```

## 2. Validación de Escenarios Críticos
- **TC-02 (Idempotencia ante reenvío):** Comprobar que reinyectar un mensaje idéntico deja el recuento `SELECT COUNT(*) FROM current_earthquakes` inalterado.
- **TC-03 y TC-04 (Control cronológico de revisiones):** Enviar versión posterior $\rightarrow$ se actualizan datos; enviar versión antigua con timestamp menor $\rightarrow$ se rechaza o ignora.
- **TC-05 (Magnitud nula):** Enviar evento con `mag: null` $\rightarrow$ se guarda `NULL` en PostgreSQL y se comprueba que en el frontend se muestra como `ND`.
- **TC-06 (Coordenadas corruptas):** Enviar evento con `lat = 120.0` $\rightarrow$ no entra a la cartografía; se verifica en `quarantine_events`.
- **TC-07 (Marítimo):** Enviar evento en mitad del océano $\rightarrow$ se valida que `adm0_a3 = 'N/A'` y nombre = «Sin país asignado».
- **TC-09 y TC-10 (Túnel ngrok):** Detener proceso ngrok $\rightarrow$ el frontend muestra aviso de desconexión sin borrar la última lectura; reiniciar ngrok $\rightarrow$ el panel reanuda la sincronización de inmediato.
- **TC-11 (Modo Replay):** Inyectar eventos con `mode="replay"` $\rightarrow$ el panel despliega el distintivo amarillo/rojo «REPRODUCCIÓN».
