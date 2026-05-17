@echo off
chcp 65001 >nul

REM ========================================
REM   Hermes Desktop - Silent Start
REM ========================================

REM [1/3] 清理旧进程
taskkill /F /IM node.exe >nul 2>&1
taskkill /F /IM electron.exe >nul 2>&1
wsl pkill -9 -f "python main.py" >nul 2>&1
timeout /t 2 /nobreak >nul

REM [2/3] 创建 VBScript 来隐藏启动服务
set "START_VBS=%TEMP%\hermes-start.vbs"
echo Set WshShell = CreateObject("WScript.Shell") > "%START_VBS%"
echo WshShell.Run "cmd /c wsl -e bash -c ""cd /mnt/d/soso/projects/hermes-desktop/backend && .venv/bin/python main.py""", 0, False >> "%START_VBS%"
echo WScript.Sleep 3000 >> "%START_VBS%"
echo WshShell.Run "cmd /c cd /d D:\soso\projects\hermes-desktop && pnpm run dev", 0, False >> "%START_VBS%"
echo WScript.Sleep 2000 >> "%START_VBS%"

REM [3/3] 运行 VBScript（同步等待）
cscript //nologo "%START_VBS%" 2>nul
del "%START_VBS%" 2>nul

exit
