@echo off
REM Quick Start Script for Phase 1 (Windows)

echo ==================================
echo PHASE 1 - QUICK START
echo ==================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

python --version
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo.

REM Initialize database
echo Initializing database...
python -c "from db import init_db; init_db()"
echo Database initialized with sample data
echo.

echo ==================================
echo Setup Complete!
echo ==================================
echo.
echo To start the server:
echo   python server.py
echo.
echo Server will run at: http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo.
echo Sample product key for testing: TEST-2024-DEMO-ABC
echo.
pause