#!/usr/bin/env bash
# Stop WhaleBots system (Linux/macOS)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================"
echo "   Stopping WhaleBots System"
echo "========================================"
echo

stopped=0

# Stop by saved PID files
for pidfile in "$SCRIPT_DIR/.bot.pid" "$SCRIPT_DIR/.dash.pid"; do
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null && echo "[OK] Stopped process $pid" && stopped=$((stopped+1))
        else
            echo "[INFO] Process $pid already stopped"
        fi
        rm -f "$pidfile"
    fi
done

# Also kill any Python processes running our scripts
for script in run_bot.py run_dashboard.py; do
    pids=$(pgrep -f "$script" 2>/dev/null || true)
    for pid in $pids; do
        kill "$pid" 2>/dev/null && echo "[OK] Stopped $script (PID: $pid)" && stopped=$((stopped+1))
    done
done

# Kill anything on port 5000
fuser -k 5000/tcp 2>/dev/null && echo "[OK] Freed port 5000" && stopped=$((stopped+1))

echo
echo "========================================"
if [ "$stopped" -gt 0 ]; then
    echo "[OK] System stopped ($stopped processes)"
else
    echo "[INFO] No running processes found"
fi
echo "========================================"
