#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: ./ops/deploy.sh <environment> <tag>" >&2
  exit 1
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_ENV_FILE="$SCRIPT_DIR/deploy.env"
if [[ -f "$DEPLOY_ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$DEPLOY_ENV_FILE"
fi

DEPLOY_ENV="$1"
TAG="$2"
FORTRX_SSH_TARGET="${FORTRX_SSH_TARGET:?Set FORTRX_SSH_TARGET in ops/deploy.env}"
IMAGE_REPOSITORY="${IMAGE_REPOSITORY:?Set IMAGE_REPOSITORY in ops/deploy.env}"
FORTRX_APP_DIR="${FORTRX_APP_DIR:-/srv/fortrx}"
IMAGE_REF="${IMAGE_REPOSITORY}:${TAG}"

require_cmd docker
require_cmd infisical
require_cmd scp
require_cmd ssh
require_cmd tar

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

export_infisical() {
  if [[ -n "${INFISICAL_PROJECT_ID:-}" ]]; then
    infisical export --projectId="$INFISICAL_PROJECT_ID" --env="$DEPLOY_ENV" --format=dotenv && return 0
    infisical export --env="$DEPLOY_ENV" --projectId="$INFISICAL_PROJECT_ID" --format=dotenv && return 0
  fi
  infisical export --env="$DEPLOY_ENV" --format=dotenv
}

echo "Building $IMAGE_REF"
docker build -t "$IMAGE_REF" "$REPO_ROOT"
docker push "$IMAGE_REF"

echo "Fetching secrets from Infisical"
export_infisical > "$tmp_dir/infisical.env"

set -a
source "$tmp_dir/infisical.env"
set +a

# Now login to GHCR using secrets from Infisical
if [[ -n "${GHCR_TOKEN:-}" && -n "${GHCR_USERNAME:-}" ]]; then
  printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
fi


cat "$tmp_dir/infisical.env" > "$tmp_dir/.env.runtime"
{
  echo "IMAGE_REF=$IMAGE_REF"
  echo "DEPLOY_ENV=$DEPLOY_ENV"
  echo "RUNTIME_ENV_FILE=.env.runtime"
} >> "$tmp_dir/.env.runtime"

echo "Syncing runtime assets to $FORTRX_SSH_TARGET:$FORTRX_APP_DIR"
tar -C "$REPO_ROOT" -cf - compose.base.yml compose.prod.yml Caddyfile ops/host | \
  ssh "$FORTRX_SSH_TARGET" "mkdir -p '$FORTRX_APP_DIR' '$FORTRX_APP_DIR/ops/host' && tar -C '$FORTRX_APP_DIR' -xf -"

ssh "$FORTRX_SSH_TARGET" "if [ -f '$FORTRX_APP_DIR/.env.runtime' ]; then cp '$FORTRX_APP_DIR/.env.runtime' '$FORTRX_APP_DIR/.env.runtime.previous'; fi"
scp "$tmp_dir/.env.runtime" "$FORTRX_SSH_TARGET:$FORTRX_APP_DIR/.env.runtime"

ssh "$FORTRX_SSH_TARGET" "find '$FORTRX_APP_DIR/ops' -type f -name '*.sh' -exec chmod +x {} +"

echo "Starting production stack"
ssh "$FORTRX_SSH_TARGET" "APP_DIR='$FORTRX_APP_DIR' bash -s" <<'EOF'
set -euo pipefail

APP_DIR="${APP_DIR:?missing APP_DIR}"
compose=(docker compose --env-file "$APP_DIR/.env.runtime" -f "$APP_DIR/compose.base.yml" -f "$APP_DIR/compose.prod.yml")

"${compose[@]}" pull
"${compose[@]}" up -d --remove-orphans
bash "$APP_DIR/ops/host/install-cron.sh" "$APP_DIR"

for attempt in $(seq 1 24); do
  container_id="$("${compose[@]}" ps -q fortrx)"
  if [[ -n "$container_id" ]]; then
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null || true)"
    if [[ "$health" == "healthy" || "$health" == "running" ]]; then
      break
    fi
  fi
  sleep 5
done

container_id="$("${compose[@]}" ps -q fortrx)"
health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null || true)"
if [[ "$health" != "healthy" && "$health" != "running" ]]; then
  echo "fortrx container did not become healthy." >&2
  exit 1
fi

for attempt in $(seq 1 24); do
  if curl -fsS http://127.0.0.1/ >/dev/null 2>&1; then
    exit 0
  fi
  sleep 5
done

echo "Caddy did not respond on port 80 in time." >&2
exit 1
EOF

echo "Deploy complete."
echo "Rollback hint:"
echo "ssh $FORTRX_SSH_TARGET \"cp '$FORTRX_APP_DIR/.env.runtime.previous' '$FORTRX_APP_DIR/.env.runtime' && docker compose --env-file '$FORTRX_APP_DIR/.env.runtime' -f '$FORTRX_APP_DIR/compose.base.yml' -f '$FORTRX_APP_DIR/compose.prod.yml' up -d --remove-orphans\""
