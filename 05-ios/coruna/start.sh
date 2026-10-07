#!/usr/bin/env bash
# Start the full iOS Security Console backend (FastAPI + static files + APIs).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"

PORT="${PORT:-9000}"
HOST="${HOST:-0.0.0.0}"
BASE_URL="${PUBLIC_BASE_URL:-}"

echo "==> Installing Python dependencies (backend/requirements.txt)"
python3 -m pip install -r requirements.txt -q

echo "==> Verifying toolkit (project root verify_setup.py)"
python3 "$ROOT/verify_setup.py"

ARGS=(--host "$HOST" --port "$PORT")
if [[ -n "$BASE_URL" ]]; then
  ARGS+=(--base-url "$BASE_URL")
fi

echo "==> Starting c2_server on ${HOST}:${PORT}"
exec python3 c2_server.py "${ARGS[@]}"
