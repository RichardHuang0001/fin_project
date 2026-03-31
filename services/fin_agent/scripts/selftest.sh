#!/usr/bin/env bash
set -euo pipefail
set -a
source /srv/fin/config/fin_agent.env
set +a
cd /srv/fin/services/fin_agent
PYTHON_BIN="${FIN_AGENT_PYTHON:-python}"
exec "$PYTHON_BIN" test_api.py
