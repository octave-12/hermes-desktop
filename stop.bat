@echo off
chcp 65001 >nul

REM ========================================
REM   Hermes Desktop - Stop All Services
REM ========================================

echo Stopping all Hermes services...

wsl bash /mnt/d/soso/projects/hermes-desktop/stop.sh

echo.
echo All services stopped.
pause
