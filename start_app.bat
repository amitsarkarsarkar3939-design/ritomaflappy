@echo off
cd /d "%~dp0"
py -3 run_app.py
if errorlevel 1 (
  echo.
  echo Could not start Collect Ricoins. Make sure Python 3 is installed.
  pause
)
