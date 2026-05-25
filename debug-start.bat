@echo off
chcp 65001 >nul

REM ========================================
REM   Hermes Desktop - Debug Start
REM ========================================

REM [1/5] Check Gateway database health
echo [1/5] Checking Gateway database...
wsl bash /mnt/d/soso/projects/hermes-desktop/check-db.sh

REM [2/5] Stop old processes gracefully
echo [2/5] Stopping old processes...
wsl bash /mnt/d/soso/projects/hermes-desktop/stop.sh
timeout /t 2 /nobreak >nul

REM [3/5] Start Hermes Gateway
echo [3/5] Starting Hermes Gateway...
start "Hermes Gateway" cmd /k "wsl -e bash -c ""~/.hermes/hermes-agent/venv/bin/hermes gateway run --replace --accept-hooks"""
timeout /t 2 /nobreak >nul

REM [4/5] Start backend
echo [4/5] Starting backend...
start "Hermes Backend" cmd /k "wsl bash /mnt/d/soso/projects/hermes-desktop/start-backend.sh"
timeout /t 3 /nobreak >nul

REM [5/5] Start frontend
echo [5/5] Starting frontend...
start "Hermes Frontend" cmd /k "cd /d D:\soso\projects\hermes-desktop && pnpm run dev"
timeout /t 2 /nobreak >nul

echo.
echo Done! Check the windows for logs.
pause
