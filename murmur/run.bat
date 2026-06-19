@echo off
REM ============================================================
REM  Murmur - launch
REM  Run install.bat once first. Then double-click this any time.
REM ============================================================
setlocal
cd /d "%~dp0"

if not exist ".venv" (
  echo   Murmur isn't set up yet. Running install.bat first...
  call install.bat
)

call .venv\Scripts\activate.bat
python -m murmur
