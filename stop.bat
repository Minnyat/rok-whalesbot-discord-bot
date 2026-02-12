@echo off
chcp 65001 >nul
title Stop WhaleBots
echo ========================================
echo    Stopping WhaleBots System
echo ========================================
echo.

REM Kill Python processes running our scripts
echo [INFO] Stopping Discord Bot and Web Dashboard...

REM Kill by window title
taskkill /FI "WINDOWTITLE eq WhaleBots System*" /F >nul 2>&1

REM Kill specific Python scripts
for /f "tokens=2" %%a in ('wmic process where "commandline like '%%run_bot.py%%'" get processid /value 2^>nul ^| find "="') do (
    taskkill /F /PID %%a >nul 2>&1
    echo [OK] Stopped run_bot.py (PID: %%a)
)
for /f "tokens=2" %%a in ('wmic process where "commandline like '%%run_dashboard.py%%'" get processid /value 2^>nul ^| find "="') do (
    taskkill /F /PID %%a >nul 2>&1
    echo [OK] Stopped run_dashboard.py (PID: %%a)
)

REM Also free port 5000
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
    echo [OK] Freed port 5000 (PID: %%a)
)

echo.
echo ========================================
echo [OK] System stopped
echo ========================================
pause
