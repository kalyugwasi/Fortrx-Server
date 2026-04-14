#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_TAG="${1:-manual}"

if [[ ! -f "$APP_DIR/.env.runtime" ]]; then
  echo "Missing $APP_DIR/.env.runtime" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "$APP_DIR/.env.runtime"
set +a

RESTIC_REPOSITORY="${RESTIC_REPOSITORY:?Set RESTIC_REPOSITORY in .env.runtime}"
RESTIC_PASSWORD="${RESTIC_PASSWORD:?Set RESTIC_PASSWORD in .env.runtime}"
MINIO_VOLUME="${COMPOSE_PROJECT_NAME:-fortrx}_minio_data"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

compose=(docker compose --env-file "$APP_DIR/.env.runtime" -f "$APP_DIR/compose.base.yml" -f "$APP_DIR/compose.prod.yml")

"${compose[@]}" exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$TMP_DIR/postgres.sql"
docker run --rm \
  -v "$MINIO_VOLUME:/source:ro" \
  -v "$TMP_DIR:/backup" \
  alpine:3.20 \
  sh -c "cd /source && tar czf /backup/minio-data.tar.gz ."

cat > "$TMP_DIR/metadata.txt" <<EOF
timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
deploy_env=${DEPLOY_ENV:-prod}
image_ref=${IMAGE_REF:-unknown}
backup_tag=$BACKUP_TAG
EOF

if ! restic snapshots >/dev/null 2>&1; then
  restic init
fi

restic backup "$TMP_DIR" --tag fortrx --tag "${DEPLOY_ENV:-prod}" --tag "$BACKUP_TAG"
restic forget --prune \
  --keep-daily "${RESTIC_KEEP_DAILY:-7}" \
  --keep-weekly "${RESTIC_KEEP_WEEKLY:-4}" \
  --keep-monthly "${RESTIC_KEEP_MONTHLY:-3}"
