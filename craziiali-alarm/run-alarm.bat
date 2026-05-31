@echo off
REM Run the alarm agent in a visible window (for testing / first run)
cd /d "%~dp0"
python agent.py
pause
