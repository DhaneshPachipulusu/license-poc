#!/usr/bin/env python3
"""
MINIMAL LICENSE VALIDATOR FOR DOCKER CONTAINER
===============================================
This runs inside the Docker container on startup.
Validates:
1. Certificate exists
2. Fingerprint matches (reads saved fingerprint, not generates new)
3. Signature is valid
4. Not expired

If valid → starts the app
If invalid → shows error page / exits
"""

import os
import sys
import json
import hashlib
import hmac
import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple, Optional

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("ERROR: cryptography package not installed")
    print("Run: pip install cryptography")
    sys.exit(1)


# ===========================================
# CONFIGURATION
# ===========================================

LICENSE_PATH = Path(os.environ.get("LICENSE_PATH", "/var/license"))
GRACE_DAYS = int(os.environ.get("GRACE_DAYS", "7"))
SERVICE_NAME = os.environ.get("SERVICE_NAME", "frontend")


# ===========================================
# VALIDATION RESULT
# ===========================================

class ValidationResult:
    """License validation result"""
    
    def __init__(self, valid: bool, reason: str, details: dict = None):
        self.valid = valid
        self.reason = reason
        self.details = details or {}
    
    def __str__(self):
        status = "✓ VALID" if self.valid else "✗ INVALID"
        return f"{status}: {self.reason}"


# ===========================================
# LICENSE VALIDATOR
# ===========================================

class LicenseValidator:
    """Minimal license validator for container startup"""
    
    def __init__(self, license_path: Path = LICENSE_PATH):
        self.license_path = license_path
        self.cert_file = license_path / "certificate.json"
        self.key_file = license_path / "public_key.pem"
        self.machine_id_file = license_path / "machine_id.json"
    
    def validate(self) -> ValidationResult:
        """
        Validate license.
        
        Returns ValidationResult with:
        - valid: True/False
        - reason: Why valid/invalid
        - details: Additional info
        """
        
        # Step 1: Check certificate file exists
        if not self.cert_file.exists():
            return ValidationResult(
                False, 
                "not_activated",
                {"message": "License not activated. Please run the installer."}
            )
        
        # Step 2: Load certificate
        try:
            with open(self.cert_file, "r") as f:
                certificate = json.load(f)
        except Exception as e:
            return ValidationResult(
                False,
                "certificate_corrupt",
                {"message": f"Cannot read certificate: {e}"}
            )
        
        # Step 3: Check machine fingerprint
        fingerprint_result = self._validate_fingerprint(certificate)
        if not fingerprint_result.valid:
            return fingerprint_result
        
        # Step 4: Verify signature
        signature_result = self._validate_signature(certificate)
        if not signature_result.valid:
            return signature_result
        
        # Step 5: Check expiry
        expiry_result = self._validate_expiry(certificate)
        if not expiry_result.valid:
            return expiry_result
        
        # Step 6: Check service permission
        service_result = self._validate_service(certificate, SERVICE_NAME)
        if not service_result.valid:
            return service_result
        
        # All checks passed
        return ValidationResult(
            True,
            "valid",
            {
                "customer": certificate["customer"]["customer_name"],
                "tier": certificate["tier"],
                "valid_until": certificate["validity"]["valid_until"],
                "services": [s for s, c in certificate.get("docker", {}).get("services", {}).items() if c.get("enabled")]
            }
        )
    
    def _validate_fingerprint(self, certificate: dict) -> ValidationResult:
        """Validate machine fingerprint matches"""
        
        # Load saved fingerprint
        if not self.machine_id_file.exists():
            return ValidationResult(
                False,
                "machine_id_missing",
                {"message": "Machine ID file not found. Please re-run installer."}
            )
        
        try:
            with open(self.machine_id_file, "r") as f:
                machine_data = json.load(f)
                saved_fingerprint = machine_data.get("fingerprint", "")
        except:
            return ValidationResult(
                False,
                "machine_id_corrupt",
                {"message": "Cannot read machine ID file."}
            )
        
        # Get fingerprint from certificate
        cert_fingerprint = certificate.get("machine", {}).get("machine_fingerprint", "")
        
        if not cert_fingerprint:
            return ValidationResult(
                False,
                "cert_fingerprint_missing",
                {"message": "Certificate does not contain machine fingerprint."}
            )
        
        if saved_fingerprint != cert_fingerprint:
            return ValidationResult(
                False,
                "fingerprint_mismatch",
                {"message": "This license is not valid for this machine."}
            )
        
        return ValidationResult(True, "fingerprint_ok")
    
    def _validate_signature(self, certificate: dict) -> ValidationResult:
        """Verify RSA signature"""
        
        if not self.key_file.exists():
            return ValidationResult(
                False,
                "public_key_missing",
                {"message": "Public key not found. Please re-run installer."}
            )
        
        try:
            # Load public key
            with open(self.key_file, "rb") as f:
                public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            
            # Extract signature
            signature = base64.b64decode(certificate["signature"])
            
            # Rebuild certificate without signature for verification
            cert_copy = certificate.copy()
            cert_copy.pop("signature", None)
            cert_copy.pop("signature_timestamp", None)
            
            cert_bytes = json.dumps(cert_copy, sort_keys=True).encode()
            
            # Verify signature
            public_key.verify(
                signature,
                cert_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA512()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA512()
            )
            
            return ValidationResult(True, "signature_ok")
            
        except Exception as e:
            return ValidationResult(
                False,
                "invalid_signature",
                {"message": f"License signature is invalid: {e}"}
            )
    
    def _validate_expiry(self, certificate: dict) -> ValidationResult:
        """Check if license has expired"""
        
        validity = certificate.get("validity", {})
        valid_until_str = validity.get("valid_until")
        
        if not valid_until_str:
            return ValidationResult(
                False,
                "no_expiry_date",
                {"message": "Certificate has no expiry date."}
            )
        
        try:
            # Parse expiry date
            valid_until_str = valid_until_str.replace("Z", "+00:00")
            valid_until = datetime.fromisoformat(valid_until_str)
            now = datetime.now(timezone.utc)
            
            if now <= valid_until:
                # Still valid
                days_remaining = (valid_until - now).days
                return ValidationResult(
                    True,
                    "not_expired",
                    {"days_remaining": days_remaining, "valid_until": valid_until_str}
                )
            
            # Check grace period
            grace_days = validity.get("grace_period_days", GRACE_DAYS)
            grace_until = valid_until + timedelta(days=grace_days)
            
            if now <= grace_until:
                # In grace period
                grace_days_left = (grace_until - now).days
                return ValidationResult(
                    True,
                    "grace_period",
                    {
                        "message": f"License expired but within {grace_days}-day grace period.",
                        "grace_days_left": grace_days_left
                    }
                )
            
            # Fully expired
            return ValidationResult(
                False,
                "expired",
                {
                    "message": "License has expired. Please renew.",
                    "expired_on": valid_until_str
                }
            )
            
        except Exception as e:
            return ValidationResult(
                False,
                "expiry_check_failed",
                {"message": f"Cannot check expiry: {e}"}
            )
    
    def _validate_service(self, certificate: dict, service_name: str) -> ValidationResult:
        """Check if this service is allowed"""
        
        if not service_name:
            return ValidationResult(True, "no_service_check")
        
        docker_config = certificate.get("docker", {})
        services = docker_config.get("services", {})
        
        service_config = services.get(service_name)
        
        if not service_config:
            return ValidationResult(
                False,
                "service_not_found",
                {"message": f"Service '{service_name}' not found in license."}
            )
        
        if not service_config.get("enabled"):
            tier = certificate.get("tier", "unknown")
            return ValidationResult(
                False,
                "service_not_allowed",
                {"message": f"Service '{service_name}' is not included in your {tier} license."}
            )
        
        return ValidationResult(True, "service_ok")


# ===========================================
# ERROR PAGE SERVER
# ===========================================

def serve_error_page(result: ValidationResult, port: int = 3005):
    """Serve an error page when license is invalid"""
    
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    error_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>License Error</title>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: white;
                min-height: 100vh;
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
                backdrop-filter: blur(10px);
                max-width: 500px;
            }}
            .icon {{
                font-size: 80px;
                margin-bottom: 20px;
            }}
            h1 {{
                color: #ff6b6b;
                margin-bottom: 10px;
            }}
            .reason {{
                background: rgba(255,107,107,0.2);
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                font-family: monospace;
            }}
            .message {{
                color: #ccc;
                margin: 20px 0;
            }}
            .contact {{
                margin-top: 30px;
                color: #888;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">🔒</div>
            <h1>License Error</h1>
            <div class="reason">{result.reason.upper().replace('_', ' ')}</div>
            <p class="message">{result.details.get('message', 'Please contact support.')}</p>
            <div class="contact">
                Contact support if you believe this is an error.
            </div>
        </div>
    </body>
    </html>
    """
    
    class ErrorHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(error_html.encode())
        
        def log_message(self, format, *args):
            pass  # Suppress logging
    
    print(f"Serving error page on port {port}")
    server = HTTPServer(('0.0.0.0', port), ErrorHandler)
    server.serve_forever()


# ===========================================
# MAIN
# ===========================================

def main():
    """Main entry point for container startup"""
    
    print("=" * 60)
    print("LICENSE VALIDATION")
    print("=" * 60)
    print(f"License path: {LICENSE_PATH}")
    print(f"Service: {SERVICE_NAME}")
    print()
    
    validator = LicenseValidator()
    result = validator.validate()
    
    print(f"Result: {result}")
    
    if result.valid:
        print()
        print("=" * 60)
        print("✓ LICENSE VALID - Starting application...")
        print("=" * 60)
        
        if result.details:
            print(f"  Customer: {result.details.get('customer', 'N/A')}")
            print(f"  Tier: {result.details.get('tier', 'N/A')}")
            print(f"  Services: {result.details.get('services', [])}")
        
        print()
        
        # Exit with success - Docker will continue to CMD
        sys.exit(0)
    
    else:
        print()
        print("=" * 60)
        print("✗ LICENSE INVALID")
        print("=" * 60)
        print(f"  Reason: {result.reason}")
        print(f"  Message: {result.details.get('message', 'Unknown error')}")
        print()
        
        # Check if we should serve error page or just exit
        serve_page = os.environ.get("SERVE_ERROR_PAGE", "true").lower() == "true"
        
        if serve_page:
            port = int(os.environ.get("PORT", "3005"))
            serve_error_page(result, port)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()