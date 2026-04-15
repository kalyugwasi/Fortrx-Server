# Fortrx Server

Run the Fortrx backend from a fresh clone with one guided command.

## Stack

- `fortrx`: FastAPI app
- `postgres`: durable message and auth data
- `redis`: live delivery and presence
- `minio`: S3-compatible sealed blob storage
- `caddy`: HTTPS + WebSocket reverse proxy in production
- `duckdns`: dynamic DNS updater in production

## Quick Start

After cloning the repo on a Debian/Ubuntu machine, run:

```bash
bash ops/launch.sh
```

The script:

- installs Docker and Docker Compose v2 if needed
- asks whether you want `local` or `prod`
- creates a local `.env` automatically for `local`
- prompts for Infisical login and exports `.env.runtime` for `prod`
- launches the stack with one `compose.yml`

## Modes

### Local

Choose `local` in `ops/launch.sh`.

Endpoints:

- API: `http://localhost:8000`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

### Production

Choose `prod` in `ops/launch.sh`.

Requirements:

- your repo is linked to the right Infisical project
- the `prod` environment in Infisical contains the runtime secrets
- optional but recommended: provide `INFISICAL_TOKEN` ahead of time for non-interactive auth

The script will:

- install Docker, Docker Compose v2, cron, and `restic`
- use `INFISICAL_TOKEN` if present, otherwise fall back to Infisical login
- export the `prod` secrets into `.env.runtime`
- start the production stack with the `prod` services enabled
- install nightly backups

## Backup and Restore

Manual backup:

```bash
bash ops/backup.sh
```

Restore a snapshot:

```bash
bash ops/restore.sh <snapshot-id>
```

Backups include:

- a logical Postgres dump
- a MinIO volume archive
- metadata about the current environment

The remote backup script uses `restic`, so any backend supported by `restic` can be used by placing the needed env vars in Infisical alongside `RESTIC_REPOSITORY` and `RESTIC_PASSWORD`.
