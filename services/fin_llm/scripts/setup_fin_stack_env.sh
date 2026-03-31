#!/usr/bin/env bash
set -euo pipefail
source /root/miniconda3/etc/profile.d/conda.sh
ENV_NAME="${1:-fin_stack}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
conda deactivate >/dev/null 2>&1 || true
conda env remove -n "$ENV_NAME" -y >/dev/null 2>&1 || true
conda create -y -n "$ENV_NAME" --clone base
conda activate "$ENV_NAME"
python -m pip install -U pip setuptools wheel
python -m pip install -r "$ROOT_DIR/requirements.in"
python -m pip freeze | sort > "$ROOT_DIR/requirements.lock.txt"
python -V
python -m pip show vllm torch transformers | sed -n 1,120p
