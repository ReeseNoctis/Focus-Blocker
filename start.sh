#!/bin/bash
# Study assistant — one-command start / stop
# Usage:
#   ./start.sh              first-time setup (if needed) + start + open browser
#   ./start.sh stop         stop backend, frontend, and release site block
#   ./start.sh visudo-hint  print the exact visudo line (copy-paste)

set -e
cd "$(dirname "$0")"

VENV=./.venv
PY="$VENV/bin/python3"
BACKEND_LOG=/tmp/study_assistant_backend.log
FRONTEND_LOG=/tmp/study_assistant_frontend.log
PID_FILE=.run.pids

find_python() {
    for c in /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12 python3.12 python3; do
        if [ -x "$c" ]; then
            echo "$c"
            return 0
        fi
        if command -v "$c" >/dev/null 2>&1; then
            command -v "$c"
            return 0
        fi
    done
    return 1
}

setup() {
    if [ ! -x "$PY" ]; then
        SYS_PY="$(find_python)" || {
            echo "Python 3.12 was not found."
            echo "On macOS, copy-paste this once:"
            echo "  brew install python@3.12 node"
            exit 1
        }
        echo "Creating virtualenv …"
        "$SYS_PY" -m venv "$VENV"
    fi
    echo "Installing Python packages …"
    "$PY" -m pip install -q -r requirements.txt
    if ! command -v npm >/dev/null 2>&1; then
        echo "npm was not found. On macOS, copy-paste this once:"
        echo "  brew install node"
        exit 1
    fi
    if [ ! -d web/node_modules ]; then
        echo "Installing frontend packages …"
        (cd web && npm install)
    fi
    if [ ! -f config/ai.json ]; then
        cp config/ai.json.example config/ai.json
        echo "Created config/ai.json (optional: paste a DeepSeek API key to enable AI planning)."
    fi
}

stop() {
    echo "Stopping the study assistant …"
    REAL_PY="$("$PY" -c "import os,sys; print(os.path.realpath(sys.executable))" 2>/dev/null || true)"
    if [ -n "$REAL_PY" ] && sudo -n "$REAL_PY" "$(pwd)/focus_blocker.py" --release assistant 2>/dev/null; then
        echo "   Site block released"
    fi
    if [ -f "$PID_FILE" ]; then
        while read -r pid; do
            kill "$pid" 2>/dev/null && echo "   Stopped PID $pid"
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    else
        pkill -f "uvicorn app.main:app" 2>/dev/null && echo "   Stopped backend" || true
        pkill -f "vite" 2>/dev/null && echo "   Stopped frontend" || true
    fi
    echo "Stopped."
}

visudo_hint() {
    if [ ! -x "$PY" ]; then
        echo "Run ./start.sh once first, then run this again."
        exit 1
    fi
    REAL_PY="$("$PY" -c "import os,sys; print(os.path.realpath(sys.executable))")"
    echo "$(whoami) ALL=(ALL) NOPASSWD: $REAL_PY $(pwd)/focus_blocker.py *"
}

if [ "$1" = "stop" ]; then
    stop
    exit 0
fi
if [ "$1" = "visudo-hint" ]; then
    visudo_hint
    exit 0
fi

setup

echo "Starting the study assistant …"

"$PY" -m uvicorn app.main:app --port 8000 > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_FILE"

(cd web && npm run dev) > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" >> "$PID_FILE"

for _ in $(seq 1 20); do
    if curl -s http://127.0.0.1:8000/api/tasks >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

echo ""
echo "Study assistant is running."
echo "   App:  http://localhost:5173"
echo "   API:  http://127.0.0.1:8000"
echo ""
echo "   Stop: ./start.sh stop"
echo ""

if command -v open >/dev/null 2>&1; then
    open http://localhost:5173
fi
