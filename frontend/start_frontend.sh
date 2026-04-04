#!/bin/bash

# Get the absolute path of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

# 1. Start the Backend API (FastAPI)
echo "🚀 正在启动后端 API 服务..."
# Kill existing backend on port 8000
fuser -k 8000/tcp 2>/dev/null
# Use the python from fin_agent environment
PYTHON_PATH="/root/autodl-tmp/conda-envs/fin_agent_py312/bin/python"
cd "$SCRIPT_DIR/backend"
$PYTHON_PATH -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 2. Start the Frontend Web Server
echo "🌐 正在启动前端 Web 服务..."
# Kill existing frontend on port 8080
fuser -k 8080/tcp 2>/dev/null
cd "$SCRIPT_DIR/web"
# Use python's built-in http server to serve the frontend
$PYTHON_PATH -m http.server 8080 &
FRONTEND_PID=$!

echo "✅ 服务已启动!"
echo "   - 前端地址: http://localhost:8080"
echo "   - 后端 API: http://localhost:8000"
echo ""
echo "按 Ctrl+C 停止所有服务"

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM
wait
