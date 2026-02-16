@echo off
chcp 65001 >nul
title WhaleBots Discord Bot
echo ========================================
echo    WhaleBots Discord Bot
echo ========================================
echo.

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Find Python executable - prefer .venv
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PY=%SCRIPT_DIR%.venv\Scripts\python.exe"
    echo [OK] Using .venv Python
) else if exist "%SCRIPT_DIR%venv\Scripts\python.exe" (
    set "PY=%SCRIPT_DIR%venv\Scripts\python.exe"
    echo [OK] Using venv Python
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found! Run setup.bat first.
        pause
        exit /b 1
    )
    set "PY=python"
    echo [WARN] Using system Python (no venv found)
)

REM Verify Python works
"%PY%" --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python executable not working: %PY%
    echo Try running setup.bat to recreate the virtual environment.
    pause
    exit /b 1
)

echo.
echo [INFO] Starting Discord Bot...
echo [INFO] Press Ctrl+C to stop.
echo ========================================
echo.

"%PY%" run_bot.py

echo.
echo [OK] Bot stopped.
pause
