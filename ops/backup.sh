#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_ENV_FILE="$SCRIPT_DIR/deploy.env"
if [[ -f "$DEPLOY_ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$DEPLOY_ENV_FILE"
fi

FORTRX_SSH_TARGET="${FORTRX_SSH_TARGET:?Set FORTRX_SSH_TARGET in ops/deploy.env}"
FORTRX_APP_DIR="${FORTRX_APP_DIR:-/srv/fortrx}"
BACKUP_TAG="${1:-manual}"

ssh "$FORTRX_SSH_TARGET" "bash '$FORTRX_APP_DIR/ops/host/backup-stack.sh' '$BACKUP_TAG'"
