#!/usr/bin/env bash
set -euo pipefail
set -a
source /srv/fin/config/fin_data_svr.env
set +a
cd /srv/fin/services/fin_data_svr
PYTHON_BIN="${FIN_DATA_SVR_PYTHON:-python}"
exec "$PYTHON_BIN" mcp_server.py
