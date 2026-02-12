# WhaleBots Discord Bot + Web Dashboard

## Quick Start Guide

### 1. Prerequisites

Make sure you have:
- ✅ Python 3.11+ installed
- ✅ Discord Bot Token from Discord Developer Portal
- ✅ WhaleBots.exe running

### 2. Run automated setup

**Windows:**
```bash
setup.bat
```

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

**Or cross-platform (Python):**
```bash
python setup_system.py
```

This creates the `.venv` virtual environment, installs the Python dependencies, and scaffolds all required JSON files using UTF-8 so multilingual text (Chinese, Korean, Japanese, etc.) is preserved.

### 3. Configure Environment

Edit the generated `.env` file and add your Discord Bot Token:

```env
DISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
WHALEBOTS_PATH=C:\Users\DELL\Downloads\WhaleBots_1013
FLASK_SECRET_KEY=random_secret_key_12345678
FLASK_PORT=5000
FLASK_HOST=127.0.0.1
FLASK_DEBUG=True
```

### 4. Add Your Discord User ID as Admin

Edit `data/config.json`:

```json
{
  "admin_users": ["YOUR_DISCORD_USER_ID_HERE"]
}
```

Notes: the JSON files are saved with UTF-8 encoding, so you can safely store names or labels in any language (Chinese, Korean, Japanese, etc.).

**How to get your Discord User ID:**
1. Discord Settings → Advanced → Enable "Developer Mode"
2. Right-click your name → Copy ID

### 5. Run the System

**Option A: Run both (Recommended)**

Windows:
```bash
run.bat
```

Linux/macOS:
```bash
./run.sh
```

**Option B: Run separately**

Terminal 1 - Discord Bot (Windows):
```bash
.\.venv\Scripts\python.exe run_bot.py
```
Terminal 1 - Discord Bot (macOS/Linux):
```bash
./.venv/bin/python run_bot.py
```

Terminal 2 - Web Dashboard (Windows):
```bash
.\.venv\Scripts\python.exe run_dashboard.py
```
Terminal 2 - Web Dashboard (macOS/Linux):
```bash
./.venv/bin/python run_dashboard.py
```

### 6. Access

- **Discord Bot**: Check Discord, bot should be online
- **Web Dashboard**: Open http://127.0.0.1:5000 in your browser

### 7. Test Commands

In Discord:
```
/help                        - Show all commands
/config current_channel add  - Allow this channel
/status                      - Check your status
/grant @user days:30 emulator_index:0  - Grant access (admin only)
/start                       - Start your bot
/stop                        - Stop your bot
```

## Common Commands

### User Commands
- `/start` - Start your bot instance
- `/stop` - Stop your bot instance
- `/status` - Check bot status
- `/expiry` - View subscription info
- `/help` - Show help

### Admin Commands
- `/grant @user days:30 emulator_index:0` - Grant subscription
- `/add_days @user days:15` - Add more days
- `/set_expiry @user date:2025-12-31` - Set expiry date
- `/revoke @user` - Revoke access
- `/force_start @user` - Force start
- `/force_stop @user` - Force stop
- `/list_expiring days:7` - List expiring users
- `/who` - List running instances
- `/config current_channel add` - Add current channel
- `/logs limit:50` - View audit logs

## Web Dashboard

Access: http://127.0.0.1:5000

### Pages
- **Overview** - System statistics and running instances
- **Users** - Manage users and subscriptions
- **Instances** - Monitor running instances
- **Config** - Configure allowed guilds/channels
- **Logs** - View audit logs

## Troubleshooting

### Bot doesn't start
- Check `.env` file has valid Discord Bot Token
- Make sure bot is invited to your server
- Check intents are enabled in Discord Developer Portal

### "Unknown interaction" error
- Wait 1-2 minutes for commands to sync
- Restart Discord client
- Check bot has "Use Slash Commands" permission

### Start instance fails
- Make sure WhaleBots.exe is running
- Check WHALEBOTS_PATH in .env is correct
- Check emulator_index is valid (0-19)
- View logs in terminal for specific error

### Web dashboard error
- Check port 5000 is not in use
- Make sure Flask is installed: `pip install Flask`

## Stop the System

Windows:
```bash
stop.bat
```

Linux/macOS:
```bash
./stop.sh
```

Or press `Ctrl+C` in each terminal window.

## File Structure

```
WhaleBots_1013/
├── discord_bot/           - Discord bot code
├── web_dashboard/         - Flask web dashboard
├── shared/                - Shared data layer
├── data/                  - JSON database
│   ├── users.json
│   ├── config.json
│   └── audit_logs.json
├── whalebots_automation/  - WhaleBots integration
├── .env                   - Configuration (DO NOT COMMIT)
├── run.bat               - Start everything (Windows)
├── run.sh                - Start everything (Linux/macOS)
├── setup.bat             - Setup (Windows)
├── setup.sh              - Setup (Linux/macOS)
├── setup_system.py       - Cross-platform setup
├── stop.bat              - Stop everything (Windows)
├── stop.sh               - Stop everything (Linux/macOS)
├── run_bot.py            - Bot launcher
└── run_dashboard.py      - Dashboard launcher
```

## Important Notes

- Web dashboard has **NO authentication** - only use on localhost!
- Each Discord user = 1 emulator (don't assign duplicate)
- Bot auto-stops when subscription expires
- All commands are ephemeral (private)
- WhaleBots.exe must be running before starting instances

## Support

Check the plan file for full documentation: `discord-bot-web.plan.md`

---

**Ready to use!** 🚀

Just run `run.bat` (Windows) or `./run.sh` (Linux/macOS) and start managing your WhaleBots!

