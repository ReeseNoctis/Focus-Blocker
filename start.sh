#!/bin/bash
# 🧘 沉浸式学习助手 — 一键启动
# 用法: ./start.sh    (启动前后端 + 打开浏览器)
#       ./start.sh stop   (停止前后端)

set -e
cd "$(dirname "$0")"

PY=./.venv/bin/python3.12
BACKEND_LOG=/tmp/study_assistant_backend.log
FRONTEND_LOG=/tmp/study_assistant_frontend.log
PID_FILE=.claude/run.pids

stop() {
    echo "🛑 正在停止学习助手 …"
    if [ -f "$PID_FILE" ]; then
        while read -r pid; do
            kill "$pid" 2>/dev/null && echo "   已停止 PID $pid"
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    else
        # 兜底:按进程名清理
        pkill -f "uvicorn app.main:app" 2>/dev/null && echo "   已停止后端"
        pkill -f "vite" 2>/dev/null && echo "   已停止前端"
    fi
    echo "✅ 已停止。"
}

if [ "$1" = "stop" ]; then
    stop
    exit 0
fi

# 首次使用检查
if [ ! -x "$PY" ]; then
    echo "❌ 未找到 venv,请先执行:"
    echo "   /opt/homebrew/bin/python3.12 -m venv .venv"
    echo "   ./.venv/bin/pip install -r requirements.txt"
    exit 1
fi
if [ ! -d web/node_modules ]; then
    echo "⚠️  前端依赖未安装,正在安装 …"
    (cd web && npm install)
fi

echo "🚀 正在启动学习助手 …"

# 启动后端
"$PY" -m uvicorn app.main:app --port 8000 > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_FILE"

# 启动前端
(cd web && npm run dev) > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" >> "$PID_FILE"

# 等待后端就绪
for _ in $(seq 1 15); do
    if curl -s http://127.0.0.1:8000/api/tasks >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

echo ""
echo "✅ 学习助手已启动!"
echo "   前端界面: http://localhost:5173"
echo "   后端 API: http://127.0.0.1:8000"
echo ""
echo "   停止: ./start.sh stop"
echo ""

# 打开浏览器
open http://localhost:5173
