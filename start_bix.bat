@echo off
cd /d "%~dp0"
py -3 terminal.py
if errorlevel 1 (
  echo.
  echo Bix could not start. Make sure Python 3 is installed.
  pause
)
