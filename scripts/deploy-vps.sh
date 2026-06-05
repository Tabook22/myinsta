#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE_FRONTEND_DIR="/opt/myinsta/frontend/dist"

cd "$ROOT_DIR"

git pull origin main

cd "$ROOT_DIR/backend"
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -r requirements.txt
fi

cd "$ROOT_DIR/frontend"
npm install
npm run build

sudo mkdir -p "$LIVE_FRONTEND_DIR"
sudo rsync -a --delete "$ROOT_DIR/frontend/dist/" "$LIVE_FRONTEND_DIR/"

sudo systemctl restart myinsta.service
sudo systemctl restart nginx

echo "Deployed MyInsta frontend to $LIVE_FRONTEND_DIR"
