#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import requests
resp = requests.get('http://127.0.0.1:6006/health', timeout=10)
resp.raise_for_status()
print('ok')
PY
