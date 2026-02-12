@echo off
chcp 65001 >nul
title WhaleBots System
echo ========================================
echo    WhaleBots Discord Bot + Dashboard
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
echo [INFO] Starting Discord Bot and Web Dashboard...
echo [INFO] Both services run in this window.
echo [INFO] Press Ctrl+C to stop all.
echo ========================================
echo.

REM Start Web Dashboard in background, then run Bot in foreground
start /b "" "%PY%" run_dashboard.py
echo [OK] Web Dashboard starting on http://127.0.0.1:5000
timeout /t 2 /nobreak >nul

echo [OK] Starting Discord Bot...
echo.
"%PY%" run_bot.py

REM If bot exits, also stop dashboard
echo.
echo [INFO] Bot exited. Stopping dashboard...
taskkill /F /FI "WINDOWTITLE eq WhaleBots System" /PID >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo [OK] System stopped.
pause
