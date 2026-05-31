@echo off
REM ==== Make the alarm agent start automatically with Windows (hidden) ====
setlocal
set "DIR=%~dp0"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS=%STARTUP%\CraziialiAlarm.vbs"

> "%VBS%" echo Set sh = CreateObject("WScript.Shell")
>> "%VBS%" echo sh.CurrentDirectory = "%DIR%"
>> "%VBS%" echo sh.Run "pythonw ""%DIR%agent.py""", 0, False

echo.
echo [ok] Auto-start installed.
echo      The alarm agent will now launch silently every time you log in.
echo      It is also starting now...
start "" wscript "%VBS%"
echo.
echo To stop it later: open Task Manager, find "pythonw.exe", End task.
echo To remove auto-start: run  uninstall-autostart.bat
echo.
pause
