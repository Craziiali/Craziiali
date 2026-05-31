@echo off
REM Run the alarm agent in a visible window (for testing / first run)
cd /d "%~dp0"

REM --- Find the real Python (avoid the Windows Store stub) ---
set "PYEXE="
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
if not defined PYEXE for /d %%D in ("%PROGRAMFILES%\Python3*") do if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
if not defined PYEXE set "PYEXE=python"

"%PYEXE%" agent.py
pause
