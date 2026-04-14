#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: ./ops/bootstrap-host.sh user@host" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_ENV_FILE="$SCRIPT_DIR/deploy.env"
if [[ -f "$DEPLOY_ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$DEPLOY_ENV_FILE"
fi

TARGET="$1"
APP_DIR="${FORTRX_APP_DIR:-/srv/fortrx}"

ssh "$TARGET" "APP_DIR='$APP_DIR' bash -s" <<'EOF'
set -euo pipefail

APP_DIR="${APP_DIR:-/srv/fortrx}"

if ! command -v apt-get >/dev/null 2>&1; then
  echo "bootstrap-host.sh currently supports Debian/Ubuntu hosts only." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

sudo apt-get update
sudo apt-get install -y \
  ca-certificates \
  cron \
  curl \
  jq \
  restic \
  ufw \
  unattended-upgrades

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
fi

sudo systemctl enable --now docker
sudo systemctl enable --now cron
sudo systemctl enable --now unattended-upgrades || true

REMOTE_USER="${SUDO_USER:-$USER}"
sudo usermod -aG docker "$REMOTE_USER"

sudo mkdir -p "$APP_DIR/ops/host" "$APP_DIR/backups"
sudo chown -R "$REMOTE_USER":"$REMOTE_USER" "$APP_DIR"

if ! sudo swapon --show | grep -q '^/swapfile'; then
  if [[ ! -f /swapfile ]]; then
    sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
  fi
  sudo swapon /swapfile
  if ! grep -q '^/swapfile ' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
  fi
fi

sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo "Host bootstrap complete. Reconnect once so docker group membership applies cleanly."
EOF
