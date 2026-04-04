#!/usr/bin/env bash
set -euo pipefail

set -a
source /srv/fin/config/fin_agent.env
set +a

SERVICE_DIR="/srv/fin/services/fin_api"
PYTHON_BIN="${FIN_API_PYTHON:-${FIN_AGENT_PYTHON:-python3}}"
HOST="${FIN_API_HOST:-0.0.0.0}"
PORT="${FIN_API_PORT:-8000}"

cd "$SERVICE_DIR"
export PYTHONPATH="/srv/fin/services/fin_agent:/srv/fin/services/fin_api:${PYTHONPATH:-}"

exec "$PYTHON_BIN" -m uvicorn main:app --host "$HOST" --port "$PORT"
