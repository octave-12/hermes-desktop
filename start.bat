@echo off
chcp 65001 >nul

REM Force HOME to correct Windows user profile (prevents D:\home creation)
set "HOME=%USERPROFILE%"

REM ========================================
REM   Hermes Desktop - Silent Start
REM ========================================

REM [1/5] Check and backup Gateway database
echo [1/5] Checking Gateway database...
wsl bash /mnt/d/soso/projects/hermes-desktop/check-db.sh >nul 2>&1

REM [2/5] Stop old processes gracefully
echo [2/5] Stopping old processes...
wsl bash /mnt/d/soso/projects/hermes-desktop/stop.sh >nul 2>&1
timeout /t 2 /nobreak >nul

REM [3/5] Create VBScript to start services hidden
set "START_VBS=%TEMP%\hermes-start.vbs"
echo Set WshShell = CreateObject("WScript.Shell") > "%START_VBS%"
echo WshShell.Run "cmd /c wsl -e bash -c ""~/.hermes/hermes-agent/venv/bin/hermes gateway run --replace --accept-hooks""", 0, False >> "%START_VBS%"
echo WScript.Sleep 2000 >> "%START_VBS%"
echo WshShell.Run "cmd /c wsl -e bash -c ""cd /mnt/d/soso/projects/hermes-desktop/backend && .venv/bin/python main.py""", 0, False >> "%START_VBS%"
echo WScript.Sleep 3000 >> "%START_VBS%"
echo WshShell.Run "cmd /c cd /d D:\soso\projects\hermes-desktop && pnpm run dev", 0, False >> "%START_VBS%"
echo WScript.Sleep 2000 >> "%START_VBS%"

REM [4/5] Run VBScript
cscript //nologo "%START_VBS%" 2>nul
del "%START_VBS%" 2>nul

exit
