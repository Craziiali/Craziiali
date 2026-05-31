@echo off
REM ==== Make the alarm agent start automatically with Windows (hidden) ====
setlocal
set "DIR=%~dp0"

REM --- Find the real pythonw.exe (no console window) ---
set "PYW="
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\pythonw.exe" set "PYW=%%D\pythonw.exe"
if not defined PYW for /d %%D in ("%PROGRAMFILES%\Python3*") do if exist "%%D\pythonw.exe" set "PYW=%%D\pythonw.exe"
if not defined PYW set "PYW=pythonw"

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS=%STARTUP%\CraziialiAlarm.vbs"

> "%VBS%" echo Set sh = CreateObject("WScript.Shell")
>> "%VBS%" echo sh.CurrentDirectory = "%DIR%"
>> "%VBS%" echo sh.Run """%PYW%"" ""%DIR%agent.py""", 0, False

echo.
echo [ok] Auto-start installed.
echo      The alarm agent will now launch silently every time you log in.
echo      Starting it now...
start "" wscript "%VBS%"
echo.
echo To stop it later: open Task Manager, find "pythonw.exe", End task.
echo To remove auto-start: run  uninstall-autostart.bat
echo.
pause
