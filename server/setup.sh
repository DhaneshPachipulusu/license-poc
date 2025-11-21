#!/bin/bash
# Quick Start Script for Phase 1

echo "=================================="
echo "PHASE 1 - QUICK START"
echo "=================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✓ Python found: $(python3 --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt
echo ""

# Initialize database
echo "🗄️  Initializing database..."
python3 -c "from db import init_db; init_db()"
echo "✓ Database initialized with sample data"
echo ""

echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "To start the server:"
echo "  python3 server.py"
echo ""
echo "Server will run at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo ""
echo "Sample product key for testing: TEST-2024-DEMO-ABC"
echo ""setup.sh
