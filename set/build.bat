@echo off
REM Build script for Windows .exe installer
REM Run this on a Windows machine with Python installed

echo ========================================
echo Building AI Dashboard Installer
echo ========================================

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Build .exe
echo Building executable...
pyinstaller --onefile --windowed --name "AI-Dashboard-Setup" --icon=icon.ico installer.py

echo.
echo ========================================
echo Build complete!
echo Executable: dist\AI-Dashboard-Setup.exe
echo ========================================

pause