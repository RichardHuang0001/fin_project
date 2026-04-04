#!/usr/bin/env bash
set -euo pipefail

API_PORT="${FIN_API_PORT:-8000}"
WEB_PORT="${FIN_WEB_PORT:-8080}"

echo "🚀 正在启动 fin_api ..."
pkill -f "uvicorn main:app --host 0.0.0.0 --port ${API_PORT}" 2>/dev/null || true
sleep 1
/srv/fin/services/fin_api/scripts/start.sh &
API_PID=$!

echo "🌐 正在启动 fin_web ..."
pkill -f "http.server ${WEB_PORT}" 2>/dev/null || true
sleep 1
/srv/fin/services/fin_web/scripts/start.sh &
WEB_PID=$!

echo "✅ 服务已启动"
echo "   - 前端地址: http://localhost:${WEB_PORT}"
echo "   - 后端 API: http://localhost:${API_PORT}"
echo "按 Ctrl+C 停止所有服务"

trap 'kill ${API_PID} ${WEB_PID} 2>/dev/null || true; exit' INT TERM
wait
