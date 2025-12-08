#!/bin/sh
set -e

echo "========================================"
echo "AI Dashboard - License Validation v3.0"
echo "========================================"

# Check validator exists
if [ ! -f "/app/container_validator.py" ]; then
    echo "❌ ERROR: Validator not found!"
    exit 1
fi

# Check Python available
if ! command -v python3 > /dev/null; then
    echo "❌ ERROR: Python not installed!"
    exit 1
fi

echo "🔍 Running license validation..."
echo ""

# Run validator (exits with code 1 if invalid)
python3 /app/container_validator.py

# If we reach here, validation passed
VALIDATOR_EXIT=$?
if [ $VALIDATOR_EXIT -ne 0 ]; then
    echo "❌ License validation failed!"
    exit 1
fi

echo ""
echo "✅ License valid - Starting application..."
echo "========================================"

# Start the application
exec "$@"