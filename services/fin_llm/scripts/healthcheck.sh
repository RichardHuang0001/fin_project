#!/usr/bin/env bash
set -euo pipefail
curl -fsS http://127.0.0.1:${LLM_PORT:-6006}/health >/dev/null && echo ok
