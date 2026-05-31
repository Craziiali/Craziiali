@echo off
REM ==== Remove the alarm agent from Windows auto-start ====
set "VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\CraziialiAlarm.vbs"
if exist "%VBS%" (
  del "%VBS%"
  echo [ok] Auto-start removed.
) else (
  echo Nothing to remove ^(auto-start was not installed^).
)
echo.
echo Note: if the agent is currently running, end "pythonw.exe" in Task Manager.
echo.
pause
