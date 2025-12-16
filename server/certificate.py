"""
ADVANCED CERTIFICATE GENERATION SYSTEM v3.1 - FIXED
====================================================
Fixes:
- Proper tier detection (reads from database, not product key)
- No networks in compose (Windows compatibility)
- Correct volume mount with bind
- Only enabled services in compose
"""

import json
import hashlib
import hmac
import secrets
import base64
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


class AdvancedCertificateGenerator:
    """Advanced certificate generator with dynamic compose support"""
    
    # ===========================================
    # CONFIGURATION
    # ===========================================
    
    REGISTRY_CONFIG = {
        "registry_url": "docker.io",
        "registry_username": "nainovate",
    }
    
    # Service definitions with images and ports
    SERVICE_DEFINITIONS = {
        "frontend": {
            "image": "nainovate/nia-frontend",
            "default_tag": "v3.0",  # Changed to license
            "container_port": 3005,
            "host_port": 3005,
            "required": True,
            "description": "AI Dashboard Frontend"
        },
        "backend": {
            "image": "nainovate/ai-dashboard-backend",
            "default_tag": "license",  # Changed to license
            "container_port": 8000,
            "host_port": 8000,
            "required": False,
            "description": "AI Dashboard Backend API"
        },
        "analytics": {
            "image": "nainovate/ai-dashboard-analytics",
            "default_tag": "latest",
            "container_port": 9000,
            "host_port": 9000,
            "required": False,
            "description": "Analytics Engine"
        },
        "monitoring": {
            "image": "nainovate/ai-dashboard-monitoring",
            "default_tag": "latest",
            "container_port": 9090,
            "host_port": 9090,
            "required": False,
            "description": "Monitoring Service"
        }
    }
    
    # Tier-based service access
    TIER_SERVICES = {
        "trial": ["frontend"],
        "basic": ["frontend", "backend"],
        "pro": ["frontend", "backend", "analytics"],
        "enterprise": ["frontend", "backend", "analytics", "monitoring"]
    }
    
    # Tier-based limits
    TIER_LIMITS = {
        "trial": {
            "max_machines": 1,
            "valid_days": 14,
            "concurrent_sessions": 1,
            "api_rate_limit": 100
        },
        "basic": {
            "max_machines": 3,
            "valid_days": 365,
            "concurrent_sessions": 5,
            "api_rate_limit": 1000
        },
        "pro": {
            "max_machines": 10,
            "valid_days": 365,
            "concurrent_sessions": 20,
            "api_rate_limit": 5000
        },
        "enterprise": {
            "max_machines": 100,
            "valid_days": 365,
            "concurrent_sessions": -1,
            "api_rate_limit": -1
        }
    }
    
    def __init__(self, private_key_path: str = "private_key.pem", docker_pat: str = None):
        self.private_key_path = private_key_path
        self.private_key = self._load_or_generate_private_key()
        self.public_key = self.private_key.public_key()
        self.docker_pat = docker_pat
        
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
            
            public_key = private_key.public_key()
            with open("public_key.pem", "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
            
            return private_key
    
    def _encrypt_data(self, data: str, key: bytes) -> str:
        """Encrypt data using AES-256-GCM"""
        derived_key = hashlib.sha256(key).digest()
        aesgcm = AESGCM(derived_key)
        nonce = secrets.token_bytes(12)
        ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
        return base64.b64encode(nonce + ciphertext).decode()
    
    def generate_certificate(
        self,
        customer_id: str,
        customer_name: str,
        machine_fingerprint: str,
        hostname: str,
        product_key: str,
        tier: str = "basic",  # Now explicitly passed from database
        valid_days: Optional[int] = None,
        machine_limit: Optional[int] = None,
        custom_services: Optional[List[str]] = None,
        custom_image_tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_cert_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive certificate with Docker configuration"""
        
        cert_id = f"CERT-{uuid.uuid4().hex[:16].upper()}"
        machine_id = f"MACHINE-{uuid.uuid4().hex[:12].upper()}"
        
        tier_config = self.TIER_LIMITS.get(tier, self.TIER_LIMITS["basic"])
        actual_valid_days = valid_days or tier_config["valid_days"]
        actual_machine_limit = machine_limit or tier_config["max_machines"]
        
        issued_at = datetime.now(timezone.utc)
        valid_until = issued_at + timedelta(days=actual_valid_days)
        
        allowed_services = custom_services or self.TIER_SERVICES.get(tier, ["frontend"])
        
        docker_config = self._build_docker_config(
            tier=tier,
            allowed_services=allowed_services,
            custom_image_tags=custom_image_tags,
            machine_fingerprint=machine_fingerprint
        )
        
        service_permissions = self._build_service_permissions(allowed_services, tier)
        features = self._build_feature_flags(tier)
        
        certificate = {
            "certificate_id": cert_id,
            "certificate_version": "3.1",
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
                "valid_days": actual_valid_days,
                "grace_period_days": 7,
                "timezone": "UTC"
            },
            
            "limits": {
                "max_machines": actual_machine_limit,
                "current_machine_number": 1,
                "concurrent_sessions": tier_config["concurrent_sessions"],
                "api_rate_limit_per_hour": tier_config["api_rate_limit"]
            },
            
            "services": service_permissions,
            "docker": docker_config,
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
    
    def _build_docker_config(
        self,
        tier: str,
        allowed_services: List[str],
        custom_image_tags: Optional[Dict[str, str]] = None,
        machine_fingerprint: str = ""
    ) -> Dict[str, Any]:
        """Build Docker configuration for certificate"""
        
        custom_image_tags = custom_image_tags or {}
        
        services = {}
        for service_name in allowed_services:
            if service_name in self.SERVICE_DEFINITIONS:
                svc_def = self.SERVICE_DEFINITIONS[service_name]
                services[service_name] = {
                    "enabled": True,
                    "image": svc_def["image"],
                    "tag": custom_image_tags.get(service_name, svc_def["default_tag"]),
                    "container_port": svc_def["container_port"],
                    "host_port": svc_def["host_port"],
                    "required": svc_def["required"],
                    "description": svc_def["description"]
                }
        
        for service_name, svc_def in self.SERVICE_DEFINITIONS.items():
            if service_name not in services:
                services[service_name] = {
                    "enabled": False,
                    "image": svc_def["image"],
                    "tag": svc_def["default_tag"],
                    "container_port": svc_def["container_port"],
                    "host_port": svc_def["host_port"],
                    "required": False,
                    "description": svc_def["description"],
                    "reason_disabled": f"Not included in {tier} tier"
                }
        
        docker_config = {
            "registry": {
                "url": self.REGISTRY_CONFIG["registry_url"],
                "username": self.REGISTRY_CONFIG["registry_username"],
            },
            "services": services,
            "compose_version": "3.8",
            "network_name": "license-network"
        }
        
        return docker_config
    
    def _build_service_permissions(self, allowed_services: List[str], tier: str) -> Dict[str, Any]:
        """Build service permissions based on tier"""
        permissions = {}
        
        all_possible_services = [
            "dashboard", "analytics", "reports", "api", 
            "integrations", "custom_modules", "white_label", "sso"
        ]
        
        tier_access = {
            "trial": ["dashboard"],
            "basic": ["dashboard", "analytics", "reports"],
            "pro": ["dashboard", "analytics", "reports", "api", "integrations"],
            "enterprise": all_possible_services
        }
        
        enabled_services = tier_access.get(tier, ["dashboard"])
        
        for service in all_possible_services:
            permissions[service] = {
                "enabled": service in enabled_services,
                "tier_required": self._get_minimum_tier_for_service(service)
            }
        
        return permissions
    
    def _get_minimum_tier_for_service(self, service: str) -> str:
        """Get minimum tier required for a service"""
        service_tiers = {
            "dashboard": "trial",
            "analytics": "basic",
            "reports": "basic",
            "api": "pro",
            "integrations": "pro",
            "custom_modules": "enterprise",
            "white_label": "enterprise",
            "sso": "enterprise"
        }
        return service_tiers.get(service, "enterprise")
    
    def _build_feature_flags(self, tier: str) -> Dict[str, Any]:
        """Build feature flags based on tier"""
        
        features = {
            "offline_mode": {
                "enabled": tier in ["basic", "pro", "enterprise"],
                "max_offline_days": 7 if tier == "basic" else 30 if tier == "pro" else 90
            },
            "auto_updates": {
                "enabled": tier in ["pro", "enterprise"],
                "channel": "stable" if tier == "pro" else "all"
            },
            "priority_support": {
                "enabled": tier == "enterprise",
                "sla_hours": 4 if tier == "enterprise" else None
            },
            "custom_branding": {
                "enabled": tier == "enterprise"
            },
            "api_access": {
                "enabled": tier in ["pro", "enterprise"],
                "rate_limit": 5000 if tier == "pro" else -1
            },
            "export_data": {
                "enabled": tier in ["basic", "pro", "enterprise"],
                "formats": ["csv"] if tier == "basic" else ["csv", "json", "xlsx"]
            }
        }
        
        return features
    
    def _add_cryptographic_layers(self, certificate: Dict[str, Any], machine_fingerprint: str) -> Dict[str, Any]:
        """Add cryptographic protection layers"""
        
        # Calculate fingerprint hash
        fp_hash = hashlib.sha3_512(machine_fingerprint.encode()).hexdigest()
        certificate["security"]["fingerprint_hash"] = fp_hash
        
        # Generate HMAC but don't add to cert yet
        hmac_key = secrets.token_bytes(64)
        
        # Create cert_bytes WITHOUT hmac fields for signing
        cert_copy_for_hmac = certificate.copy()
        # Remove security fields that shouldn't be in signature
        security_backup = cert_copy_for_hmac.pop("security")
        cert_bytes_for_hmac = json.dumps(cert_copy_for_hmac, sort_keys=True).encode()
        hmac_digest = hmac.new(hmac_key, cert_bytes_for_hmac, hashlib.sha512).hexdigest()
        
        # Now add HMAC to certificate
        certificate["security"]["hmac"] = hmac_digest
        certificate["security"]["hmac_key"] = base64.b64encode(hmac_key).decode()
        
        # Create final cert_bytes for signature (without signature fields)
        cert_copy_for_sig = certificate.copy()
        # Don't include signature or timestamp in what we sign
        cert_copy_for_sig.pop("signature", None)
        cert_copy_for_sig.pop("signature_timestamp", None)
        cert_bytes = json.dumps(cert_copy_for_sig, sort_keys=True).encode()
        
        # Sign the complete certificate (including security with hmac)
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
    
    def generate_docker_credentials(self, machine_fingerprint: str) -> Dict[str, str]:
        """Generate encrypted Docker credentials for a machine"""
        if not self.docker_pat:
            raise ValueError("Docker PAT not configured")
        
        credentials = {
            "registry": self.REGISTRY_CONFIG["registry_url"],
            "username": self.REGISTRY_CONFIG["registry_username"],
            "token": self.docker_pat,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        encrypted = self._encrypt_data(
            json.dumps(credentials),
            machine_fingerprint.encode()
        )
        
        return {
            "encrypted_credentials": encrypted,
            "encryption_method": "AES-256-GCM",
            "key_derivation": "SHA256(machine_fingerprint)"
        }
    
    def generate_compose_file(self, certificate: Dict[str, Any]) -> str:
        """
        Generate docker-compose.yml - FIXED for Windows
        - No networks (Windows compatibility)
        - Proper volume mount with bind
        - Only enabled services
        - Mock data folder mount
        """
        
        docker_config = certificate.get("docker", {})
        services = docker_config.get("services", {})
        
        compose = {
            "services": {},
            "volumes": {
                "license-data": {
                    "driver": "local",
                    "driver_opts": {
                        "type": "none",
                        "o": "bind",
                        "device": "C:/ProgramData/AILicenseDashboard/license"
                    }
                },
                "app-data": {
                    "driver": "local",
                    "driver_opts": {
                        "type": "none",
                        "o": "bind",
                        "device": "C:/ProgramData/AILicenseDashboard/data"  # ← Mock data folder
                    }
                }
            }
        }
        
        # Add ONLY enabled services
        for svc_name, svc_config in services.items():
            if svc_config.get("enabled"):  # Only if enabled!
                image = f"{svc_config['image']}:{svc_config['tag']}"
                
                service_def = {
                    "image": image,
                    "ports": [f"{svc_config['host_port']}:{svc_config['container_port']}"],
                    "restart": "unless-stopped",
                    "environment": [
                        "LICENSE_PATH=/var/license",
                        "DATA_PATH=/var/data",  # ← Add data path env
                        f"SERVICE_NAME={svc_name}",
                        f"TIER={certificate.get('tier', 'basic')}"
                    ],
                    "volumes": [
                        "license-data:/var/license:ro",  # License (read-only)
                        "app-data:/var/data"  # ← App data (read-write)
                    ]
                }
                
                # Add healthcheck for frontend
                if svc_name == "frontend":
                    service_def["healthcheck"] = {
                        "test": ["CMD", "wget", "-qO-", f"http://localhost:{svc_config['container_port']}/"],
                        "interval": "30s",
                        "timeout": "5s",
                        "retries": 3
                    }
                
                # Backend depends on frontend
                if svc_name == "backend":
                    service_def["depends_on"] = ["frontend"]
                
                compose["services"][svc_name] = service_def
        
        # Convert to YAML
        import yaml
        return yaml.dump(compose, default_flow_style=False, sort_keys=False)
    
    def generate_activation_bundle(
        self,
        certificate: Dict[str, Any],
        machine_fingerprint: str,
        include_compose: bool = True
    ) -> Dict[str, Any]:
        """Generate complete activation bundle"""
        
        bundle = {
            "bundle_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "certificate": certificate,
        }
        
        if self.docker_pat:
            bundle["docker_credentials"] = self.generate_docker_credentials(machine_fingerprint)
        
        if include_compose:
            bundle["compose_file"] = self.generate_compose_file(certificate)
        
        public_key_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        bundle["public_key"] = public_key_pem
        
        return bundle
    
    def upgrade_certificate(
        self,
        old_certificate: Dict[str, Any],
        new_tier: Optional[str] = None,
        additional_days: Optional[int] = None,
        new_machine_limit: Optional[int] = None,
        additional_services: Optional[List[str]] = None,
        new_image_tags: Optional[Dict[str, str]] = None
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
            new_valid_until = old_valid_until + timedelta(days=additional_days)
            valid_days = (new_valid_until - datetime.now(timezone.utc)).days
        else:
            valid_days = (old_valid_until - datetime.now(timezone.utc)).days
        
        machine_limit = new_machine_limit or old_certificate["limits"]["max_machines"]
        
        old_docker_services = old_certificate.get("docker", {}).get("services", {})
        old_enabled = [svc for svc, cfg in old_docker_services.items() if cfg.get("enabled")]
        
        if additional_services:
            allowed_services = list(set(old_enabled + additional_services))
        else:
            allowed_services = self.TIER_SERVICES.get(tier, old_enabled)
        
        old_tags = {svc: cfg.get("tag") for svc, cfg in old_docker_services.items()}
        if new_image_tags:
            old_tags.update(new_image_tags)
        
        new_cert = self.generate_certificate(
            customer_id=customer_id,
            customer_name=customer_name,
            machine_fingerprint=machine_fingerprint,
            hostname=hostname,
            product_key=product_key,
            tier=tier,
            valid_days=valid_days,
            machine_limit=machine_limit,
            custom_services=allowed_services,
            custom_image_tags=old_tags,
            parent_cert_id=old_certificate["certificate_id"],
            metadata={
                "upgrade_from_tier": old_certificate["tier"],
                "upgrade_to_tier": tier,
                "upgrade_reason": "customer_upgrade",
                "upgraded_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        new_cert["upgrade_chain"]["upgrade_count"] = old_certificate["upgrade_chain"]["upgrade_count"] + 1
        
        return new_cert