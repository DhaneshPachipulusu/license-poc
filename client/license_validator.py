"""
License Validator
Validates licenses offline without internet connection

Features:
- Offline validation (no server required)
- Signature verification
- Expiry checking
- Machine fingerprint matching
- Grace period support

Usage:
    from license_validator import LicenseValidator
    
    validator = LicenseValidator()
    result = validator.validate()
    
    if result.valid:
        start_application()
    else:
        show_error(result.reason, result.details)
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

from fingerprint import get_machine_fingerprint
from cert_manager import CertificateManager


@dataclass
class ValidationResult:
    """Result of license validation"""
    valid: bool
    reason: str
    details: Optional[Dict] = None
    certificate: Optional[Dict] = None


class LicenseValidator:
    """Validates license certificates offline"""
    
    def __init__(
        self,
        cert_dir: str = "/var/license",
        grace_days: int = 7
    ):
        """
        Initialize validator
        
        Args:
            cert_dir: Directory containing certificate
            grace_days: Grace period after expiry (default 7 days)
        """
        self.cert_manager = CertificateManager(cert_dir)
        self.grace_days = grace_days
        self.machine_fingerprint = None
    
    def validate(self) -> ValidationResult:
        """
        Validate license certificate
        
        Checks (in order):
        1. Certificate exists
        2. Can decrypt (machine match)
        3. Signature valid
        4. Not expired (with grace period)
        5. Fingerprint matches
        
        Returns:
            ValidationResult with status and details
        """
        
        print("\n" + "="*70)
        print("LICENSE VALIDATION")
        print("="*70 + "\n")
        
        # Step 1: Check if certificate exists
        if not self.cert_manager.certificate_exists():
            print("✗ No certificate found")
            return ValidationResult(
                valid=False,
                reason="not_activated",
                details={
                    "message": "License not activated",
                    "action": "Please activate with product key"
                }
            )
        
        print("✓ Certificate file found")
        
        # Step 2: Get machine fingerprint
        self.machine_fingerprint = get_machine_fingerprint()
        print(f"✓ Machine fingerprint: {self.machine_fingerprint[:16]}...")
        
        # Step 3: Load and decrypt certificate
        certificate = self.cert_manager.load_certificate(self.machine_fingerprint)
        
        if not certificate:
            print("✗ Failed to decrypt certificate")
            return ValidationResult(
                valid=False,
                reason="machine_mismatch",
                details={
                    "message": "License is bound to a different machine",
                    "action": "This certificate cannot be used on this machine"
                }
            )
        
        print("✓ Certificate decrypted successfully")
        
        # Step 4: Verify fingerprint match (double check)
        cert_fingerprint = certificate.get('machine_fingerprint')
        if cert_fingerprint != self.machine_fingerprint:
            print(f"✗ Fingerprint mismatch")
            print(f"  Cert: {cert_fingerprint[:16]}...")
            print(f"  This: {self.machine_fingerprint[:16]}...")
            return ValidationResult(
                valid=False,
                reason="fingerprint_mismatch",
                details={
                    "message": "Machine fingerprint does not match",
                    "cert_fingerprint": cert_fingerprint[:16] + "...",
                    "current_fingerprint": self.machine_fingerprint[:16] + "..."
                },
                certificate=certificate
            )
        
        print("✓ Fingerprint matches")
        
        # Step 5: Verify signature
        public_key_pem = self.cert_manager.load_public_key()
        
        if not public_key_pem:
            print("⚠ Warning: Public key not found, skipping signature verification")
        else:
            signature_valid = self._verify_signature(certificate, public_key_pem)
            
            if not signature_valid:
                print("✗ Invalid signature")
                return ValidationResult(
                    valid=False,
                    reason="invalid_signature",
                    details={
                        "message": "Certificate signature is invalid",
                        "action": "Certificate may be corrupted or tampered"
                    },
                    certificate=certificate
                )
            
            print("✓ Signature valid")
        
        # Step 6: Check expiry
        expiry_status = self._check_expiry(certificate)
        
        if expiry_status == "expired":
            print("✗ Certificate expired")
            valid_until = certificate.get('valid_until', 'unknown')
            return ValidationResult(
                valid=False,
                reason="expired",
                details={
                    "message": "License has expired",
                    "valid_until": valid_until,
                    "action": "Please renew your license"
                },
                certificate=certificate
            )
        elif expiry_status == "grace_period":
            days_left = self._get_grace_days_left(certificate)
            print(f"⚠ In grace period ({days_left} days left)")
        else:
            days_until_expiry = self._get_days_until_expiry(certificate)
            print(f"✓ Valid (expires in {days_until_expiry} days)")
        
        # All checks passed!
        print("\n" + "="*70)
        print("✅ LICENSE VALID")
        print("="*70 + "\n")
        
        return ValidationResult(
            valid=True,
            reason="valid",
            details={
                "customer": certificate.get('customer_name'),
                "machine": certificate.get('hostname'),
                "valid_until": certificate.get('valid_until'),
                "days_remaining": self._get_days_until_expiry(certificate),
                "services": certificate.get('allowed_services', [])
            },
            certificate=certificate
        )
    
    def _verify_signature(self, certificate: Dict, public_key_pem: str) -> bool:
        """
        Verify certificate signature with RSA public key
        
        Args:
            certificate: Certificate dict
            public_key_pem: RSA public key in PEM format
            
        Returns:
            True if signature valid
        """
        try:
            # Extract signature
            cert_copy = certificate.copy()
            signature_hex = cert_copy.pop('signature', None)
            
            if not signature_hex:
                print("  No signature found in certificate")
                return False
            
            signature = bytes.fromhex(signature_hex)
            
            # Recreate signed data (canonical JSON)
            cert_json = json.dumps(cert_copy, sort_keys=True, separators=(',', ':'))
            cert_bytes = cert_json.encode('utf-8')
            
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
            
            # Verify signature
            public_key.verify(
                signature,
                cert_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except Exception as e:
            print(f"  Signature verification failed: {e}")
            return False
    
    def _check_expiry(self, certificate: Dict) -> str:
        """
        Check if certificate is expired
        
        Returns:
            'valid', 'grace_period', or 'expired'
        """
        try:
            valid_until_str = certificate.get('valid_until')
            if not valid_until_str:
                return 'expired'
            
            # Parse expiry date
            valid_until = datetime.fromisoformat(
                valid_until_str.replace('Z', '+00:00')
            )
            
            now = datetime.now(timezone.utc)
            
            # Check if expired
            if now > valid_until:
                # Check grace period
                grace_end = valid_until + timedelta(days=self.grace_days)
                
                if now <= grace_end:
                    return 'grace_period'
                else:
                    return 'expired'
            
            return 'valid'
            
        except Exception as e:
            print(f"  Error checking expiry: {e}")
            return 'expired'
    
    def _get_days_until_expiry(self, certificate: Dict) -> int:
        """Get days until certificate expires"""
        try:
            valid_until_str = certificate.get('valid_until')
            valid_until = datetime.fromisoformat(
                valid_until_str.replace('Z', '+00:00')
            )
            
            now = datetime.now(timezone.utc)
            delta = valid_until - now
            
            return max(0, delta.days)
        except:
            return -999
    
    def _get_grace_days_left(self, certificate: Dict) -> int:
        """Get days left in grace period"""
        try:
            valid_until_str = certificate.get('valid_until')
            valid_until = datetime.fromisoformat(
                valid_until_str.replace('Z', '+00:00')
            )
            
            grace_end = valid_until + timedelta(days=self.grace_days)
            now = datetime.now(timezone.utc)
            delta = grace_end - now
            
            return max(0, delta.days)
        except:
            return 0
    
    def get_certificate_info(self) -> Optional[Dict]:
        """Get certificate information without full validation"""
        if not self.cert_manager.certificate_exists():
            return None
        
        fingerprint = get_machine_fingerprint()
        certificate = self.cert_manager.load_certificate(fingerprint)
        
        if not certificate:
            return None
        
        return {
            "customer": certificate.get('customer_name', 'Unknown'),
            "machine": certificate.get('hostname', 'Unknown'),
            "product_key": certificate.get('product_key', 'Unknown'),
            "issued_at": certificate.get('issued_at', 'Unknown'),
            "valid_until": certificate.get('valid_until', 'Unknown'),
            "days_remaining": self._get_days_until_expiry(certificate),
            "services": certificate.get('allowed_services', [])
        }


# CLI interface for testing
if __name__ == "__main__":
    print("\n" + "="*70)
    print("LICENSE VALIDATOR TEST")
    print("="*70 + "\n")
    
    validator = LicenseValidator()
    
    # Run validation
    result = validator.validate()
    
    print("\n" + "="*70)
    print("VALIDATION RESULT")
    print("="*70)
    print(f"Valid: {result.valid}")
    print(f"Reason: {result.reason}")
    
    if result.details:
        print("\nDetails:")
        for key, value in result.details.items():
            print(f"  {key}: {value}")
    
    print("\n" + "="*70)
    
    # Exit code
    exit(0 if result.valid else 1)