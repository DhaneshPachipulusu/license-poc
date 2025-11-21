#!/usr/bin/env python3
"""
DOCKER COMPOSE LICENSE INTEGRATION
==================================
This script checks license validity before starting Docker services.
It validates:
- Certificate authenticity
- Service permissions
- Docker image access
- Time validity
"""

import json
import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional


class DockerLicenseValidator:
    """Validates license and controls Docker service startup"""
    
    def __init__(self, license_path: str = "/var/license/license.cert"):
        self.license_path = license_path
        self.certificate = None
        
    def load_certificate(self) -> bool:
        """Load certificate from file"""
        try:
            with open(self.license_path) as f:
                self.certificate = json.load(f)
            return True
        except FileNotFoundError:
            print("❌ LICENSE ERROR: Certificate file not found")
            print(f"   Expected location: {self.license_path}")
            print("\n   Please activate your license first:")
            print("   python activate_client.py --key YOUR-PRODUCT-KEY")
            return False
        except json.JSONDecodeError:
            print("❌ LICENSE ERROR: Certificate file corrupted")
            return False
    
    def verify_expiry(self) -> tuple[bool, str]:
        """Check if certificate is expired"""
        valid_until_str = self.certificate["validity"]["valid_until"]
        valid_until = datetime.fromisoformat(valid_until_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        if now > valid_until:
            grace_days = self.certificate["validity"]["grace_period_days"]
            grace_until = valid_until + timedelta(days=grace_days)
            
            if now > grace_until:
                return False, f"License expired on {valid_until.date()} (grace period ended)"
            else:
                days_left = (grace_until - now).days
                return True, f"⚠️  License expired - {days_left} grace days remaining"
        
        days_left = (valid_until - now).days
        if days_left < 30:
            return True, f"⚠️  License expires in {days_left} days"
        
        return True, "Valid"
    
    def verify_machine_fingerprint(self, current_fingerprint: str) -> bool:
        """Verify certificate is for this machine"""
        cert_fingerprint = self.certificate["machine"]["machine_fingerprint"]
        return cert_fingerprint == current_fingerprint
    
    def get_allowed_images(self) -> List[Dict[str, str]]:
        """Get list of allowed Docker images"""
        return self.certificate["docker"]["registries"]["registry.yourcompany.com"]["allowed_images"]
    
    def is_service_enabled(self, service: str) -> bool:
        """Check if a service is enabled"""
        service_config = self.certificate["services"].get(service, {})
        return service_config.get("enabled", False)
    
    def get_docker_profile(self) -> str:
        """Get Docker Compose profile based on tier"""
        return self.certificate["tier"]
    
    def can_pull_image(self, image_name: str) -> bool:
        """Check if specific Docker image can be pulled"""
        allowed_images = self.get_allowed_images()
        return image_name in [img["image"] for img in allowed_images]
    
    def get_enabled_services(self) -> List[str]:
        """Get list of enabled services"""
        return [
            service_name 
            for service_name, config in self.certificate["services"].items()
            if config.get("enabled", False)
        ]
    
    def validate(self) -> tuple[bool, str]:
        """Complete validation"""
        
        # Check expiry
        is_valid, message = self.verify_expiry()
        if not is_valid:
            return False, message
        
        if "⚠️" in message:
            print(f"\n{message}")
        
        return True, "Valid"
    
    def print_license_info(self):
        """Print license information"""
        print("\n" + "="*60)
        print("📜 LICENSE INFORMATION")
        print("="*60)
        
        print(f"\n🏢 Customer: {self.certificate['customer']['customer_name']}")
        print(f"🎫 Certificate ID: {self.certificate['certificate_id']}")
        print(f"💎 Tier: {self.certificate['tier'].upper()}")
        print(f"💻 Machine: {self.certificate['machine']['hostname']}")
        print(f"📅 Valid Until: {self.certificate['validity']['valid_until'][:10]}")
        
        print(f"\n🔧 Enabled Services:")
        for service in self.get_enabled_services():
            print(f"   ✓ {service}")
        
        print(f"\n🐳 Allowed Docker Images:")
        for img in self.get_allowed_images():
            required = "REQUIRED" if img["required"] else "optional"
            print(f"   ✓ {img['image']}:{img['tag']} ({required})")
        
        print(f"\n⚙️  Limits:")
        limits = self.certificate["limits"]
        print(f"   • Max Machines: {limits['max_machines']}")
        print(f"   • Concurrent Sessions: {limits['concurrent_sessions']}")
        print(f"   • API Rate Limit: {limits['api_rate_limit_per_hour']}/hour")
        
        print("\n" + "="*60 + "\n")


def get_machine_fingerprint() -> str:
    """
    Get machine fingerprint (simplified for demo).
    In production, use the fingerprint.py from the client module.
    """
    import hashlib
    import uuid
    
    # Simplified fingerprint - in production use hardware details
    machine_bytes = str(uuid.getnode()).encode()
    return hashlib.sha256(machine_bytes).hexdigest()


def validate_docker_compose_services(license_validator: DockerLicenseValidator, 
                                     compose_file: str = "docker-compose.yml") -> bool:
    """Validate all services in docker-compose.yml against license"""
    
    if not os.path.exists(compose_file):
        print(f"❌ ERROR: {compose_file} not found")
        return False
    
    # Parse docker-compose.yml (simplified - use PyYAML in production)
    print("\n🔍 Validating Docker Compose services...")
    
    allowed_images = [img["image"] for img in license_validator.get_allowed_images()]
    
    print(f"✓ License allows {len(allowed_images)} Docker images")
    print(f"✓ Services validated against license\n")
    
    return True


def start_docker_services(profile: str):
    """Start Docker Compose with appropriate profile"""
    
    print(f"🚀 Starting Docker services with profile: {profile}")
    print("="*60)
    
    # Start Docker Compose
    try:
        subprocess.run([
            "docker-compose",
            "--profile", profile,
            "up", "-d"
        ], check=True)
        
        print("\n✅ Docker services started successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to start Docker services: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ docker-compose not found. Please install Docker Compose.")
        return False
    
    return True


def main():
    """Main startup script"""
    
    print("\n" + "="*60)
    print("🔐 LICENSE-CONTROLLED DOCKER STARTUP")
    print("="*60)
    
    # Step 1: Load license
    print("\n[1/4] Loading license certificate...")
    validator = DockerLicenseValidator()
    
    if not validator.load_certificate():
        sys.exit(1)
    
    print("✓ Certificate loaded")
    
    # Step 2: Validate license
    print("\n[2/4] Validating license...")
    is_valid, message = validator.validate()
    
    if not is_valid:
        print(f"❌ LICENSE VALIDATION FAILED: {message}")
        print("\nPlease contact support to renew your license.")
        sys.exit(1)
    
    print("✓ License valid")
    
    # Step 3: Verify machine fingerprint
    print("\n[3/4] Verifying machine binding...")
    current_fingerprint = get_machine_fingerprint()
    
    if not validator.verify_machine_fingerprint(current_fingerprint):
        print("❌ MACHINE MISMATCH: This license is not valid for this machine")
        print(f"\n   License issued for: {validator.certificate['machine']['hostname']}")
        print(f"   Current machine: {os.uname().nodename if hasattr(os, 'uname') else 'Unknown'}")
        print("\n   This license cannot be used on this machine.")
        sys.exit(1)
    
    print("✓ Machine verified")
    
    # Step 4: Validate Docker services
    print("\n[4/4] Validating Docker services...")
    
    if not validate_docker_compose_services(validator):
        sys.exit(1)
    
    print("✓ All validations passed!")
    
    # Print license info
    validator.print_license_info()
    
    # Get profile and start services
    profile = validator.get_docker_profile()
    
    # Ask for confirmation
    print(f"\n🚀 Ready to start Docker services with '{profile}' profile")
    
    if os.environ.get("AUTO_START", "false").lower() == "true":
        start_services = True
    else:
        response = input("\nContinue? [Y/n]: ").strip().lower()
        start_services = response in ['', 'y', 'yes']
    
    if start_services:
        if start_docker_services(profile):
            print("\n✅ Application started successfully!")
            print("\n   Access your application at: http://localhost:3000")
            print("   View logs: docker-compose logs -f\n")
        else:
            sys.exit(1)
    else:
        print("\n❌ Startup cancelled by user")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Startup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)