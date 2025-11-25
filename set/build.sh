#!/bin/bash
# Build script for Linux executable
# Run this on a Linux machine with Python installed

echo "========================================"
echo "Building AI Dashboard Installer"
echo "========================================"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Build executable
echo "Building executable..."
pyinstaller --onefile --name "ai-dashboard-setup" installer.py

echo ""
echo "========================================"
echo "Build complete!"
echo "Executable: dist/ai-dashboard-setup"
echo "========================================"