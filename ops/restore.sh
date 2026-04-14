#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: ./ops/restore.sh <snapshot-id>" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_ENV_FILE="$SCRIPT_DIR/deploy.env"
if [[ -f "$DEPLOY_ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$DEPLOY_ENV_FILE"
fi

FORTRX_SSH_TARGET="${FORTRX_SSH_TARGET:?Set FORTRX_SSH_TARGET in ops/deploy.env}"
FORTRX_APP_DIR="${FORTRX_APP_DIR:-/srv/fortrx}"
SNAPSHOT_ID="$1"

ssh "$FORTRX_SSH_TARGET" "bash '$FORTRX_APP_DIR/ops/host/restore-stack.sh' '$SNAPSHOT_ID'"
