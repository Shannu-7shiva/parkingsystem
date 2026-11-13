@echo off
title Smart Parking ANPR System - Setup
color 0B

echo =====================================================================
echo   SMART PARKING MANAGEMENT SYSTEM USING ANPR
echo   Automated Environment Setup Script (Windows)
echo =====================================================================
echo.

REM Determine Python Executable
set "BASE_PY="

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "BASE_PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :CHECK_VENV
)

py -3.12 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "BASE_PY=py -3.12"
    goto :CHECK_VENV
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "BASE_PY=python"
    goto :CHECK_VENV
)

color 0C
echo [ERROR] Python 3.11+ is not found!
echo Please ensure Python is installed.
pause
exit /b 1

:CHECK_VENV
echo [1/4] Checking Python Virtual Environment using %BASE_PY%...
if not exist "venv" (
    echo Creating virtual environment 'venv'...
    %BASE_PY% -m venv venv
) else (
    echo Virtual environment 'venv' already exists.
)

echo.
echo [2/4] Activating Virtual Environment and Installing Dependencies...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    %BASE_PY% -m pip install -r requirements.txt
)

echo.
echo [3/4] Initializing Database and Seeding Sample Data...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe database\seed.py
) else (
    %BASE_PY% database\seed.py
)

echo.
echo [4/4] Verifying Test Suite...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -m unittest discover tests
) else (
    %BASE_PY% -m unittest discover tests
)

echo.
echo =====================================================================
echo   SETUP COMPLETED SUCCESSFULLY!
echo =====================================================================
echo.
echo   To launch the server:
echo     Double click 'run.bat'
echo.
echo   Default Admin Credentials:
echo     Username: admin
echo     Password: admin123
echo =====================================================================
echo.
pause
