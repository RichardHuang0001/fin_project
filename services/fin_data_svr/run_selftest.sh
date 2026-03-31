#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python >/dev/null 2>&1; then
  exec python selftest_mcp.py "$@"
elif command -v python3 >/dev/null 2>&1; then
  exec python3 selftest_mcp.py "$@"
elif command -v uv >/dev/null 2>&1; then
  exec uv run python selftest_mcp.py "$@"
else
  echo "python/python3 not found" >&2
  exit 1
fi
