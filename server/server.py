"""
FLEXIBLE server.py - Works with ANY Product Key Format
=======================================================
This version is flexible with product key validation.
It checks if the key EXISTS in database, not if format is perfect.

USE THIS VERSION - It's more practical!
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import json
import uuid

# Import your existing db functions
from db import (
    init_db,
    create_customer,
    get_customer_by_product_key,
    get_customer_by_id,
    get_all_customers,
    register_machine,
    get_machine_by_fingerprint,
    get_machine_by_id,
    count_active_machines,
    update_machine_last_seen,
    revoke_machine,
    log_action,
    generate_product_key
)

# Import advanced certificate generator
from certificate import AdvancedCertificateGenerator

app = FastAPI(
    title="Advanced License Server",
    description="License server with flexible product key validation",
    version="2.0-flexible"
)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Initialize certificate generator
PRIVATE_KEY = 'private_key.pem'
PUBLIC_KEY = 'public_key.pem'

cert_generator = AdvancedCertificateGenerator(PRIVATE_KEY)


# ==================== PYDANTIC MODELS ====================

class CreateCustomerRequest(BaseModel):
    company_name: str
    tier: str = "basic"
    machine_limit: int = 3
    valid_days: int = 365
    notes: Optional[str] = None


class ActivationRequest(BaseModel):
    product_key: str
    machine_fingerprint: str
    hostname: str
    os_info: Optional[str] = None
    app_version: Optional[str] = "1.0.0"


class ValidationRequest(BaseModel):
    certificate: Dict[str, Any]
    machine_fingerprint: str
    service: Optional[str] = None
    docker_image: Optional[str] = None


class UpgradeRequest(BaseModel):
    machine_fingerprint: str
    new_tier: Optional[str] = None
    additional_days: Optional[int] = None
    new_machine_limit: Optional[int] = None
    additional_services: Optional[List[str]] = None


# ==================== HELPER FUNCTIONS ====================

def get_tier_from_product_key(product_key: str) -> str:
    """Determine tier from product key - flexible matching"""
    key_upper = product_key.upper()
    
    if "TRIAL" in key_upper or "TRI" in key_upper:
        return "trial"
    elif "ENT" in key_upper or "ENTERPRISE" in key_upper:
        return "enterprise"
    elif "PRO" in key_upper:
        return "pro"
    else:
        return "basic"


# ==================== STARTUP ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database and certificate generator"""
    init_db()
    print("✓ Database initialized")
    print("✓ Certificate generator ready")
    print("✓ Flexible product key validation enabled")


# ==================== ADMIN ENDPOINTS ====================

@app.post("/api/v1/admin/customers")
async def create_customer_endpoint(req: CreateCustomerRequest, request: Request):
    """Create a new customer with product key"""
    
    customer = create_customer(
        company_name=req.company_name,
        machine_limit=req.machine_limit,
        valid_days=req.valid_days,
        allowed_services=["dashboard"]
    )
    
    log_action(
        action="customer_created",
        customer_id=customer['id'],
        details={
            "company_name": req.company_name,
            "tier": req.tier,
            "machine_limit": req.machine_limit
        },
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "success": True,
        "customer": customer,
        "tier": req.tier,
        "message": f"Customer created. Product key: {customer['product_key']}"
    }


@app.get("/api/v1/admin/customers")
async def list_customers():
    """List all customers"""
    customers = get_all_customers()
    return {"customers": customers}


@app.get("/api/v1/admin/customers/{customer_id}")
async def get_customer_details(customer_id: str):
    """Get customer details with machines"""
    from db import get_customer_machines
    
    customer = get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    
    machines = get_customer_machines(customer_id)
    
    return {
        "customer": customer,
        "machines": machines
    }


# ==================== ACTIVATION ENDPOINT ====================

@app.post('/api/v1/activate')
async def activate_machine(req: ActivationRequest, request: Request):
    """
    Activate a machine - FLEXIBLE product key validation.
    
    Just checks if product key EXISTS in database!
    """
    
    # Check if already activated
    existing = get_machine_by_fingerprint(req.machine_fingerprint)
    if existing:
        certificate = existing.get('certificate')
        if certificate and isinstance(certificate, str):
            certificate = json.loads(certificate)
        
        return {
            "success": True,
            "message": "Machine already activated",
            "certificate": certificate,
            "reactivation": True
        }
    
    # FLEXIBLE: Just check if product key exists in database
    customer = get_customer_by_product_key(req.product_key)
    if not customer:
        # Product key not found in database
        raise HTTPException(
            404, 
            f"Product key not found: {req.product_key}. "
            "Please check the key or create a customer first."
        )
    
    # Check if customer is revoked
    if customer.get('revoked'):
        raise HTTPException(403, "Customer license revoked")
    
    # Check machine limit
    active_count = count_active_machines(customer['id'])
    if active_count >= customer['machine_limit']:
        raise HTTPException(
            403, 
            f"Machine limit reached ({active_count}/{customer['machine_limit']})"
        )
    
    # Determine tier
    tier = get_tier_from_product_key(req.product_key)
    
    # Generate advanced certificate
    certificate = cert_generator.generate_certificate(
        customer_id=customer['id'],
        customer_name=customer['company_name'],
        machine_fingerprint=req.machine_fingerprint,
        hostname=req.hostname,
        product_key=req.product_key,
        tier=tier,
        valid_days=customer['valid_days'],
        machine_limit=customer['machine_limit'],
        metadata={
            "os_info": req.os_info,
            "app_version": req.app_version,
            "activated_from_ip": request.client.host if request.client else "unknown"
        }
    )
    
    # Save to database
    machine = register_machine(
        customer_id=customer['id'],
        fingerprint=req.machine_fingerprint,
        hostname=req.hostname,
        os_info=req.os_info,
        app_version=req.app_version,
        ip_address=request.client.host if request.client else None,
        certificate=certificate
    )
    
    # Log activation
    log_action(
        action="machine_activated",
        customer_id=customer['id'],
        machine_id=machine['id'],
        details={
            "hostname": req.hostname,
            "tier": tier,
            "certificate_id": certificate['certificate_id']
        },
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "success": True,
        "message": f"✓ Activation successful! ({active_count + 1}/{customer['machine_limit']} machines) - {tier.upper()} tier",
        "certificate": certificate,
        "tier": tier,
        "customer_name": customer['company_name']
    }


# ==================== VALIDATION ENDPOINT ====================

@app.post('/api/v1/validate')
async def validate_certificate(req: ValidationRequest):
    """Validate certificate"""
    
    certificate = req.certificate
    
    cert_fingerprint = certificate.get("machine", {}).get("machine_fingerprint") or \
                       certificate.get("machine_fingerprint")
    
    if not cert_fingerprint:
        return {"valid": False, "reason": "missing_fingerprint"}
    
    if cert_fingerprint != req.machine_fingerprint:
        return {"valid": False, "reason": "fingerprint_mismatch"}
    
    machine = get_machine_by_fingerprint(req.machine_fingerprint)
    if not machine:
        return {"valid": False, "reason": "machine_not_found"}
    
    if machine.get('status') == 'revoked':
        return {"valid": False, "reason": "revoked"}
    
    # Check expiry
    validity = certificate.get("validity") or {}
    valid_until_str = validity.get("valid_until") or certificate.get("valid_till")
    
    if valid_until_str:
        from dateutil import parser
        valid_until = parser.isoparse(valid_until_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        
        if now > valid_until:
            return {"valid": False, "reason": "expired"}
    
    # Check service permission
    if req.service and "services" in certificate:
        service_config = certificate["services"].get(req.service)
        if not service_config or not service_config.get("enabled"):
            return {
                "valid": False,
                "reason": f"service_{req.service}_not_allowed"
            }
    
    # Check Docker image
    if req.docker_image and "docker" in certificate:
        docker_config = certificate["docker"]
        allowed_images = []
        
        for registry_config in docker_config.get("registries", {}).values():
            for img in registry_config.get("allowed_images", []):
                allowed_images.append(img["image"])
        
        if req.docker_image not in allowed_images:
            return {
                "valid": False,
                "reason": f"docker_image_{req.docker_image}_not_allowed"
            }
    
    update_machine_last_seen(machine['id'])
    
    return {
        "valid": True,
        "reason": "ok",
        "tier": certificate.get("tier"),
        "expires_at": valid_until_str
    }


# ==================== UPGRADE ENDPOINT ====================

@app.post('/api/v1/upgrade')
async def upgrade_certificate(req: UpgradeRequest, request: Request):
    """Upgrade certificate"""
    
    machine = get_machine_by_fingerprint(req.machine_fingerprint)
    if not machine:
        raise HTTPException(404, "Machine not found")
    
    old_certificate = machine.get('certificate')
    if isinstance(old_certificate, str):
        old_certificate = json.loads(old_certificate)
    
    if not old_certificate:
        raise HTTPException(400, "No certificate found for machine")
    
    new_certificate = cert_generator.upgrade_certificate(
        old_certificate=old_certificate,
        new_tier=req.new_tier,
        additional_days=req.additional_days,
        new_machine_limit=req.new_machine_limit,
        additional_services=req.additional_services
    )
    
    from db import update_license
    update_license(machine['machine_id'], new_certificate)
    
    log_action(
        action="certificate_upgraded",
        customer_id=machine['customer_id'],
        machine_id=machine['id'],
        details={
            "old_tier": old_certificate.get("tier"),
            "new_tier": new_certificate.get("tier")
        },
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "success": True,
        "message": "✓ Certificate upgraded successfully!",
        "old_tier": old_certificate.get("tier"),
        "new_tier": new_certificate.get("tier"),
        "certificate": new_certificate
    }


# ==================== UTILITY ENDPOINTS ====================

@app.get("/api/v1/public-key", response_class=PlainTextResponse)
async def get_public_key():
    """Get RSA public key"""
    with open(PUBLIC_KEY, "r") as f:
        return f.read()


@app.post("/api/v1/heartbeat")
async def heartbeat(machine_fingerprint: str):
    """Heartbeat"""
    machine = get_machine_by_fingerprint(machine_fingerprint)
    if machine:
        update_machine_last_seen(machine['id'])
        return {"status": "ok"}
    return {"status": "not_found"}


@app.post("/api/v1/admin/revoke/{machine_id}")
async def revoke_machine_endpoint(machine_id: str, request: Request):
    """Revoke machine"""
    machine = get_machine_by_id(machine_id)
    if not machine:
        raise HTTPException(404, "Machine not found")
    
    revoke_machine(machine_id)
    
    log_action(
        action="machine_revoked",
        customer_id=machine['customer_id'],
        machine_id=machine_id,
        ip_address=request.client.host if request.client else None
    )
    
    return {"success": True, "message": "Machine revoked"}


@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "version": "2.0-flexible",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint with helpful info"""
    return {
        "service": "Advanced License Server",
        "version": "2.0-flexible",
        "status": "running",
        "features": [
            "Flexible product key validation",
            "Service permissions",
            "Docker image access control",
            "Certificate upgrades",
            "Multi-tier licensing"
        ],
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)