---
name: kafka-idempotent-consumer
description: >-
  Procedimiento para implementar el consumo asíncrono con aiokafka, escrituras
  idempotentes mediante UPSERT en PostgreSQL y confirmación de offsets posterior a la BD.
---

# Consumo Asíncrono e Idempotencia Transaccional

Esta habilidad describe la mecánica para garantizar que ningún mensaje duplicado o reinicio del consumidor altere el estado persistido.

## 1. Configuración de `AIOKafkaConsumer`
- Desactivar commit automático: `enable_auto_commit = False`.
- Suscripción al grupo: `group_id = "observatorio-consumer-group"`.
- Política de lectura inicial: `auto_offset_reset = "earliest"`.

## 2. Sentencia SQL Idempotente (UPSERT con Control de Versión)
```sql
INSERT INTO current_earthquakes (
    event_id, mag, mag_type, depth_km, time_utc, updated_utc, 
    adm0_a3, place, geom_lon, geom_lat, raw_properties
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
ON CONFLICT (event_id) DO UPDATE
SET mag = EXCLUDED.mag,
    depth_km = EXCLUDED.depth_km,
    updated_utc = EXCLUDED.updated_utc,
    adm0_a3 = EXCLUDED.adm0_a3,
    raw_properties = EXCLUDED.raw_properties
WHERE EXCLUDED.updated_utc > current_earthquakes.updated_utc;
```

## 3. Protocolo de Commit en Dos Pasos
1. Abrir bloque transaccional en PostgreSQL (`async with pool.acquire() as conn: async with conn.transaction(): ...`).
2. Insertar en `current_earthquakes` (upsert).
3. Insertar registro de versión en `earthquake_versions`.
4. Si la transacción de base de datos se completa con éxito, invocar `await consumer.commit()`.
5. Si PostgreSQL falla o pierde conexión, la transacción revierte y Kafka retiene el offset para reintento automático.
