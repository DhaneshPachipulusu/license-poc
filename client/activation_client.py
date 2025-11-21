"""
Activation Client
Communicates with license server to activate machine

Usage:
    from activation_client import ActivationClient
    
    client = ActivationClient("https://license.mycompany.com")
    
    # Activate
    result = client.activate(
        product_key="ACME-2024-X7H9-K2P",
        hostname="OFFICE-PC"
    )
    
    if result.success:
        print("Activated!")
    else:
        print(f"Error: {result.error}")
"""

import requests
import json
from typing import Optional, Dict
from dataclasses import dataclass

from fingerprint import get_machine_fingerprint
from cert_manager import CertificateManager


@dataclass
class ActivationResult:
    """Result of activation attempt"""
    success: bool
    message: str
    error: Optional[str] = None
    certificate: Optional[Dict] = None
    active_machines: Optional[list] = None


class ActivationClient:
    """Client for activating licenses with server"""
    
    def __init__(
        self, 
        server_url: str = "http://localhost:8000",
        timeout: int = 30
    ):
        """
        Initialize activation client
        
        Args:
            server_url: URL of license server
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.cert_manager = CertificateManager()
    
    def activate(
        self,
        product_key: str,
        hostname: str = None,
        os_info: str = None,
        app_version: str = "1.0.0"
    ) -> ActivationResult:
        """
        Activate license with server
        
        Args:
            product_key: Product key from admin
            hostname: Machine hostname (optional)
            os_info: OS information (optional)
            app_version: Application version
            
        Returns:
            ActivationResult with status
        """
        
        print("\n" + "="*70)
        print("LICENSE ACTIVATION")
        print("="*70 + "\n")
        
        # Get machine fingerprint
        print("Generating machine fingerprint...")
        fingerprint = get_machine_fingerprint()
        print(f"✓ Fingerprint: {fingerprint[:16]}...")
        print()
        
        # Get hostname if not provided
        if not hostname:
            import platform
            hostname = platform.node()
        
        # Get OS info if not provided
        if not os_info:
            import platform
            os_info = f"{platform.system()} {platform.release()}"
        
        # Prepare request
        payload = {
            "product_key": product_key.strip().upper(),
            "machine_fingerprint": fingerprint,
            "hostname": hostname,
            "os_info": os_info,
            "app_version": app_version
        }
        
        print(f"Activating with server: {self.server_url}")
        print(f"  Product Key: {product_key}")
        print(f"  Hostname: {hostname}")
        print(f"  OS: {os_info}")
        print()
        
        try:
            # Send activation request
            response = requests.post(
                f"{self.server_url}/api/v1/activate",
                json=payload,
                timeout=self.timeout
            )
            
            # Parse response
            result = response.json()
            
            # Check if successful
            if result.get('success'):
                certificate = result.get('certificate')
                message = result.get('message', 'Activation successful')
                
                print(f"✓ {message}")
                print()
                
                # Download public key
                print("Downloading public key for signature verification...")
                public_key = self._download_public_key()
                
                if public_key:
                    print("✓ Public key downloaded")
                else:
                    print("⚠ Warning: Could not download public key")
                print()
                
                # Save certificate
                print("Saving certificate...")
                self.cert_manager.save_certificate(
                    certificate,
                    fingerprint,
                    public_key
                )
                print()
                
                print("="*70)
                print("✅ ACTIVATION COMPLETE")
                print("="*70)
                print()
                
                return ActivationResult(
                    success=True,
                    message=message,
                    certificate=certificate
                )
            else:
                # Activation failed
                error = result.get('error', 'unknown')
                message = result.get('message', 'Activation failed')
                active_machines = result.get('active_machines')
                
                print(f"✗ {message}")
                
                if active_machines:
                    print("\nActive machines:")
                    for i, machine in enumerate(active_machines, 1):
                        print(f"  {i}. {machine.get('hostname', 'Unknown')}")
                        print(f"     Last seen: {machine.get('last_seen', 'Unknown')}")
                
                print()
                
                return ActivationResult(
                    success=False,
                    message=message,
                    error=error,
                    active_machines=active_machines
                )
        
        except requests.exceptions.Timeout:
            print(f"✗ Request timed out after {self.timeout} seconds")
            return ActivationResult(
                success=False,
                message="Server request timed out",
                error="timeout"
            )
        
        except requests.exceptions.ConnectionError:
            print(f"✗ Could not connect to server: {self.server_url}")
            return ActivationResult(
                success=False,
                message="Could not connect to license server",
                error="connection_error"
            )
        
        except Exception as e:
            print(f"✗ Activation error: {e}")
            return ActivationResult(
                success=False,
                message=f"Activation error: {str(e)}",
                error="unknown"
            )
    
    def _download_public_key(self) -> Optional[str]:
        """Download RSA public key from server"""
        try:
            response = requests.get(
                f"{self.server_url}/api/v1/public-key",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.text
        except:
            pass
        
        return None
    
    def check_server_status(self) -> bool:
        """Check if license server is reachable"""
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def deactivate(self) -> bool:
        """
        Deactivate current machine (remove certificate)
        
        Note: This only removes local certificate.
        Server-side deactivation should be done by admin.
        """
        try:
            self.cert_manager.delete_certificate()
            print("✓ Machine deactivated (certificate removed)")
            return True
        except Exception as e:
            print(f"✗ Deactivation error: {e}")
            return False


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="License Activation Tool")
    parser.add_argument("--server", default="http://localhost:8000", 
                       help="License server URL")
    parser.add_argument("--key", required=True, 
                       help="Product key")
    parser.add_argument("--hostname", 
                       help="Machine hostname (optional)")
    parser.add_argument("--deactivate", action="store_true",
                       help="Deactivate (remove certificate)")
    
    args = parser.parse_args()
    
    client = ActivationClient(args.server)
    
    if args.deactivate:
        # Deactivate
        client.deactivate()
    else:
        # Activate
        result = client.activate(
            product_key=args.key,
            hostname=args.hostname
        )
        
        if not result.success:
            exit(1)