#!/usr/bin/env bash
# WhaleBots Discord Bot + Web Dashboard launcher (Linux/macOS)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "   WhaleBots Discord Bot + Dashboard"
echo "========================================"
echo

# Determine Python executable
if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
elif [ -f "venv/bin/python" ]; then
    PYTHON_CMD="venv/bin/python"
else
    PYTHON_CMD="python3"
fi

echo "[INFO] Using Python: $PYTHON_CMD"
echo

# Start Discord Bot in background
echo "[1/2] Starting Discord Bot..."
$PYTHON_CMD run_bot.py &
BOT_PID=$!
echo "[OK] Discord Bot started (PID: $BOT_PID)"
sleep 2

# Start Web Dashboard in background
echo "[2/2] Starting Web Dashboard..."
$PYTHON_CMD run_dashboard.py &
DASH_PID=$!
echo "[OK] Web Dashboard started (PID: $DASH_PID)"

echo
echo "========================================"
echo "[OK] System started successfully!"
echo "========================================"
echo
echo "Discord Bot PID: $BOT_PID"
echo "Web Dashboard PID: $DASH_PID"
echo "Web Dashboard: http://127.0.0.1:5000"
echo
echo "Press Ctrl+C to stop all, or run ./stop.sh"
echo "========================================"

# Save PIDs for stop.sh
echo "$BOT_PID" > "$SCRIPT_DIR/.bot.pid"
echo "$DASH_PID" > "$SCRIPT_DIR/.dash.pid"

# Wait for both processes
trap 'kill $BOT_PID $DASH_PID 2>/dev/null; rm -f "$SCRIPT_DIR/.bot.pid" "$SCRIPT_DIR/.dash.pid"; exit 0' INT TERM
wait
