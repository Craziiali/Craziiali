@echo off
REM ==== CRAZIIALI Alarm Agent — one-time installer ====
echo.
echo Installing the alarm agent dependencies...
echo.

REM Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
  echo [!] Python is not installed or not on PATH.
  echo     Install Python 3 from https://www.python.org/downloads/
  echo     IMPORTANT: tick "Add python.exe to PATH" during install.
  echo.
  pause
  exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r "%~dp0requirements.txt"

echo.
echo ============================================================
echo  Done. Next:
echo   1) Put serviceAccountKey.json in this folder (README Step 3)
echo   2) Double-click  run-alarm.bat  to test it
echo   3) Run  install-autostart.bat  so it starts with Windows
echo ============================================================
echo.
pause
