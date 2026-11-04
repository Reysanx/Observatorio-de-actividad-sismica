## 2026-11-02T16:27:23Z — t3.1 broadcast

Health-check all five canonical services; use `condition: service_healthy` only for real dependency edges. `productor` waits for `broker`; `consumidor` waits for `broker` and `almacenamiento`; `api` waits only for `almacenamiento`. Keep the dependency graph acyclic—do not add artificial dependencies to infrastructure roots.

## 2026-11-02T19:24:03Z — t20 tester

Backend acceptance checks pass. TC-05 visual “ND”, TC-09/10 outage recovery, and TC-11 replay badge remain browser scope for t21/t28; TC-08 verifies redelivery idempotency but not an actual consumer container restart.
