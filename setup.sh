#!/usr/bin/env bash
# WhaleBots Discord Bot - Setup (Linux/macOS)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "   ROK WhalesBot Discord Bot - Setup"
echo "============================================"
echo

# 1. Check Python
echo "[1/5] Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 not found! Please install Python 3.11+"
    exit 1
fi
PY_VERSION=$(python3 --version 2>&1)
echo "[OK] $PY_VERSION"

# 2. Check pip
echo
echo "[2/5] Checking pip..."
if ! python3 -m pip --version &>/dev/null; then
    echo "[ERROR] pip not found! Install with: sudo apt install python3-pip"
    exit 1
fi
echo "[OK] pip is available"

# 3. Create virtual environment
echo
echo "[3/5] Setting up virtual environment..."
VENV_DIR=".venv"

if [ -d "$VENV_DIR" ]; then
    echo "[INFO] Virtual environment already exists at $VENV_DIR"
    read -rp "Recreate? (y/N): " RECREATE
    if [[ "$RECREATE" =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        python3 -m venv "$VENV_DIR"
        echo "[OK] Recreated virtual environment"
    else
        echo "[SKIP] Keeping existing virtual environment"
    fi
else
    python3 -m venv "$VENV_DIR"
    echo "[OK] Created virtual environment at $VENV_DIR"
fi

# 4. Install dependencies
echo
echo "[4/5] Installing dependencies..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt
echo "[OK] Dependencies installed"

# 5. Setup config files
echo
echo "[5/5] Setting up configuration files..."

# Create .env if not exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[OK] Created .env from .env.example"
    elif [ -f env_example.txt ]; then
        cp env_example.txt .env
        echo "[OK] Created .env from env_example.txt"
    else
        echo "[WARN] No .env template found"
    fi
    echo "[IMPORTANT] Edit .env with your Discord Bot Token!"
else
    echo "[SKIP] .env already exists"
fi

# Create data directory and files
mkdir -p data

if [ ! -f data/users.json ]; then
    echo '{"users": {}}' > data/users.json
    echo "[OK] Created data/users.json"
fi

if [ ! -f data/config.json ]; then
    echo '{"admin_users": [], "allowed_guilds": [], "allowed_channels": [], "admin_roles": [], "cooldown_seconds": 60, "max_emulators": 20}' > data/config.json
    echo "[OK] Created data/config.json"
    echo "[IMPORTANT] Add your Discord User ID to admin_users in data/config.json"
fi

if [ ! -f data/audit_logs.json ]; then
    echo '{"logs": []}' > data/audit_logs.json
    echo "[OK] Created data/audit_logs.json"
fi

# Summary
echo
echo "============================================"
echo "          SETUP COMPLETE!"
echo "============================================"
echo
echo "Next steps:"
echo "  1. Edit .env:"
echo "     DISCORD_BOT_TOKEN=your_bot_token_here"
echo "     WHALEBOTS_PATH=/path/to/WhaleBots"
echo
echo "  2. Edit data/config.json:"
echo "     Add your Discord User ID to \"admin_users\""
echo
echo "  3. Run the bot:"
echo "     ./run.sh"
echo "     or manually:"
echo "       source $VENV_DIR/bin/activate"
echo "       python run_bot.py"
echo
echo "============================================"
