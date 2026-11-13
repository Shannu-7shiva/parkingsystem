@echo off
title Smart Parking ANPR System - Web Server
color 0A

echo =====================================================================
echo   SMART PARKING MANAGEMENT SYSTEM USING ANPR
echo =====================================================================
echo.

REM Determine Python Executable
set "PY_CMD="

if exist "venv\Scripts\python.exe" (
    echo [INFO] Activating virtual environment 'venv'...
    set "PY_CMD=venv\Scripts\python.exe"
    goto :START_SERVER
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :START_SERVER
)

py -3.12 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py -3.12"
    goto :START_SERVER
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto :START_SERVER
)

set "PY_CMD=python"

:START_SERVER
echo.
echo Starting Smart Parking Flask Server using %PY_CMD%...
echo Portal URL : http://127.0.0.1:5000
echo Username   : admin
echo Password   : admin123
echo.
echo Press Ctrl+C in this terminal window to stop the server.
echo =====================================================================
echo.

%PY_CMD% app.py

pause
