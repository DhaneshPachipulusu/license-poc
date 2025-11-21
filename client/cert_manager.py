"""
Certificate Manager
Handles encrypted storage and retrieval of license certificates

Features:
- Encrypts certificate with machine fingerprint (machine-bound)
- Saves to persistent volume (survives container restarts)
- Decrypts only on matching machine
- Prevents certificate copying

Usage:
    from cert_manager import CertificateManager
    
    manager = CertificateManager()
    
    # Save certificate
    manager.save_certificate(cert_dict)
    
    # Load certificate
    cert = manager.load_certificate()
"""

import json
import os
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Paths
CERT_DIR = "/var/license"
CERT_FILE = os.path.join(CERT_DIR, "certificate.dat")
PUBLIC_KEY_FILE = os.path.join(CERT_DIR, "public_key.pem")


class CertificateManager:
    """Manages encrypted certificate storage"""
    
    def __init__(self, cert_dir: str = CERT_DIR):
        """
        Initialize certificate manager
        
        Args:
            cert_dir: Directory to store certificates
        """
        self.cert_dir = cert_dir
        self.cert_file = os.path.join(cert_dir, "certificate.dat")
        self.public_key_file = os.path.join(cert_dir, "public_key.pem")
        
        # Create directory if not exists
        os.makedirs(cert_dir, exist_ok=True)
    
    def save_certificate(
        self, 
        certificate: Dict, 
        machine_fingerprint: str,
        public_key_pem: str = None
    ):
        """
        Save certificate encrypted with machine fingerprint
        
        Args:
            certificate: Certificate dict from server
            machine_fingerprint: Current machine fingerprint
            public_key_pem: RSA public key (optional, for verification)
        """
        
        # Convert certificate to JSON
        cert_json = json.dumps(certificate, indent=2)
        cert_bytes = cert_json.encode('utf-8')
        
        # Derive encryption key from machine fingerprint
        encryption_key = self._derive_key(machine_fingerprint)
        
        # Encrypt certificate
        encrypted_data = self._encrypt(cert_bytes, encryption_key)
        
        # Save encrypted certificate
        with open(self.cert_file, 'wb') as f:
            f.write(encrypted_data)
        
        print(f"✓ Certificate saved to {self.cert_file}")
        
        # Save public key if provided
        if public_key_pem:
            with open(self.public_key_file, 'w') as f:
                f.write(public_key_pem)
            print(f"✓ Public key saved to {self.public_key_file}")
    
    def load_certificate(self, machine_fingerprint: str) -> Optional[Dict]:
        """
        Load and decrypt certificate
        
        Args:
            machine_fingerprint: Current machine fingerprint
            
        Returns:
            Certificate dict if valid, None if not found or can't decrypt
        """
        
        # Check if certificate file exists
        if not os.path.exists(self.cert_file):
            print("✗ Certificate file not found")
            return None
        
        try:
            # Read encrypted certificate
            with open(self.cert_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Derive decryption key from machine fingerprint
            decryption_key = self._derive_key(machine_fingerprint)
            
            # Decrypt certificate
            cert_bytes = self._decrypt(encrypted_data, decryption_key)
            
            # Parse JSON
            cert_json = cert_bytes.decode('utf-8')
            certificate = json.loads(cert_json)
            
            print("✓ Certificate loaded successfully")
            return certificate
            
        except Exception as e:
            print(f"✗ Failed to decrypt certificate: {e}")
            print("  (This certificate may be from a different machine)")
            return None
    
    def certificate_exists(self) -> bool:
        """Check if certificate file exists"""
        return os.path.exists(self.cert_file)
    
    def load_public_key(self) -> Optional[str]:
        """Load RSA public key"""
        try:
            if os.path.exists(self.public_key_file):
                with open(self.public_key_file, 'r') as f:
                    return f.read()
        except:
            pass
        return None
    
    def delete_certificate(self):
        """Delete certificate file (deactivation)"""
        try:
            if os.path.exists(self.cert_file):
                os.remove(self.cert_file)
                print(f"✓ Certificate deleted")
            
            if os.path.exists(self.public_key_file):
                os.remove(self.public_key_file)
                print(f"✓ Public key deleted")
        except Exception as e:
            print(f"✗ Error deleting certificate: {e}")
    
    def get_certificate_info(self) -> Optional[Dict]:
        """Get basic info about stored certificate without full decryption"""
        try:
            if not os.path.exists(self.cert_file):
                return None
            
            stat = os.stat(self.cert_file)
            return {
                'exists': True,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'path': self.cert_file
            }
        except:
            return None
    
    def _derive_key(self, fingerprint: str, salt: bytes = b'license_salt_v1') -> bytes:
        """
        Derive encryption key from machine fingerprint
        Uses PBKDF2HMAC for key derivation
        
        Args:
            fingerprint: Machine fingerprint string
            salt: Salt for key derivation
            
        Returns:
            32-byte encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(fingerprint.encode('utf-8'))
        return key
    
    def _encrypt(self, data: bytes, key: bytes) -> bytes:
        """
        Encrypt data using AES-256-GCM
        
        Args:
            data: Data to encrypt
            key: 32-byte encryption key
            
        Returns:
            Encrypted data (IV + tag + ciphertext)
        """
        # Generate random IV
        iv = os.urandom(16)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Combine: IV (16) + tag (16) + ciphertext
        encrypted_data = iv + encryptor.tag + ciphertext
        
        return encrypted_data
    
    def _decrypt(self, encrypted_data: bytes, key: bytes) -> bytes:
        """
        Decrypt data using AES-256-GCM
        
        Args:
            encrypted_data: Encrypted data (IV + tag + ciphertext)
            key: 32-byte decryption key
            
        Returns:
            Decrypted data
            
        Raises:
            Exception if decryption fails (wrong key/machine)
        """
        # Extract components
        iv = encrypted_data[:16]
        tag = encrypted_data[16:32]
        ciphertext = encrypted_data[32:]
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt
        data = decryptor.update(ciphertext) + decryptor.finalize()
        
        return data


# CLI interface for testing
if __name__ == "__main__":
    print("="*70)
    print("CERTIFICATE MANAGER TEST")
    print("="*70)
    print()
    
    from fingerprint import get_machine_fingerprint
    
    # Get machine fingerprint
    fingerprint = get_machine_fingerprint()
    print(f"Machine Fingerprint: {fingerprint}")
    print()
    
    # Create manager
    manager = CertificateManager()
    
    # Test certificate
    test_cert = {
        "version": "1.0",
        "customer_id": "test-customer",
        "customer_name": "Test Company",
        "machine_id": "test-machine-123",
        "machine_fingerprint": fingerprint,
        "hostname": "TEST-PC",
        "product_key": "TEST-2024-ABCD-XYZ",
        "issued_at": "2024-11-21T10:00:00Z",
        "valid_until": "2025-11-21T10:00:00Z",
        "allowed_services": ["dashboard"],
        "signature": "abc123..."
    }
    
    # Save certificate
    print("Saving certificate...")
    manager.save_certificate(test_cert, fingerprint)
    print()
    
    # Load certificate
    print("Loading certificate...")
    loaded_cert = manager.load_certificate(fingerprint)
    
    if loaded_cert:
        print("✓ Certificate loaded successfully!")
        print(f"  Customer: {loaded_cert['customer_name']}")
        print(f"  Machine: {loaded_cert['hostname']}")
        print(f"  Valid until: {loaded_cert['valid_until']}")
    else:
        print("✗ Failed to load certificate")
    print()
    
    # Test with wrong fingerprint (should fail)
    print("Testing with wrong fingerprint (should fail)...")
    wrong_fp = "wrong-fingerprint-12345678"
    loaded_cert2 = manager.load_certificate(wrong_fp)
    
    if loaded_cert2:
        print("✗ ERROR: Certificate decrypted with wrong fingerprint!")
    else:
        print("✓ Correctly rejected wrong fingerprint")
    print()
    
    # Get info
    info = manager.get_certificate_info()
    if info:
        print("Certificate Info:")
        print(f"  Exists: {info['exists']}")
        print(f"  Size: {info['size']} bytes")
        print(f"  Path: {info['path']}")
    print()
    
    print("="*70)