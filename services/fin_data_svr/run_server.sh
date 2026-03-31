#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python >/dev/null 2>&1; then
  exec python mcp_server.py "$@"
elif command -v python3 >/dev/null 2>&1; then
  exec python3 mcp_server.py "$@"
else
  echo "python/python3 not found" >&2
  exit 1
fi
