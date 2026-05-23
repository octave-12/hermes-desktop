@echo off
chcp 65001 >nul

REM ========================================
REM   Hermes Desktop - Debug Start
REM ========================================

REM [1/3] Clean old processes
echo [1/3] Cleaning old processes...
taskkill /F /IM node.exe >nul 2>&1
taskkill /F /IM electron.exe >nul 2>&1
wsl pkill -9 -f "python main.py" >nul 2>&1
timeout /t 2 /nobreak >nul

REM [2/3] Start backend (show window)
echo [2/3] Starting backend...
start "Hermes Backend" cmd /k "wsl bash /mnt/d/soso/projects/hermes-desktop/start-backend.sh"
timeout /t 3 /nobreak >nul

REM [3/3] Start frontend (show window)
echo [3/3] Starting frontend...
start "Hermes Frontend" cmd /k "cd /d D:\soso\projects\hermes-desktop && pnpm run dev"
timeout /t 2 /nobreak >nul

echo.
echo Done! Check the windows for logs.
pause
