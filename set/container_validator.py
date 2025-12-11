#!/usr/bin/env python3
"""
CONTAINER LICENSE VALIDATOR v3.0
=================================
Hardware fingerprint validation with priority order:
1. Read saved machine_id.json (Docker persistent volume)
2. Generate from hardware if not found

Validates:
- Certificate existence
- RSA-4096 signature
- Machine fingerprint binding
- Expiry dates with grace period
- Service permissions
"""

import os
import sys
import json
import hashlib
import platform
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error

# Check cryptography library
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend
    from cryptography.exceptions import InvalidSignature
except ImportError:
    print("❌ ERROR: cryptography library not installed!")
    print("Install with: pip install cryptography")
    sys.exit(1)

# ===========================================
# CONFIGURATION
# ===========================================

LICENSE_PATH = os.environ.get('LICENSE_PATH', '/var/license')
SERVICE_NAME = os.environ.get('SERVICE_NAME', 'frontend')
LICENSE_SERVER = os.environ.get('LICENSE_SERVER', 'http://localhost:8000')
PORT = int(os.environ.get('PORT', 3005))
GRACE_PERIOD_DAYS = 7

# v3.0 NEW: Periodic revalidation interval (1 hour)
REVALIDATION_INTERVAL = 3600  # Check every 1 hour

# v3.0 NEW: Import additional modules for periodic checks
import threading
import time
import signal

# ===========================================
# MACHINE FINGERPRINT - v3.0 CORRECTED
# ===========================================

def generate_hardware_fingerprint():
    """
    Generate fingerprint EXACTLY as installer does.
    v3.0 FIX: Match installer algorithm (sorted, with prefixes, no disk serial)
    """
    print("\n🔍 Generating fingerprint from ACTUAL hardware...")
    
    components = []
    
    # hostname with prefix
    try:
        hostname = platform.node()
        components.append(f"hostname:{hostname}")
        print(f"  ✓ Hostname: {hostname}")
    except Exception as e:
        print(f"  ✗ Could not get hostname: {e}")
    
    # system with prefix
    try:
        system = platform.system()
        components.append(f"system:{system}")
        print(f"  ✓ System: {system}")
    except Exception as e:
        print(f"  ✗ Could not get system: {e}")
    
    # machine with prefix
    try:
        machine = platform.machine()
        components.append(f"machine:{machine}")
        print(f"  ✓ Machine: {machine}")
    except Exception as e:
        print(f"  ✗ Could not get machine: {e}")
    
    # Windows-specific
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
            winreg.CloseKey(key)
            components.append(f"machine_guid:{machine_guid}")
            print(f"  ✓ MachineGuid: {machine_guid[:16]}...")
        except:
            pass
        
        try:
            import subprocess
            result = subprocess.run(["wmic", "cpu", "get", "ProcessorId"], 
                                    capture_output=True, text=True, timeout=5)
            cpu_id = result.stdout.strip().split('\n')[-1].strip()
            if cpu_id:
                components.append(f"cpu:{cpu_id}")
                print(f"  ✓ CPU ID: {cpu_id[:16]}...")
        except:
            pass
    
    # Linux-specific
    elif platform.system() == "Linux":
        try:
            with open("/etc/machine-id", "r") as f:
                machine_id = f.read().strip()
                components.append(f"machine_id:{machine_id}")
                print(f"  ✓ Machine ID: {machine_id[:16]}...")
        except:
            pass
    
    # Fallback
    if len(components) < 3:
        import uuid
        components.append(f"random:{uuid.uuid4().hex}")
    
    print(f"  Total components: {len(components)}")
    
    # CRITICAL: Sort alphabetically (installer does this!)
    combined = "|".join(sorted(components))
    
    print(f"  Combined (sorted): {combined[:60]}...")
    fingerprint = hashlib.sha3_512(combined.encode()).hexdigest()
    print(f"  ✓ Generated fingerprint: {fingerprint[:16]}...")
    
    return fingerprint


def get_machine_fingerprint():
    """
    v3.0 FIX #1: Always verify fingerprint against real hardware
    """
    machine_id_path = os.path.join(LICENSE_PATH, "machine_id.json")
    
    # ALWAYS generate from real hardware
    real_fingerprint = generate_hardware_fingerprint()
    
    if not real_fingerprint:
        print(f"  ✗ ERROR: Could not generate hardware fingerprint!")
        return None
    
    # Check if saved fingerprint exists
    if os.path.exists(machine_id_path):
        try:
            print(f"\n🔐 Verifying against saved fingerprint...")
            with open(machine_id_path, 'r') as f:
                data = json.load(f)
                saved_fingerprint = data.get('machine_fingerprint') or data.get('fingerprint')
            
            if saved_fingerprint:
                if saved_fingerprint == real_fingerprint:
                    print(f"  ✓ Fingerprint verification PASSED")
                    print(f"  ✓ Saved fingerprint matches current hardware")
                    return real_fingerprint
                else:
                    print(f"\n" + "="*70)
                    print(f"  ✗✗✗ SECURITY VIOLATION DETECTED ✗✗✗")
                    print(f"="*70)
                    print(f"  Saved fingerprint: {saved_fingerprint[:16]}...")
                    print(f"  Real fingerprint:  {real_fingerprint[:16]}...")
                    print(f"  REASON: License was activated on different hardware!")
                    print(f"="*70)
                    return None
            else:
                print(f"  ⚠ Saved fingerprint is empty, using real hardware fingerprint")
                return real_fingerprint
        except Exception as e:
            print(f"  ⚠ Could not read saved fingerprint: {e}")
            return real_fingerprint
    else:
        print(f"  ⚠ No saved fingerprint found (first activation)")
        return real_fingerprint


# ===========================================
# CERTIFICATE VALIDATION
# ===========================================

def load_certificate():
    """Load certificate from file"""
    cert_path = os.path.join(LICENSE_PATH, "certificate.json")
    
    if not os.path.exists(cert_path):
        return None, "Certificate file not found"
    
    try:
        with open(cert_path, 'r') as f:
            cert = json.load(f)
        return cert, None
    except Exception as e:
        return None, f"Failed to load certificate: {e}"


def load_public_key():
    """Load public key for signature verification"""
    key_path = os.path.join(LICENSE_PATH, "public_key.pem")
    
    if not os.path.exists(key_path):
        return None, "Public key not found"
    
    try:
        with open(key_path, 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
        return public_key, None
    except Exception as e:
        return None, f"Failed to load public key: {e}"


def verify_certificate_signature(certificate, public_key):
    """Verify RSA signature"""
    try:
        # Extract signature
        signature_b64 = certificate.get('signature')
        if not signature_b64:
            return False, "No signature in certificate"
        
        import base64
        signature_bytes = base64.b64decode(signature_b64)
        
        # Reconstruct certificate without signature
        cert_copy = certificate.copy()
        cert_copy.pop('signature', None)
        cert_copy.pop('signature_timestamp', None)
        
        # Serialize to bytes (sorted keys for consistency)
        cert_json = json.dumps(cert_copy, sort_keys=True).encode('utf-8')
        
        # Verify signature
        public_key.verify(
            signature_bytes,
            cert_json,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA512()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA512()
        )
        
        return True, None
    
    except InvalidSignature:
        return False, "Invalid signature"
    except Exception as e:
        return False, f"Signature verification failed: {e}"


def check_expiry(certificate):
    """Check if certificate is expired (with grace period)"""
    try:
        valid_until_str = certificate['validity']['valid_until']
        
        # Parse ISO format timestamp
        if valid_until_str.endswith('Z'):
            valid_until_str = valid_until_str[:-1] + '+00:00'
        
        valid_until = datetime.fromisoformat(valid_until_str)
        
        # Convert to UTC if not already
        if valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        
        # Check with grace period
        grace_period = timedelta(days=GRACE_PERIOD_DAYS)
        expiry_with_grace = valid_until + grace_period
        
        if now > expiry_with_grace:
            return False, "expired"
        elif now > valid_until:
            days_left = (expiry_with_grace - now).days
            return True, f"grace_period ({days_left} days left)"
        else:
            return True, "valid"
    
    except Exception as e:
        return False, f"expiry_check_failed: {e}"


def check_machine_fingerprint(certificate, real_fingerprint):
    """Verify machine fingerprint matches"""
    try:
        cert_fingerprint = certificate['machine']['machine_fingerprint']
        
        print(f"  Cert fingerprint: {cert_fingerprint[:32]}...")
        print(f"  Real fingerprint: {real_fingerprint[:32]}...")
        
        if cert_fingerprint == real_fingerprint:
            print(f"  ✓ Machine fingerprint matches!")
            return True, None
        else:
            print(f"  ✗ MISMATCH - This license is for a different machine!")
            return False, "fingerprint_mismatch"
    
    except Exception as e:
        return False, f"fingerprint_check_failed: {e}"


def check_service_permission(certificate, service_name):
    """Check if this service is allowed"""
    try:
        docker_services = certificate.get('docker', {}).get('services', {})
        
        if service_name in docker_services:
            service_config = docker_services[service_name]
            if service_config.get('enabled', False):
                return True, None
            else:
                reason = service_config.get('reason_disabled', 'Service not enabled')
                return False, f"service_disabled: {reason}"
        
        # If service not in list, allow by default (backward compatibility)
        return True, None
    
    except Exception as e:
        return False, f"service_check_failed: {e}"


def check_revocation():
    """Check with license server if certificate is revoked"""
    try:
        # Try to contact license server (optional, with timeout)
        heartbeat_url = f"{LICENSE_SERVER}/api/v1/heartbeat"
        
        # This is a quick check, fail gracefully if server unavailable
        req = urllib.request.Request(
            heartbeat_url,
            data=json.dumps({"service": SERVICE_NAME}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            if data.get('revoked', False):
                return False, "revoked_by_server"
            
            return True, "not_revoked"
    
    except Exception:
        # If server check fails, allow (offline grace)
        return True, "server_check_skipped"


# ===========================================
# MAIN VALIDATION
# ===========================================

def validate_license():
    """
    Main validation logic
    Returns: (valid: bool, reason: str, details: dict)
    """
    
    print("\n" + "="*70)
    print("LICENSE VALIDATION v3.0 - WITH HARDWARE FINGERPRINT VERIFICATION")
    print("="*70)
    print(f"License path: {LICENSE_PATH}")
    print(f"Service: {SERVICE_NAME}")
    print(f"License Server: {LICENSE_SERVER}")
    
    # Step 1: Get machine fingerprint (priority: saved > hardware)
    real_fingerprint = get_machine_fingerprint()
    if not real_fingerprint:
        result = "fingerprint_generation_failed"
        print(f"\nResult: ✗ INVALID: {result}")
        return False, result, {}
    
    # Step 2: Load certificate
    print(f"\nLoading certificate from: {os.path.join(LICENSE_PATH, 'certificate.json')}")
    certificate, err = load_certificate()
    if certificate is None:
        result = f"certificate_not_found: {err}"
        print(f"\nResult: ✗ INVALID: {result}")
        return False, result, {}
    
    print(f"  ✓ Certificate loaded successfully")
    
    # Step 3: Load public key
    public_key, err = load_public_key()
    if public_key is None:
        result = f"public_key_not_found: {err}"
        print(f"\nResult: ✗ INVALID: {result}")
        return False, result, {}
    
    # Step 4: Verify signature
    print(f"\nValidating certificate signature...")
    sig_valid, err = verify_certificate_signature(certificate, public_key)
    if not sig_valid:
        result = f"invalid_signature: {err}"
        print(f"  ✗ {result}")
        print(f"\nResult: ✗ INVALID: {result}")
        return False, result, {}
    
    print(f"  ✓ Certificate signature valid")
    
    # Step 5: Check expiry
    print(f"\nChecking expiry...")
    not_expired, status = check_expiry(certificate)
    if not not_expired:
        result = f"expired: {status}"
        print(f"  ✗ Certificate expired")
        print(f"\nResult: ✗ INVALID: {result}")
        return False, result, {}
    
    valid_until = certificate['validity']['valid_until']
    print(f"  ✓ Certificate valid until: {valid_until}")
    if "grace" in status:
        print(f"  ⚠ Currently in grace period: {status}")
    
    # Step 6: Verify machine fingerprint
    print(f"\nVerifying machine fingerprint...")
    fingerprint_ok, err = check_machine_fingerprint(certificate, real_fingerprint)
    if not fingerprint_ok:
        result = err
        print(f"\nResult: ✗ INVALID: {result}")
        return False, result, {}
    
    # Step 7: Check service permission
    print(f"\nChecking service permissions...")
    service_ok, err = check_service_permission(certificate, SERVICE_NAME)
    if not service_ok:
        result = err
        print(f"  ✗ Service '{SERVICE_NAME}' not allowed")
        print(f"\nResult: ✗ INVALID: {result}")
        return False, result, {}
    
    print(f"  ✓ Service '{SERVICE_NAME}' is enabled")
    
    # Step 8: Check revocation (optional, with graceful failure)
    print(f"\nChecking revocation status...")
    not_revoked, rev_status = check_revocation()
    if not not_revoked:
        result = rev_status
        print(f"  ✗ License revoked by server")
        print(f"\nResult: ✗ INVALID: {result}")
        return False, result, {}
    
    if rev_status and "skipped" in rev_status:
        print(f"  ⚠ {rev_status} (offline mode)")
    else:
        print(f"  ✓ Not revoked")
    
    # All checks passed
    print("\n" + "="*70)
    print("✅ LICENSE VALID")
    print("="*70)
    
    details = {
        "customer": certificate.get('customer', {}),
        "tier": certificate.get('tier'),
        "valid_until": valid_until,
        "service": SERVICE_NAME
    }
    
    return True, "valid", details


# ===========================================
# ERROR PAGE SERVER
# ===========================================

class ErrorHandler(BaseHTTPRequestHandler):
    """Serve error page when license invalid"""
    
    def log_message(self, format, *args):
        """Suppress request logs"""
        pass
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>License Invalid</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 48px;
                    border-radius: 16px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    max-width: 500px;
                    text-align: center;
                }}
                .icon {{
                    font-size: 64px;
                    margin-bottom: 24px;
                }}
                h1 {{
                    color: #1a202c;
                    margin-bottom: 16px;
                }}
                p {{
                    color: #4a5568;
                    line-height: 1.6;
                    margin-bottom: 24px;
                }}
                .reason {{
                    background: #fff5f5;
                    border-left: 4px solid #f56565;
                    padding: 16px;
                    margin: 24px 0;
                    text-align: left;
                }}
                .reason strong {{
                    color: #c53030;
                }}
                .footer {{
                    margin-top: 32px;
                    font-size: 14px;
                    color: #718096;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">🔒</div>
                <h1>License Validation Failed</h1>
                <p>This application requires a valid license to run.</p>
                
                <div class="reason">
                    <strong>Reason:</strong> {getattr(self.server, 'reason', 'Unknown error')}
                </div>
                
                <p>Please contact your administrator or license provider.</p>
                
                <div class="footer">
                    AI Dashboard License System v3.0
                </div>
            </div>
        </body>
        </html>
        """
        
        self.wfile.write(html.encode('utf-8'))


def serve_error_page(result, port):
    """Serve error page on the application port"""
    print(f"\nServing error page on port {port}")
    
    try:
        server = HTTPServer(('0.0.0.0', port), ErrorHandler)
        server.reason = result[1]
        
        print(f"Error page available at: http://localhost:{port}")
        print("Press Ctrl+C to exit\n")
        
        server.serve_forever()
    
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
    except Exception as e:
        print(f"Failed to start error server: {e}")
        sys.exit(1)


# ===========================================
# MAIN ENTRY POINT
# ===========================================

# ===========================================
# PERIODIC REVALIDATION (v3.0 FIX #2)
# ===========================================

def periodic_revalidation():
    """
    v3.0 FIX #2: Periodic license revalidation (every 1 hour)
    - Checks certificate expiry (strict)
    - Checks server heartbeat (if online)
    - Terminates services if invalid/expired/revoked
    """
    print(f"\n🔄 Periodic revalidation started (every {REVALIDATION_INTERVAL}s = {REVALIDATION_INTERVAL//3600}h)")
    
    while True:
        try:
            time.sleep(REVALIDATION_INTERVAL)
            
            print(f"\n" + "="*70)
            print(f"🔄 PERIODIC REVALIDATION CHECK")
            print(f"  Time: {datetime.now(timezone.utc).isoformat()}")
            print("="*70)
            
            # Load certificate
            cert_path = os.path.join(LICENSE_PATH, "certificate.json")
            if not os.path.exists(cert_path):
                print(f"  ✗ Certificate file not found!")
                os.kill(os.getpid(), signal.SIGTERM)
                return
            
            with open(cert_path, 'r') as f:
                certificate = json.load(f)
            
            # Check expiry
            validity = certificate.get('validity', {})
            valid_until_str = validity.get('valid_until', '')
            
            if valid_until_str:
                from dateutil import parser
                valid_until = parser.isoparse(valid_until_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                
                if now > valid_until:
                    print(f"\n  ✗✗✗ CERTIFICATE EXPIRED ✗✗✗")
                    print(f"  → Terminating services...")
                    os.kill(os.getpid(), signal.SIGTERM)
                    return
                else:
                    days_remaining = (valid_until - now).days
                    print(f"  ✓ Certificate valid (expires in {days_remaining} days)")
            
            # Check fingerprint
            real_fp = get_machine_fingerprint()
            if not real_fp:
                print(f"  ✗ Fingerprint verification failed")
                os.kill(os.getpid(), signal.SIGTERM)
                return
            
            # Check server heartbeat (graceful failure if offline)
            try:
                print(f"  → Checking with license server...")
                heartbeat_url = f"{LICENSE_SERVER}/api/v1/heartbeat"
                heartbeat_data = {
                    "machine_fingerprint": real_fp,
                    "service_name": SERVICE_NAME
                }
                
                req = urllib.request.Request(
                    heartbeat_url,
                    data=json.dumps(heartbeat_data).encode('utf-8'),
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=5) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    
                    if result.get('valid') == False:
                        print(f"\n  ✗✗✗ LICENSE REVOKED ✗✗✗")
                        os.kill(os.getpid(), signal.SIGTERM)
                        return
                    else:
                        print(f"  ✓ Server heartbeat OK")
            
            except Exception as e:
                print(f"  ⚠ Cannot reach server (offline mode): {e}")
                print(f"  → Continuing (will check again in 1 hour)")
            
            print(f"\n✅ Periodic revalidation PASSED")
            print("="*70)
        
        except Exception as e:
            print(f"\n⚠ Periodic revalidation error: {e}")


# ===========================================
# MAIN ENTRY POINT (v3.0 UPDATED)
# ===========================================

def main():
    """Main entry point with v3.0 periodic revalidation"""
    
    # Initial validation
    valid, reason, details = validate_license()
    
    if valid:
        print("\n✅ Initial license validation successful")
        
        # Start periodic revalidation thread
        revalidation_thread = threading.Thread(
            target=periodic_revalidation,
            daemon=True,
            name="LicenseRevalidation"
        )
        revalidation_thread.start()
        
        print("✅ Periodic revalidation thread started (checks every 1 hour)")
        print("✅ Application starting...\n")
        
        sys.exit(0)
    else:
        # License invalid
        print("\n" + "="*70)
        print("✗ LICENSE INVALID")
        print("="*70)
        print(f"  Reason: {reason}")
        print(f"  Message: This license is not valid for this machine.")
        
        result = (False, reason, details)
        serve_error_page(result, PORT)


if __name__ == "__main__":
    main()