#!/usr/bin/env python3
"""
KEY PAIR VERIFICATION SCRIPT
=============================
Verifies that server's private key matches client's public key

Usage:
    # On server side
    python verify_keypair.py --mode server --private-key private_key.pem
    
    # On client side  
    python verify_keypair.py --mode client --public-key public_key.pem
    
    # Compare both
    python verify_keypair.py --mode compare --private-key private_key.pem --public-key public_key.pem
"""

import sys
import hashlib
import argparse
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def get_key_fingerprint(key_pem_bytes):
    """Generate fingerprint from key"""
    return hashlib.sha256(key_pem_bytes).hexdigest()


def verify_keypair_match(private_key_path, public_key_path):
    """Verify that private and public keys are a matching pair"""
    
    print("="*70)
    print("KEY PAIR VERIFICATION")
    print("="*70)
    
    # Load private key
    print(f"\n1. Loading private key from: {private_key_path}")
    try:
        with open(private_key_path, 'rb') as f:
            private_key_pem = f.read()
            private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
                backend=default_backend()
            )
        print("   ✓ Private key loaded successfully")
        private_fingerprint = get_key_fingerprint(private_key_pem)
        print(f"   Fingerprint: {private_fingerprint[:32]}...")
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        return False
    
    # Load public key
    print(f"\n2. Loading public key from: {public_key_path}")
    try:
        with open(public_key_path, 'rb') as f:
            public_key_pem = f.read()
            public_key = serialization.load_pem_public_key(
                public_key_pem,
                backend=default_backend()
            )
        print("   ✓ Public key loaded successfully")
        public_fingerprint = get_key_fingerprint(public_key_pem)
        print(f"   Fingerprint: {public_fingerprint[:32]}...")
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        return False
    
    # Extract public key from private key
    print(f"\n3. Extracting public key from private key...")
    extracted_public_key = private_key.public_key()
    extracted_public_key_pem = extracted_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    extracted_fingerprint = get_key_fingerprint(extracted_public_key_pem)
    print(f"   Extracted public key fingerprint: {extracted_fingerprint[:32]}...")
    
    # Compare
    print(f"\n4. Comparing keys...")
    print(f"   Public key file fingerprint:     {public_fingerprint}")
    print(f"   Extracted from private key:      {extracted_fingerprint}")
    
    if public_fingerprint == extracted_fingerprint:
        print(f"\n✅ SUCCESS: Keys are a MATCHING PAIR!")
        print(f"   → Certificates signed with this private key")
        print(f"   → Can be verified with this public key")
        return True
    else:
        print(f"\n❌ MISMATCH: Keys are NOT a matching pair!")
        print(f"   → Certificates signed with this private key")
        print(f"   → CANNOT be verified with this public key")
        print(f"\n   This is why signature verification fails!")
        print(f"\n   Solutions:")
        print(f"   1. Use the correct private key that matches client's public key")
        print(f"   2. Or send client the new public key (and regenerate all certificates)")
        return False


def show_key_info(key_path, key_type):
    """Show information about a key"""
    
    print("="*70)
    print(f"{key_type.upper()} KEY INFORMATION")
    print("="*70)
    print(f"File: {key_path}\n")
    
    try:
        with open(key_path, 'rb') as f:
            key_pem = f.read()
        
        # Show fingerprint
        fingerprint = get_key_fingerprint(key_pem)
        print(f"Fingerprint: {fingerprint}")
        print(f"Short:       {fingerprint[:32]}...\n")
        
        # Load key to get details
        if key_type == "private":
            key = serialization.load_pem_private_key(
                key_pem,
                password=None,
                backend=default_backend()
            )
            print(f"Type: RSA Private Key")
            print(f"Size: {key.key_size} bits")
            
            # Extract public key
            public_key = key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            public_fingerprint = get_key_fingerprint(public_pem)
            print(f"\nCorresponding public key fingerprint: {public_fingerprint[:32]}...")
            
        else:  # public
            key = serialization.load_pem_public_key(
                key_pem,
                backend=default_backend()
            )
            print(f"Type: RSA Public Key")
            print(f"Size: {key.key_size} bits")
        
        print(f"\n✓ Key is valid and can be used")
        
        # Show actual PEM content (first/last lines)
        pem_lines = key_pem.decode('utf-8').split('\n')
        print(f"\nPEM Content:")
        print(f"  {pem_lines[0]}")
        print(f"  ... ({len(pem_lines)-2} lines)")
        print(f"  {pem_lines[-2]}")
        
    except Exception as e:
        print(f"✗ ERROR: {e}")


def test_sign_verify(private_key_path, public_key_path):
    """Test that we can sign and verify with the key pair"""
    
    print("\n" + "="*70)
    print("SIGN & VERIFY TEST")
    print("="*70)
    
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        # Load keys
        with open(private_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        
        with open(public_key_path, 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
        
        # Test data
        test_data = b"Test certificate data for signature verification"
        
        print(f"\n1. Signing test data with private key...")
        signature = private_key.sign(
            test_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA512()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA512()
        )
        print(f"   ✓ Signature created (length: {len(signature)} bytes)")
        
        print(f"\n2. Verifying signature with public key...")
        public_key.verify(
            signature,
            test_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA512()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA512()
        )
        print(f"   ✓ Signature verified successfully!")
        
        print(f"\n✅ Sign/Verify test PASSED")
        print(f"   This key pair works correctly for certificate signing")
        
    except Exception as e:
        print(f"\n❌ Sign/Verify test FAILED")
        print(f"   Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify key pair compatibility")
    parser.add_argument("--mode", choices=['server', 'client', 'compare', 'test'], 
                       required=True,
                       help="Mode: server (show private key), client (show public key), compare (check if keys match), test (sign & verify)")
    parser.add_argument("--private-key", default="private_key.pem",
                       help="Path to private key (default: private_key.pem)")
    parser.add_argument("--public-key", default="public_key.pem",
                       help="Path to public key (default: public_key.pem)")
    
    args = parser.parse_args()
    
    if args.mode == 'server':
        show_key_info(args.private_key, "private")
    
    elif args.mode == 'client':
        show_key_info(args.public_key, "public")
    
    elif args.mode == 'compare':
        if not verify_keypair_match(args.private_key, args.public_key):
            print("\n⚠️  IMPORTANT:")
            print("   The server's private key does NOT match the client's public key!")
            print("   This is why certificate validation is failing.")
            sys.exit(1)
        else:
            # Also run sign/verify test
            test_sign_verify(args.private_key, args.public_key)
    
    elif args.mode == 'test':
        test_sign_verify(args.private_key, args.public_key)