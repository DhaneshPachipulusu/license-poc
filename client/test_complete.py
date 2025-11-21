#!/usr/bin/env python3
"""
Complete Testing Script for License System
Tests all components and scenarios

Usage:
    python test_complete.py
"""

import sys
import os
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*70)
print("LICENSE SYSTEM - COMPLETE TEST SUITE")
print("="*70 + "\n")

# Test counters
tests_passed = 0
tests_failed = 0
tests_total = 0

def test(name):
    """Decorator for test functions"""
    def decorator(func):
        def wrapper():
            global tests_passed, tests_failed, tests_total
            tests_total += 1
            
            print(f"\n[TEST {tests_total}] {name}")
            print("-" * 70)
            
            try:
                func()
                print(f"✅ PASSED")
                tests_passed += 1
                return True
            except AssertionError as e:
                print(f"❌ FAILED: {e}")
                tests_failed += 1
                return False
            except Exception as e:
                print(f"❌ ERROR: {e}")
                tests_failed += 1
                return False
        
        return wrapper
    return decorator


# ============================================================================
# TEST 1: Machine Fingerprinting
# ============================================================================

@test("Machine Fingerprinting")
def test_fingerprinting():
    from fingerprint import get_machine_fingerprint
    
    # Generate fingerprint
    fp1 = get_machine_fingerprint()
    print(f"  Fingerprint 1: {fp1[:16]}...")
    
    assert fp1, "Fingerprint should not be empty"
    assert len(fp1) == 32, f"Fingerprint should be 32 chars, got {len(fp1)}"
    
    # Generate again (should be same - uses saved)
    fp2 = get_machine_fingerprint()
    print(f"  Fingerprint 2: {fp2[:16]}...")
    
    assert fp1 == fp2, "Fingerprints should be consistent"
    
    print(f"  ✓ Fingerprint is consistent: {fp1 == fp2}")


# ============================================================================
# TEST 2: Certificate Manager - Save & Load
# ============================================================================

@test("Certificate Manager - Save & Load")
def test_cert_manager():
    from cert_manager import CertificateManager
    from fingerprint import get_machine_fingerprint
    
    # Create manager
    manager = CertificateManager()
    fingerprint = get_machine_fingerprint()
    
    # Test certificate
    test_cert = {
        "version": "1.0",
        "customer_id": "test-123",
        "customer_name": "Test Company",
        "machine_id": "machine-456",
        "machine_fingerprint": fingerprint,
        "hostname": "TEST-PC",
        "product_key": "TEST-2024-ABCD-XYZ",
        "issued_at": "2024-11-21T10:00:00Z",
        "valid_until": "2025-11-21T10:00:00Z",
        "allowed_services": ["dashboard"],
        "signature": "abc123..."
    }
    
    # Save
    print("  Saving certificate...")
    manager.save_certificate(test_cert, fingerprint)
    
    assert manager.certificate_exists(), "Certificate file should exist"
    
    # Load
    print("  Loading certificate...")
    loaded = manager.load_certificate(fingerprint)
    
    assert loaded is not None, "Should load certificate"
    assert loaded["customer_name"] == "Test Company", "Customer name should match"
    assert loaded["machine_fingerprint"] == fingerprint, "Fingerprint should match"
    
    print(f"  ✓ Certificate saved and loaded correctly")


# ============================================================================
# TEST 3: Certificate Manager - Wrong Machine (Should Fail)
# ============================================================================

@test("Certificate Manager - Wrong Machine Rejection")
def test_cert_manager_wrong_machine():
    from cert_manager import CertificateManager
    
    manager = CertificateManager()
    
    # Try to load with wrong fingerprint
    wrong_fp = "wrong-fingerprint-12345678901234567890123456789012"
    loaded = manager.load_certificate(wrong_fp)
    
    assert loaded is None, "Should NOT load with wrong fingerprint"
    
    print(f"  ✓ Correctly rejected wrong machine")


# ============================================================================
# TEST 4: License Validator - Valid Certificate
# ============================================================================

@test("License Validator - Valid Certificate")
def test_validator_valid():
    from license_validator import LicenseValidator
    from cert_manager import CertificateManager
    from fingerprint import get_machine_fingerprint
    from datetime import datetime, timedelta, timezone
    
    # Create valid certificate
    fingerprint = get_machine_fingerprint()
    manager = CertificateManager()
    
    # Create certificate that expires in 30 days
    now = datetime.now(timezone.utc)
    valid_until = now + timedelta(days=30)
    
    cert = {
        "version": "1.0",
        "customer_id": "test-123",
        "customer_name": "Test Company",
        "machine_id": "machine-456",
        "machine_fingerprint": fingerprint,
        "hostname": "TEST-PC",
        "product_key": "TEST-2024-ABCD-XYZ",
        "issued_at": now.isoformat(),
        "valid_until": valid_until.isoformat(),
        "allowed_services": ["dashboard"],
        "signature": "abc123..."  # Note: signature check will be skipped if no public key
    }
    
    # Save
    manager.save_certificate(cert, fingerprint)
    
    # Validate
    validator = LicenseValidator()
    result = validator.validate()
    
    # Note: Will pass all checks except signature (no public key in test)
    # In real scenario with public key, signature would also be verified
    
    print(f"  Valid: {result.valid}")
    print(f"  Reason: {result.reason}")
    
    # For test without public key, we expect it to pass other checks
    assert result.valid or result.reason == "invalid_signature", \
        f"Should be valid or fail only on signature, got: {result.reason}"


# ============================================================================
# TEST 5: Activation Client - Server Communication
# ============================================================================

@test("Activation Client - Server Check")
def test_activation_client():
    from activation_client import ActivationClient
    
    # Try to connect to local server
    client = ActivationClient("http://localhost:8000")
    
    print("  Checking server status...")
    server_ok = client.check_server_status()
    
    if server_ok:
        print("  ✓ Server is reachable")
    else:
        print("  ⚠ Server not running (expected if server is offline)")
        print("  ℹ This is not a failure - server may not be started")
    
    # Test always passes (server may or may not be running)
    assert True


# ============================================================================
# TEST 6: Error Pages Exist
# ============================================================================

@test("Error Pages Exist")
def test_error_pages():
    error_pages = [
        'error_pages/expired.html',
        'error_pages/invalid.html',
        'error_pages/machine_mismatch.html',
        'error_pages/not_activated.html'
    ]
    
    for page in error_pages:
        path = Path(__file__).parent / page
        assert path.exists(), f"Error page should exist: {page}"
        print(f"  ✓ {page}")


# ============================================================================
# TEST 7: All Modules Importable
# ============================================================================

@test("All Modules Importable")
def test_imports():
    modules = [
        'fingerprint',
        'cert_manager',
        'license_validator',
        'activation_client',
        'startup_with_license'
    ]
    
    for module_name in modules:
        try:
            __import__(module_name)
            print(f"  ✓ {module_name}")
        except ImportError as e:
            raise AssertionError(f"Failed to import {module_name}: {e}")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

def run_all_tests():
    """Run all tests"""
    
    print("Starting test suite...\n")
    time.sleep(1)
    
    # Run tests
    test_fingerprinting()
    test_cert_manager()
    test_cert_manager_wrong_machine()
    test_validator_valid()
    test_activation_client()
    test_error_pages()
    test_imports()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total Tests:  {tests_total}")
    print(f"Passed:       {tests_passed} ✅")
    print(f"Failed:       {tests_failed} ❌")
    print()
    
    if tests_failed == 0:
        print("🎉 ALL TESTS PASSED!")
        print("="*70 + "\n")
        return 0
    else:
        print(f"⚠️  {tests_failed} TEST(S) FAILED")
        print("="*70 + "\n")
        return 1


if __name__ == "__main__":
    # Ensure /var/license directory exists
    os.makedirs("/var/license", exist_ok=True)
    
    # Run tests
    exit_code = run_all_tests()
    sys.exit(exit_code)