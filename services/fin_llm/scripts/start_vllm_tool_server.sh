#!/usr/bin/env bash
set -euo pipefail
CONDA_PREFIX_PATH="${FIN_LLM_CONDA_PREFIX:-/root/autodl-tmp/conda-envs/fin_llm_py312}"
VLLM_BIN="$CONDA_PREFIX_PATH/bin/vllm"
set -a
source /srv/fin/config/fin_llm.env
set +a
HOST="${LLM_HOST:-127.0.0.1}"
PORT="${LLM_PORT:-6006}"
MODEL_PATH="${MODEL_PATH:?MODEL_PATH is required}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-dianjin}"
exec "$VLLM_BIN" serve "$MODEL_PATH" \
  --host "$HOST" \
  --port "$PORT" \
  --served-model-name "$SERVED_MODEL_NAME" \
  --dtype auto \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_xml
