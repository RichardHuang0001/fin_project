#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="/srv/fin/services/fin_agent"
ENV_PREFIX="${FIN_AGENT_CONDA_PREFIX:-/root/autodl-tmp/conda-envs/fin_agent_py312}"
export TMPDIR="${TMPDIR:-/root/autodl-tmp/tmp}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/root/autodl-tmp/pip-cache}"
mkdir -p "$TMPDIR" "$PIP_CACHE_DIR"
source /root/miniconda3/etc/profile.d/conda.sh
conda create -y -p "$ENV_PREFIX" python=3.12 pip
"$ENV_PREFIX/bin/python" -m pip install --upgrade pip
"$ENV_PREFIX/bin/python" -m pip install -r "$ROOT_DIR/requirements.lock.txt"
echo "env_ready:$ENV_PREFIX"
