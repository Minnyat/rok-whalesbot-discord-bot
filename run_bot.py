"""
Discord bot launcher script.
"""

import os
import sys
from dotenv import load_dotenv
from discord_bot.bot import create_bot
from shared.updater import check_and_prompt


def _app_dir() -> str:
    # When frozen by PyInstaller --onefile, __file__ points to the temp
    # extraction dir; the user's .env lives next to the .exe instead.
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _enable_dpi_awareness() -> None:
    # Without this, on monitors with display scaling > 100%, GetWindowRect /
    # ScreenToClient return virtualized coords while BitBlt captures physical
    # pixels, producing a zoomed-in crop of the emulator window.
    if sys.platform != "win32":
        return
    import ctypes
    try:
        # Per-monitor DPI aware v2 (Windows 10 1703+)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except (AttributeError, OSError):
        pass
    try:
        # Per-monitor DPI aware (Windows 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def main():
    """Main entry point for Discord bot."""
    _enable_dpi_awareness()
    script_dir = _app_dir()
    env_path = os.path.join(script_dir, '.env')

    # Load environment variables from .env file
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        print(f"Error: .env file not found at {env_path}")
        print("Please create a .env file with DISCORD_BOT_TOKEN=your_token_here")
        input("Press Enter to exit...")
        return

    # Check for updates before doing anything else. Exits the process
    # if the user accepts an update so the relauncher can swap files in.
    check_and_prompt()
    
    # Get Discord token
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("Error: DISCORD_BOT_TOKEN not found in .env file")
        print("Please add DISCORD_BOT_TOKEN=your_token_here to .env file")
        input("Press Enter to exit...")
        return
    
    # Get WhaleBots path
    whalebots_path = os.getenv("WHALEBOTS_PATH")
    if not whalebots_path:
        print("Warning: WHALEBOTS_PATH not set, using current directory")
        whalebots_path = os.getcwd()
    
    print("Starting WhaleBots Discord Bot...")
    print(f"WhaleBots path: {whalebots_path}")
    
    # Create and run bot
    bot = create_bot(whalebots_path)
    
    try:
        bot.run(token)
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error running bot: {e}")


if __name__ == "__main__":
    main()

