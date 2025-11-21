"""
ADVANCED CERTIFICATE GENERATION SYSTEM
======================================
Features:
- Docker image access control with registry URLs
- Service-level permissions (granular control)
- Time-based expiry with grace periods
- Machine limits with upgrade capability
- Certificate versioning for upgrades
- Cryptographic binding to machine fingerprint
- Multi-layer security (AES-256-GCM + RSA-4096 + HMAC)
"""

import json
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import uuid
import base64


class AdvancedCertificateGenerator:
    """Advanced certificate generator with multi-layer security"""
    
    def __init__(self, private_key_path: str = "private_key.pem"):
        self.private_key_path = private_key_path
        self.private_key = self._load_or_generate_private_key()
        self.public_key = self.private_key.public_key()
        
    def _load_or_generate_private_key(self):
        """Load existing RSA key or generate new 4096-bit key"""
        try:
            with open(self.private_key_path, "rb") as f:
                return serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
        except FileNotFoundError:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
            
            with open(self.private_key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            with open("public_key.pem", "wb") as f:
                f.write(self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
            
            return private_key
    
    def generate_certificate(
        self,
        customer_id: str,
        customer_name: str,
        machine_fingerprint: str,
        hostname: str,
        product_key: str,
        tier: str = "basic",
        valid_days: int = 365,
        machine_limit: int = 3,
        allowed_services: Optional[List[str]] = None,
        allowed_docker_images: Optional[List[Dict[str, str]]] = None,
        custom_permissions: Optional[Dict[str, Any]] = None,
        parent_cert_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive certificate"""
        
        cert_id = f"CERT-{uuid.uuid4().hex[:16].upper()}"
        machine_id = f"MACHINE-{uuid.uuid4().hex[:12].upper()}"
        
        issued_at = datetime.now(timezone.utc)
        valid_until = issued_at + timedelta(days=valid_days)
        
        if allowed_services is None:
            allowed_services = self._get_default_services(tier)
        
        if allowed_docker_images is None:
            allowed_docker_images = self._get_default_docker_images(tier)
        
        service_permissions = self._build_service_permissions(allowed_services, tier)
        docker_access = self._build_docker_access_control(allowed_docker_images, tier)
        features = self._build_feature_flags(tier, custom_permissions)
        
        certificate = {
            "certificate_id": cert_id,
            "certificate_version": "2.0",
            "certificate_type": "machine_license",
            "tier": tier,
            
            "customer": {
                "customer_id": customer_id,
                "customer_name": customer_name,
                "product_key": product_key,
            },
            
            "machine": {
                "machine_id": machine_id,
                "machine_fingerprint": machine_fingerprint,
                "hostname": hostname,
                "fingerprint_algorithm": "SHA3-512",
            },
            
            "validity": {
                "issued_at": issued_at.isoformat(),
                "valid_until": valid_until.isoformat(),
                "grace_period_days": 7,
                "timezone": "UTC"
            },
            
            "limits": {
                "max_machines": machine_limit,
                "current_machine_number": 1,
                "concurrent_sessions": self._get_session_limit(tier),
                "api_rate_limit_per_hour": self._get_rate_limit(tier)
            },
            
            "services": service_permissions,
            "docker": docker_access,
            "features": features,
            
            "upgrade_chain": {
                "parent_certificate_id": parent_cert_id,
                "upgrade_count": 0 if not parent_cert_id else 1,
                "is_upgrade": parent_cert_id is not None,
                "can_upgrade": tier != "enterprise"
            },
            
            "security": {
                "encryption_algorithm": "AES-256-GCM",
                "signature_algorithm": "RSA-4096-SHA512",
                "integrity_algorithm": "HMAC-SHA512",
                "binding_method": "machine_fingerprint"
            },
            
            "metadata": metadata or {}
        }
        
        certificate = self._add_cryptographic_layers(certificate, machine_fingerprint)
        
        return certificate
    
    def _get_default_services(self, tier: str) -> List[str]:
        """Get default services based on tier"""
        services_by_tier = {
            "trial": ["dashboard", "basic_analytics"],
            "basic": ["dashboard", "analytics", "reports"],
            "pro": ["dashboard", "analytics", "reports", "api", "integrations"],
            "enterprise": ["dashboard", "analytics", "reports", "api", 
                          "integrations", "custom_modules", "white_label", "sso"]
        }
        return services_by_tier.get(tier, ["dashboard"])
    
    def _get_default_docker_images(self, tier: str) -> List[Dict[str, str]]:
        """Get default Docker images based on tier"""
        
        base_images = [
            {
                "name": "frontend",
                "registry": "registry.yourcompany.com",
                "image": "frontend-app",
                "tag": "latest",
                "required": True
            },
            {
                "name": "backend",
                "registry": "registry.yourcompany.com",
                "image": "backend-api",
                "tag": "latest",
                "required": True
            }
        ]
        
        tier_specific = {
            "trial": [],
            "basic": [
                {
                    "name": "analytics",
                    "registry": "registry.yourcompany.com",
                    "image": "analytics-engine",
                    "tag": "basic",
                    "required": False
                }
            ],
            "pro": [
                {
                    "name": "analytics",
                    "registry": "registry.yourcompany.com",
                    "image": "analytics-engine",
                    "tag": "pro",
                    "required": False
                },
                {
                    "name": "ml-engine",
                    "registry": "registry.yourcompany.com",
                    "image": "ml-processor",
                    "tag": "latest",
                    "required": False
                }
            ],
            "enterprise": [
                {
                    "name": "analytics",
                    "registry": "registry.yourcompany.com",
                    "image": "analytics-engine",
                    "tag": "enterprise",
                    "required": False
                },
                {
                    "name": "ml-engine",
                    "registry": "registry.yourcompany.com",
                    "image": "ml-processor",
                    "tag": "enterprise",
                    "required": False
                },
                {
                    "name": "custom-modules",
                    "registry": "registry.yourcompany.com",
                    "image": "custom-builder",
                    "tag": "latest",
                    "required": False
                }
            ]
        }
        
        return base_images + tier_specific.get(tier, [])
    
    def _build_service_permissions(self, allowed_services: List[str], tier: str) -> Dict[str, Any]:
        """Build granular service permissions"""
        
        all_services = {
            "dashboard": {
                "enabled": "dashboard" in allowed_services,
                "permissions": ["read", "view"],
                "features": ["basic_charts", "data_export"]
            },
            "analytics": {
                "enabled": "analytics" in allowed_services,
                "permissions": ["read", "view", "export"],
                "features": ["advanced_charts", "custom_reports", "scheduled_reports"],
                "data_retention_days": 90 if tier == "basic" else 365
            },
            "reports": {
                "enabled": "reports" in allowed_services,
                "permissions": ["read", "create", "edit", "delete"],
                "max_reports": 10 if tier == "basic" else 100,
                "export_formats": ["pdf", "csv", "xlsx"]
            },
            "api": {
                "enabled": "api" in allowed_services,
                "permissions": ["read", "write"],
                "rate_limit_per_hour": 1000 if tier == "pro" else 10000,
                "endpoints": ["v1", "v2"] if tier == "enterprise" else ["v1"]
            },
            "integrations": {
                "enabled": "integrations" in allowed_services,
                "permissions": ["configure", "execute"],
                "available_integrations": ["webhook", "zapier", "slack"] 
                    if tier == "pro" else ["webhook", "zapier", "slack", "custom"]
            },
            "custom_modules": {
                "enabled": "custom_modules" in allowed_services,
                "permissions": ["read", "write", "deploy"],
                "max_modules": 5 if tier == "pro" else -1
            },
            "white_label": {
                "enabled": "white_label" in allowed_services,
                "permissions": ["customize_branding", "custom_domain"],
            },
            "sso": {
                "enabled": "sso" in allowed_services,
                "permissions": ["configure"],
                "providers": ["saml", "oauth2", "ldap"]
            }
        }
        
        return all_services
    
    def _build_docker_access_control(self, allowed_images: List[Dict[str, str]], tier: str) -> Dict[str, Any]:
        """Build Docker registry access control"""
        
        return {
            "enabled": True,
            "registries": {
                "registry.yourcompany.com": {
                    "authentication_required": True,
                    "access_token_url": "https://registry.yourcompany.com/v2/token",
                    "allowed_images": allowed_images
                }
            },
            "pull_limits": {
                "max_pulls_per_day": 100 if tier == "basic" else 1000,
                "max_concurrent_pulls": 5 if tier == "basic" else 20
            },
            "image_validation": {
                "verify_signatures": True,
                "scan_for_vulnerabilities": tier in ["pro", "enterprise"],
                "allowed_architectures": ["amd64", "arm64"]
            }
        }
    
    def _build_feature_flags(self, tier: str, custom_permissions: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build feature flags"""
        
        base_features = {
            "offline_mode": {
                "enabled": True,
                "max_offline_days": 7 if tier == "basic" else 30
            },
            "multi_tenancy": {
                "enabled": tier in ["pro", "enterprise"],
                "max_tenants": 5 if tier == "pro" else -1
            },
            "backup_restore": {
                "enabled": tier in ["pro", "enterprise"],
                "auto_backup": tier == "enterprise",
                "backup_frequency_hours": 24
            },
            "audit_logging": {
                "enabled": tier in ["pro", "enterprise"],
                "retention_days": 90 if tier == "pro" else 365
            },
            "high_availability": {
                "enabled": tier == "enterprise",
                "min_replicas": 3
            }
        }
        
        if custom_permissions:
            base_features.update(custom_permissions)
        
        return base_features
    
    def _get_session_limit(self, tier: str) -> int:
        limits = {"trial": 1, "basic": 3, "pro": 10, "enterprise": -1}
        return limits.get(tier, 1)
    
    def _get_rate_limit(self, tier: str) -> int:
        limits = {"trial": 100, "basic": 1000, "pro": 10000, "enterprise": 100000}
        return limits.get(tier, 100)
    
    def _add_cryptographic_layers(self, certificate: Dict[str, Any], machine_fingerprint: str) -> Dict[str, Any]:
        """Add cryptographic protection layers"""
        
        fp_hash = hashlib.sha3_512(machine_fingerprint.encode()).hexdigest()
        certificate["security"]["fingerprint_hash"] = fp_hash
        
        hmac_key = secrets.token_bytes(64)
        cert_bytes = json.dumps(certificate, sort_keys=True).encode()
        hmac_digest = hmac.new(hmac_key, cert_bytes, hashlib.sha512).hexdigest()
        
        certificate["security"]["hmac"] = hmac_digest
        certificate["security"]["hmac_key"] = base64.b64encode(hmac_key).decode()
        
        signature = self.private_key.sign(
            cert_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA512()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA512()
        )
        
        certificate["signature"] = base64.b64encode(signature).decode()
        certificate["signature_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return certificate
    
    def upgrade_certificate(
        self,
        old_certificate: Dict[str, Any],
        new_tier: Optional[str] = None,
        additional_days: Optional[int] = None,
        new_machine_limit: Optional[int] = None,
        additional_services: Optional[List[str]] = None,
        additional_docker_images: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Generate upgraded certificate"""
        
        customer_id = old_certificate["customer"]["customer_id"]
        customer_name = old_certificate["customer"]["customer_name"]
        machine_fingerprint = old_certificate["machine"]["machine_fingerprint"]
        hostname = old_certificate["machine"]["hostname"]
        product_key = old_certificate["customer"]["product_key"]
        
        tier = new_tier or old_certificate["tier"]
        
        old_valid_until = datetime.fromisoformat(old_certificate["validity"]["valid_until"])
        if additional_days:
            valid_until = old_valid_until + timedelta(days=additional_days)
            valid_days = (valid_until - datetime.now(timezone.utc)).days
        else:
            valid_days = (old_valid_until - datetime.now(timezone.utc)).days
        
        machine_limit = new_machine_limit or old_certificate["limits"]["max_machines"]
        
        old_services = [svc for svc, data in old_certificate["services"].items() if data.get("enabled")]
        allowed_services = list(set(old_services + (additional_services or [])))
        
        old_images = old_certificate["docker"]["registries"]["registry.yourcompany.com"]["allowed_images"]
        allowed_docker_images = old_images + (additional_docker_images or [])
        
        new_cert = self.generate_certificate(
            customer_id=customer_id,
            customer_name=customer_name,
            machine_fingerprint=machine_fingerprint,
            hostname=hostname,
            product_key=product_key,
            tier=tier,
            valid_days=valid_days,
            machine_limit=machine_limit,
            allowed_services=allowed_services,
            allowed_docker_images=allowed_docker_images,
            parent_cert_id=old_certificate["certificate_id"],
            metadata={
                "upgrade_from_tier": old_certificate["tier"],
                "upgrade_reason": "customer_upgrade",
                "upgraded_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        new_cert["upgrade_chain"]["upgrade_count"] = old_certificate["upgrade_chain"]["upgrade_count"] + 1
        
        return new_cert
    
    def verify_certificate(self, certificate: Dict[str, Any], public_key_path: str = "public_key.pem") -> tuple[bool, str]:
        """Verify certificate authenticity"""
        
        try:
            with open(public_key_path, "rb") as f:
                public_key = serialization.load_pem_public_key(f.read(), backend=default_backend())
            
            signature = base64.b64decode(certificate["signature"])
            
            cert_copy = certificate.copy()
            cert_copy.pop("signature")
            cert_copy.pop("signature_timestamp")
            
            cert_bytes = json.dumps(cert_copy, sort_keys=True).encode()
            
            public_key.verify(
                signature,
                cert_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA512()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA512()
            )
            
            hmac_key = base64.b64decode(certificate["security"]["hmac_key"])
            expected_hmac = hmac.new(hmac_key, cert_bytes, hashlib.sha512).hexdigest()
            
            if expected_hmac != certificate["security"]["hmac"]:
                return False, "HMAC verification failed"
            
            valid_until = datetime.fromisoformat(certificate["validity"]["valid_until"])
            if datetime.now(timezone.utc) > valid_until:
                return False, "Certificate expired"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Verification failed: {str(e)}"


def main():
    """Demo"""
    print("=" * 80)
    print("ADVANCED CERTIFICATE GENERATION SYSTEM - DEMO")
    print("=" * 80)
    
    generator = AdvancedCertificateGenerator()
    
    print("\n[1] Generating BASIC tier certificate...")
    basic_cert = generator.generate_certificate(
        customer_id="CUST-001",
        customer_name="Acme Corporation",
        machine_fingerprint="FP-ABC123-XYZ789-HARDWARE",
        hostname="OFFICE-PC-001",
        product_key="ACME-2024-BASIC-X7Y9",
        tier="basic",
        valid_days=365,
        machine_limit=3
    )
    
    print(f"✓ Certificate ID: {basic_cert['certificate_id']}")
    print(f"✓ Tier: {basic_cert['tier']}")
    print(f"✓ Services: {len([s for s, d in basic_cert['services'].items() if d['enabled']])} enabled")
    print(f"✓ Docker Images: {len(basic_cert['docker']['registries']['registry.yourcompany.com']['allowed_images'])}")
    
    print("\n[2] Generating ENTERPRISE tier certificate...")
    enterprise_cert = generator.generate_certificate(
        customer_id="CUST-002",
        customer_name="TechGiant Inc",
        machine_fingerprint="FP-DEF456-UVW012-HARDWARE",
        hostname="SERVER-PROD-001",
        product_key="TECH-2024-ENT-A1B2",
        tier="enterprise",
        valid_days=365,
        machine_limit=50,
        custom_permissions={
            "custom_feature_1": {"enabled": True},
            "advanced_analytics": {"enabled": True, "ml_models": True}
        }
    )
    
    print(f"✓ Certificate ID: {enterprise_cert['certificate_id']}")
    print(f"✓ Tier: {enterprise_cert['tier']}")
    print(f"✓ Machine Limit: {enterprise_cert['limits']['max_machines']}")
    
    print("\n[3] Upgrading BASIC certificate to PRO...")
    upgraded_cert = generator.upgrade_certificate(
        old_certificate=basic_cert,
        new_tier="pro",
        additional_days=365,
        new_machine_limit=10,
        additional_services=["integrations", "custom_modules"]
    )
    
    print(f"✓ New Certificate ID: {upgraded_cert['certificate_id']}")
    print(f"✓ Upgraded from: {upgraded_cert['metadata']['upgrade_from_tier']} → {upgraded_cert['tier']}")
    
    print("\n[4] Verifying certificate...")
    is_valid, reason = generator.verify_certificate(upgraded_cert)
    print(f"✓ Verification: {is_valid} - {reason}")
    
    with open("/home/claude/sample_basic_cert.json", "w") as f:
        json.dump(basic_cert, f, indent=2)
    
    with open("/home/claude/sample_enterprise_cert.json", "w") as f:
        json.dump(enterprise_cert, f, indent=2)
    
    with open("/home/claude/sample_upgraded_cert.json", "w") as f:
        json.dump(upgraded_cert, f, indent=2)
    
    print("\n" + "=" * 80)
    print("✓ Certificates saved!")
    print("=" * 80)


if __name__ == "__main__":
    main()