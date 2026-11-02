# Local runtime

This project runs five backend containers: `productor`, `broker`, `consumidor`,
`almacenamiento`, and `api`. The Angular development server is separate and runs
on the host at `http://localhost:4200`; it is not an additional Compose service.

## Prerequisites

- Docker Desktop with Docker Compose v2 or newer and a running daemon.
- Outbound HTTPS from Docker containers for USGS requests.
- The backend modules, database schema, and Natural Earth file required by the
  Compose mounts must be present in the checkout.

## Start

From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
# Edit .env and replace POSTGRES_PASSWORD with a local-only password.
docker compose config
docker compose up --build -d
docker compose ps
```

`docker compose config` resolves and validates the Compose model before startup.
The broker initializes the `earthquakes.live` (3 partitions) and
`earthquakes.replay` (1 partition) topics with 48-hour retention. PostgreSQL
initializes its schema from `backend/db/init.sql` when its data volume is empty.

Only the API is published, bound to host loopback at
`http://127.0.0.1:8000`; its health endpoint is
`http://127.0.0.1:8000/api/v1/health`. Kafka and PostgreSQL have no host port
mapping and are reachable by service DNS only from the Compose network. The
Angular dev server can call the API from the allowed local origin.

To inspect or follow service logs:

```powershell
docker compose ps
docker compose logs --tail 100
docker compose logs -f productor consumidor api
```

Stop containers without deleting persistent PostgreSQL, Kafka, or USGS cache
data:

```powershell
docker compose down
```

To intentionally reset all local state (this deletes the named volumes):

```powershell
docker compose down --volumes
```

Do not commit `.env`; `.gitignore` excludes it. `.env.example` contains only
non-secret placeholders. No Kafka or PostgreSQL port is published to the host.
