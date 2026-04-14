# Fortrx Server

Docker-first deployment for the Fortrx backend, designed to run the same way on a local machine, a single cloud VM, or any Linux host with Docker.

## Stack

- `fortrx`: FastAPI app
- `postgres`: durable message and auth data
- `redis`: live delivery and presence
- `minio`: S3-compatible sealed blob storage
- `caddy`: HTTPS + WebSocket reverse proxy in production
- `duckdns`: dynamic DNS updater in production

## Local Development

Copy `.env.example` to `.env`, then run:

```bash
docker compose -f compose.base.yml -f compose.local.yml up --build
```

Compatibility shortcut:

```bash
docker compose up --build
```

Local endpoints:

- API: `http://localhost:8000`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

## Production Workflow

1. Create `ops/deploy.env` from `ops/deploy.env.example`.
2. Store runtime secrets in Infisical.
3. Bootstrap a fresh host:

```bash
./ops/bootstrap-host.sh user@host
```

4. Deploy a tagged image:

```bash
./ops/deploy.sh prod v1
```

The deploy script:

- builds and pushes a public GHCR image
- exports secrets from Infisical into a transient `.env.runtime`
- syncs only production compose/runtime assets to the server
- starts `compose.base.yml + compose.prod.yml`
- installs nightly backups

## Backup and Restore

Manual backup:

```bash
./ops/backup.sh
```

Restore a snapshot:

```bash
./ops/restore.sh <snapshot-id>
```

Backups include:

- a logical Postgres dump
- a MinIO volume archive
- metadata about the deploy image and environment

The remote backup script uses `restic`, so any backend supported by `restic` can be used by placing the needed env vars in Infisical alongside `RESTIC_REPOSITORY` and `RESTIC_PASSWORD`.
