#!/usr/bin/env bash
set -euo pipefail

SERVICE_DIR="/srv/fin/services/fin_web"
PYTHON_BIN="${FIN_WEB_PYTHON:-${FIN_AGENT_PYTHON:-python3}}"
PORT="${FIN_WEB_PORT:-8080}"

cd "$SERVICE_DIR"
exec "$PYTHON_BIN" -m http.server "$PORT"
