#!/usr/bin/env bash
set -euo pipefail
cd /srv/fin/services/fin_data_svr
exec ./run_selftest.sh
