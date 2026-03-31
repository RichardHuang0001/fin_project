#!/usr/bin/env bash
set -euo pipefail
set -a
source /srv/fin/config/fin_data_svr.env
set +a
cd /srv/fin/services/fin_data_svr
PYTHON_BIN="${FIN_DATA_SVR_PYTHON:-python}"
"$PYTHON_BIN" selftest_mcp.py >/tmp/fin_data_svr_health.log
printf 'ok\n'
