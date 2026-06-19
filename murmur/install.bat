@echo off
REM ============================================================
REM  Murmur - one-time setup for Windows
REM  Creates a local virtual environment and installs everything.
REM ============================================================
setlocal
cd /d "%~dp0"

echo.
echo   Setting up Murmur...
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo   [!] Python was not found on your PATH.
  echo       Install Python 3.10+ from https://www.python.org/downloads/
  echo       and tick "Add python.exe to PATH" during setup.
  echo.
  pause
  exit /b 1
)

if not exist ".venv" (
  echo   Creating virtual environment (.venv)...
  python -m venv .venv
)

call .venv\Scripts\activate.bat

echo   Upgrading pip...
python -m pip install --upgrade pip >nul

echo   Installing dependencies (this can take a few minutes the first time)...
pip install -r requirements.txt

echo.
echo   Done. Launch Murmur any time with:  run.bat
echo.
pause
