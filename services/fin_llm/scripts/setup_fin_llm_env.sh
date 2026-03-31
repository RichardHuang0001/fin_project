#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PREFIX="${FIN_LLM_ENV_PREFIX:-/root/autodl-tmp/conda-envs/fin_llm_py312}"
export TMPDIR="${TMPDIR:-/root/autodl-tmp/tmp}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/root/autodl-tmp/.cache/pip}"
mkdir -p "$TMPDIR" "$PIP_CACHE_DIR" "$(dirname "$ENV_PREFIX")"
source /root/miniconda3/etc/profile.d/conda.sh
conda env remove -p "$ENV_PREFIX" -y >/dev/null 2>&1 || true
conda create -y -p "$ENV_PREFIX" python=3.12 pip
conda activate "$ENV_PREFIX"
python -m pip install -U pip setuptools wheel
python -m pip install -r "$ROOT_DIR/requirements.in"
python -m pip freeze | sort > "$ROOT_DIR/requirements.lock.txt"
echo "env_ready:$ENV_PREFIX"
