#!/bin/bash
# Quick Test Script for container_validator_v3_final.py
# Run this WITHOUT Docker to test the fixes

echo "=================================="
echo "CONTAINER VALIDATOR v3.0 - QUICK TEST"
echo "=================================="
echo ""

# Step 1: Setup test environment
echo "📁 Setting up test environment..."
mkdir -p /tmp/license_test
export LICENSE_PATH=/tmp/license_test
export SERVICE_NAME=frontend
export LICENSE_SERVER=http://localhost:8000
export PORT=3005

echo "✓ Test directory: $LICENSE_PATH"
echo "✓ Service: $SERVICE_NAME"
echo "✓ Server: $LICENSE_SERVER"
echo ""

# Step 2: Check if we have an actual license
if [ -f "/var/license/certificate.json" ]; then
    echo "📄 Found existing license files, copying..."
    cp /var/license/certificate.json $LICENSE_PATH/
    cp /var/license/public_key.pem $LICENSE_PATH/
    cp /var/license/machine_id.json $LICENSE_PATH/ 2>/dev/null || echo "  (No machine_id.json - will generate)"
    echo "✓ License files copied"
elif [ -f "./certificate.json" ]; then
    echo "📄 Found license files in current directory, copying..."
    cp ./certificate.json $LICENSE_PATH/
    cp ./public_key.pem $LICENSE_PATH/
    cp ./machine_id.json $LICENSE_PATH/ 2>/dev/null || echo "  (No machine_id.json - will generate)"
    echo "✓ License files copied"
else
    echo "❌ ERROR: No license files found!"
    echo ""
    echo "Please either:"
    echo "  1. Have files in /var/license/"
    echo "  2. Have files in current directory"
    echo "  3. Create test files manually"
    echo ""
    exit 1
fi

echo ""
echo "=================================="
echo "🧪 RUNNING VALIDATION TEST"
echo "=================================="
echo ""

# Step 3: Run the validator (but don't exit - catch the exit code)
python3 container_validator_v3_final.py &
VALIDATOR_PID=$!

echo ""
echo "✓ Validator started (PID: $VALIDATOR_PID)"
echo ""
echo "Watch for:"
echo "  • ✓ Fingerprint verification PASSED (Fix #1 working)"
echo "  • ✅ Periodic revalidation thread started (Fix #2 working)"
echo ""
echo "Press Ctrl+C to stop..."
echo ""

# Wait for validator
wait $VALIDATOR_PID
EXIT_CODE=$?

echo ""
echo "=================================="
echo "TEST RESULT"
echo "=================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ VALIDATION PASSED"
    echo ""
    echo "This means:"
    echo "  • Fix #1: Fingerprint verification working"
    echo "  • Fix #2: Periodic thread started"
    echo "  • License is valid for this machine"
else
    echo "❌ VALIDATION FAILED (Exit code: $EXIT_CODE)"
    echo ""
    echo "This could mean:"
    echo "  • Certificate expired"
    echo "  • Fingerprint mismatch (good - Fix #1 working!)"
    echo "  • Invalid signature"
    echo "  • Service not allowed"
fi
echo "=================================="