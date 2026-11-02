## 2026-11-02T16:27:23Z — t3.1 broadcast

Health-check all five canonical services; use `condition: service_healthy` only for real dependency edges. `productor` waits for `broker`; `consumidor` waits for `broker` and `almacenamiento`; `api` waits only for `almacenamiento`. Keep the dependency graph acyclic—do not add artificial dependencies to infrastructure roots.
