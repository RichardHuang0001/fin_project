#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${FIN_LLM_VENV_DIR:-/root/autodl-tmp/venvs/fin_llm_py312}"
export TMPDIR="${TMPDIR:-/root/autodl-tmp/tmp}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/root/autodl-tmp/.cache/pip}"
mkdir -p "$TMPDIR" "$PIP_CACHE_DIR" "$(dirname "$VENV_DIR")"
rm -rf "$VENV_DIR"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python -m pip install -U pip setuptools wheel
python -m pip install -r "$ROOT_DIR/requirements.in"
python -m pip freeze | sort > "$ROOT_DIR/requirements.lock.txt"
echo "venv_ready:$VENV_DIR"
