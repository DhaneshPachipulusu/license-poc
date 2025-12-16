"""
ADVANCED LICENSE SERVER v3.0
============================
Features:
- Dynamic compose generation
- Encrypted Docker credentials delivery
- Per-tier service control
- Activation bundle for .exe installer
"""

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import json
import uuid

# Import database functions
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
    update_machine_certificate,
    revoke_machine,
    log_action,
    generate_product_key
)

# Import certificate generator
from certificate import AdvancedCertificateGenerator

# ===========================================
# CONFIGURATION
# ===========================================

# Docker Hub PAT - Load from environment variable (secure)
DOCKER_PAT = os.environ.get("DOCKER_PAT", "")

# Key paths
PRIVATE_KEY = 'private_key.pem'
PUBLIC_KEY = 'public_key.pem'

# ===========================================
# APP INITIALIZATION
# ===========================================

app = FastAPI(
    title="Advanced License Server",
    description="License server with dynamic compose generation and encrypted Docker credentials",
    version="3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize certificate generator with Docker PAT
cert_generator = AdvancedCertificateGenerator(
    private_key_path=PRIVATE_KEY,
    docker_pat=DOCKER_PAT
)


# ===========================================
# PYDANTIC MODELS
# ===========================================

class CreateCustomerRequest(BaseModel):
    company_name: str
    tier: str = "basic"
    machine_limit: Optional[int] = None  # None = use tier default
    valid_days: Optional[int] = None  # None = use tier default
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
    new_image_tags: Optional[Dict[str, str]] = None


class UpdateImageTagsRequest(BaseModel):
    """Admin request to update image tags for a tier or customer"""
    tier: Optional[str] = None
    customer_id: Optional[str] = None
    image_tags: Dict[str, str]  # {"frontend": "v1.2.3", "backend": "v1.0.0"}


# ===========================================
# HELPER FUNCTIONS
# ===========================================

def get_tier_from_product_key(product_key: str) -> str:
    """Determine tier from product key prefix"""
    key_upper = product_key.upper()
    
    if "TRIAL" in key_upper or "TRI" in key_upper:
        return "trial"
    elif "ENT" in key_upper or "ENTERPRISE" in key_upper:
        return "enterprise"
    elif "PRO" in key_upper:
        return "pro"
    else:
        return "basic"


# ===========================================
# STARTUP EVENT
# ===========================================

@app.on_event("startup")
async def startup_event():
    """Initialize database and check configuration"""
    init_db()
    print("✓ Database initialized")
    print("✓ Certificate generator ready")
    
    if DOCKER_PAT:
        print("✓ Docker PAT configured")
    else:
        print("⚠ Docker PAT not configured - set DOCKER_PAT environment variable")
    
    print("✓ Server ready!")


# ===========================================
# ADMIN ENDPOINTS
# ===========================================

@app.post("/api/v1/admin/customers")
async def create_customer_endpoint(req: CreateCustomerRequest, request: Request):
    """Create a new customer with product key"""
    
    # Get tier defaults
    tier_limits = cert_generator.TIER_LIMITS.get(req.tier, cert_generator.TIER_LIMITS["basic"])
    
    machine_limit = req.machine_limit or tier_limits["max_machines"]
    valid_days = req.valid_days or tier_limits["valid_days"]
    
    customer = create_customer(
        company_name=req.company_name,
        machine_limit=machine_limit,
        valid_days=valid_days,
        allowed_services=cert_generator.TIER_SERVICES.get(req.tier, ["frontend"]),
        tier=req.tier  # ← FIX: Pass tier to database
    )
    
    log_action(
        action="customer_created",
        customer_id=customer['id'],
        details={
            "company_name": req.company_name,
            "tier": req.tier,
            "machine_limit": machine_limit,
            "valid_days": valid_days
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


@app.get("/api/v1/admin/tiers")
async def get_tier_info():
    """Get tier configuration info"""
    return {
        "tiers": cert_generator.TIER_LIMITS,
        "services_per_tier": cert_generator.TIER_SERVICES,
        "service_definitions": cert_generator.SERVICE_DEFINITIONS
    }


# ===========================================
# HEARTBEAT ENDPOINT (Revocation Check)
# ===========================================

@app.post("/api/v1/heartbeat")
async def heartbeat(request: Request):
    """Check if machine is still allowed (for revocation detection)"""
    
    try:
        body = await request.json()
        machine_fingerprint = body.get("machine_fingerprint")
        service_name = body.get("service_name", "unknown")
        
        if not machine_fingerprint:
            return {"valid": False, "reason": "missing_fingerprint"}
        
        # Get machine from database
        machine = get_machine_by_fingerprint(machine_fingerprint)
        
        if not machine:
            return {"valid": False, "reason": "machine_not_found"}
        
        # Check if machine is revoked
        if machine.get('status') != 'active':
            log_action(
                action="heartbeat_rejected_revoked",
                machine_id=machine['id'],
                details={"service": service_name, "status": machine.get('status')},
                ip_address=request.client.host if request.client else "unknown"
            )
            return {"valid": False, "reason": "machine_revoked"}
        
        # Check if customer is revoked
        customer = get_customer_by_id(machine['customer_id'])
        if not customer:
            return {"valid": False, "reason": "customer_not_found"}
        
        if customer.get('revoked'):
            log_action(
                action="heartbeat_rejected_customer_revoked",
                customer_id=customer['id'],
                machine_id=machine['id'],
                details={"service": service_name},
                ip_address=request.client.host if request.client else "unknown"
            )
            return {"valid": False, "reason": "customer_revoked"}
        
        # Update last_seen timestamp
        update_machine_last_seen(machine['id'])
        
        # Log successful heartbeat
        log_action(
            action="heartbeat_success",
            customer_id=customer['id'],
            machine_id=machine['id'],
            details={"service": service_name},
            ip_address=request.client.host if request.client else "unknown"
        )
        
        return {
            "valid": True,
            "reason": "ok",
            "customer_name": customer['company_name'],
            "tier": customer.get('tier', 'basic')
        }
    
    except Exception as e:
        print(f"Heartbeat error: {e}")
        return {"valid": False, "reason": "server_error"}


# ===========================================
# ACTIVATION ENDPOINT (Main endpoint for .exe)
# ===========================================

@app.post('/api/v1/activate')
async def activate_machine(req: ActivationRequest, request: Request):
    """
    Activate a machine and return complete activation bundle.
    
    Returns:
    - Certificate (signed, with service permissions)
    - Encrypted Docker credentials (AES-256-GCM, keyed to machine fingerprint)
    - Docker compose file (dynamically generated based on tier)
    - Public key for offline verification
    """
    
    # Check if already activated
    @app.post('/api/v1/activate')
    async def activate_machine(req: ActivationRequest, request: Request):
        """
        Activate a machine and return complete activation bundle.
        """
        
        # Check if already activated
        existing = get_machine_by_fingerprint(req.machine_fingerprint)
        if existing:
            # Check if SAME product key
            old_cert = existing.get('certificate')
            old_product_key = old_cert.get('customer', {}).get('product_key')
            
            if old_product_key != req.product_key:
                # Different key - reject!
                raise HTTPException(
                    403,
                    "This machine is already activated with a different product key"
                )
            
            # Same key - return existing activation
            return {
                "success": True,
                "message": f"✓ Machine already activated ({active_count}/{customer['machine_limit']} machines)",
                "bundle": bundle,  # ← SAME format as new activation
                "tier": tier,
                "customer_name": customer['company_name'],
                "services_enabled": [s for s, c in old_cert['docker']['services'].items() if c['enabled']]
                
            }
    
    # ... rest of activation code for NEW machines    
    # Validate product key
    customer = get_customer_by_product_key(req.product_key)
    if not customer:
        raise HTTPException(
            404, 
            f"Product key not found: {req.product_key}. "
            "Please check the key or contact support."
        )
    
    # Check if customer is revoked
    if customer.get('revoked'):
        raise HTTPException(403, "Customer license has been revoked")
    
    # Check machine limit
    active_count = count_active_machines(customer['id'])
    if active_count >= customer['machine_limit']:
        raise HTTPException(
            403, 
            f"Machine limit reached ({active_count}/{customer['machine_limit']}). "
            "Please revoke an existing machine or upgrade your license."
        )
    
    # Get tier from database (not from product key!)
    tier = customer.get('tier', 'basic')  # ← FIX: Read from database
    
    # Generate certificate
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
            "activated_from_ip": request.client.host if request.client else "unknown",
            "activation_timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    
    # Generate complete activation bundle
    bundle = cert_generator.generate_activation_bundle(
        certificate=certificate,
        machine_fingerprint=req.machine_fingerprint,
        include_compose=True
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
            "certificate_id": certificate['certificate_id'],
            "services_enabled": [s for s, c in certificate['docker']['services'].items() if c['enabled']]
        },
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "success": True,
        "message": f"✓ Activation successful! ({active_count + 1}/{customer['machine_limit']} machines)",
        "bundle": bundle,
        "tier": tier,
        "customer_name": customer['company_name'],
        "services_enabled": [s for s, c in certificate['docker']['services'].items() if c['enabled']]
    }
# ===========================================
# Custom Certificate Generation Endpoint
# ===========================================
@app.post("/api/v1/certificates/custom-generate")
async def generate_custom_certificate(request: Request):
    """
    Generate custom certificate with flexible configuration
    For B2B customers needing non-standard configs
    """
    data = await request.json()
    
    # Extract custom config
    customer_id = data.get('customer_id')
    machine_fingerprint = data.get('machine_fingerprint')
    hostname = data.get('hostname', 'unknown')
    
    # Custom services (checkboxes from UI)
    custom_services = data.get('services', {})
    # Example: {"frontend": True, "backend": True, "analytics": False}
    
    # Custom limits (from form inputs)
    machine_limit = data.get('machine_limit', 3)
    valid_days = data.get('valid_days', 365)
    max_models = data.get('max_models', 5)
    max_data_gb = data.get('max_data_gb', 100)
    
    # Version requirements (optional)
    min_versions = data.get('min_versions', {})
    
    # Get customer
    customer = get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    
    # Build custom tier name
    tier = data.get('tier', 'custom')
    
    # Generate certificate with custom config
    certificate = cert_generator.generate_certificate(
        customer_id=customer['id'],
        customer_name=customer['company_name'],
        machine_fingerprint=machine_fingerprint,
        hostname=hostname,
        product_key=customer['product_key'],
        tier=tier,
        valid_days=valid_days,
        machine_limit=machine_limit,
        metadata={
            "custom_generated": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "custom_services": custom_services,
            "max_models": max_models,
            "max_data_gb": max_data_gb
        }
    )
    
    # Override services with custom selection
    for service_name, enabled in custom_services.items():
        if service_name in certificate['docker']['services']:
            certificate['docker']['services'][service_name]['enabled'] = enabled
    
    # Add custom limits to certificate
    certificate['limits'] = {
        "max_models": max_models,
        "max_data_gb": max_data_gb,
        "max_concurrent_users": data.get('max_concurrent_users', 10)
    }
    
    # Add version requirements
    if min_versions:
        certificate['version_requirements'] = min_versions
    
    # Generate bundle
    bundle = cert_generator.generate_activation_bundle(
        certificate=certificate,
        machine_fingerprint=machine_fingerprint,
        include_compose=True
    )
    
    # Save to database (optional - for customer download later)
    if data.get('save_to_db', True):
        # Check if machine already exists
        existing_machine = get_machine_by_fingerprint(machine_fingerprint)
        if existing_machine:
            # Update existing
            update_machine_certificate(existing_machine['id'], certificate)
        else:
            # Create new
            register_machine(
                customer_id=customer['id'],
                fingerprint=machine_fingerprint,
                hostname=hostname,
                os_info=data.get('os_info', 'Unknown'),
                app_version="3.0",
                ip_address=request.client.host if request.client else None,
                certificate=certificate
            )
    
    # Log action
    log_action(
        action="custom_certificate_generated",
        customer_id=customer['id'],
        details={
            "tier": tier,
            "services": custom_services,
            "limits": certificate['limits'],
            "valid_days": valid_days
        },
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "success": True,
        "message": "Custom certificate generated",
        "certificate": certificate,
        "bundle": bundle,
        "download_filename": f"certificate_{customer['company_name']}_{hostname}.json"
    }
# ===========================================
# VALIDATION ENDPOINT
# ===========================================

@app.post('/api/v1/validate')
async def validate_certificate(req: ValidationRequest):
    """Validate certificate (used by Docker container on startup)"""
    
    certificate = req.certificate
    
    # Get fingerprint from certificate
    cert_fingerprint = certificate.get("machine", {}).get("machine_fingerprint") or \
                       certificate.get("machine_fingerprint")
    
    if not cert_fingerprint:
        return {"valid": False, "reason": "missing_fingerprint"}
    
    if cert_fingerprint != req.machine_fingerprint:
        return {"valid": False, "reason": "fingerprint_mismatch"}
    
    # Check database
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
            # Check grace period
            grace_days = validity.get("grace_period_days", 7)
            from datetime import timedelta
            grace_until = valid_until + timedelta(days=grace_days)
            
            if now > grace_until:
                return {"valid": False, "reason": "expired"}
            else:
                return {
                    "valid": True, 
                    "reason": "grace_period",
                    "message": f"License expired but within {grace_days}-day grace period"
                }
    
    # Check service permission
    if req.service:
        services = certificate.get("services", {})
        service_config = services.get(req.service)
        if not service_config or not service_config.get("enabled"):
            return {
                "valid": False,
                "reason": "service_not_allowed",
                "service": req.service
            }
    
    # Check Docker image permission
    if req.docker_image:
        docker_config = certificate.get("docker", {})
        services = docker_config.get("services", {})
        
        allowed_images = []
        for svc_name, svc_config in services.items():
            if svc_config.get("enabled"):
                allowed_images.append(f"{svc_config['image']}:{svc_config['tag']}")
        
        if req.docker_image not in allowed_images:
            return {
                "valid": False,
                "reason": "docker_image_not_allowed",
                "image": req.docker_image
            }
    
    # Update last seen
    update_machine_last_seen(machine['id'])
    
    return {
        "valid": True,
        "reason": "ok",
        "tier": certificate.get("tier"),
        "expires_at": valid_until_str,
        "services_enabled": [s for s, c in certificate.get("docker", {}).get("services", {}).items() if c.get("enabled")]
    }


# ===========================================
# UPGRADE ENDPOINT
# ===========================================

@app.post('/api/v1/upgrade')
async def upgrade_certificate(req: UpgradeRequest, request: Request):
    """Upgrade certificate (tier, validity, services)"""
    
    machine = get_machine_by_fingerprint(req.machine_fingerprint)
    if not machine:
        raise HTTPException(404, "Machine not found")
    
    old_certificate = machine.get('certificate')
    if isinstance(old_certificate, str):
        old_certificate = json.loads(old_certificate)
    
    if not old_certificate:
        raise HTTPException(400, "No certificate found for machine")
    
    # Generate upgraded certificate
    new_certificate = cert_generator.upgrade_certificate(
        old_certificate=old_certificate,
        new_tier=req.new_tier,
        additional_days=req.additional_days,
        new_machine_limit=req.new_machine_limit,
        additional_services=req.additional_services,
        new_image_tags=req.new_image_tags
    )
    
    # Generate new bundle
    bundle = cert_generator.generate_activation_bundle(
        certificate=new_certificate,
        machine_fingerprint=req.machine_fingerprint,
        include_compose=True
    )
    
    # Update database
    from db import update_license
    update_license(machine['machine_id'], new_certificate)
    
    log_action(
        action="certificate_upgraded",
        customer_id=machine['customer_id'],
        machine_id=machine['id'],
        details={
            "old_tier": old_certificate.get("tier"),
            "new_tier": new_certificate.get("tier"),
            "additional_days": req.additional_days,
            "new_services": req.additional_services
        },
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "success": True,
        "message": "✓ Certificate upgraded successfully!",
        "old_tier": old_certificate.get("tier"),
        "new_tier": new_certificate.get("tier"),
        "bundle": bundle
    }


# ===========================================
# COMPOSE ENDPOINT (Regenerate compose file)
# ===========================================

@app.get('/api/v1/compose/{machine_fingerprint}')
async def get_compose_file(machine_fingerprint: str):
    """Get docker-compose.yml for a machine"""
    
    machine = get_machine_by_fingerprint(machine_fingerprint)
    if not machine:
        raise HTTPException(404, "Machine not found")
    
    certificate = machine.get('certificate')
    if isinstance(certificate, str):
        certificate = json.loads(certificate)
    
    if not certificate:
        raise HTTPException(400, "No certificate found")
    
    compose_content = cert_generator.generate_compose_file(certificate)
    
    return PlainTextResponse(
        content=compose_content,
        media_type="application/x-yaml"
    )


# ===========================================
# UTILITY ENDPOINTS
# ===========================================

@app.get("/api/v1/public-key", response_class=PlainTextResponse)
async def get_public_key():
    """Get RSA public key for offline verification"""
    with open(PUBLIC_KEY, "r") as f:
        return f.read()


@app.post("/api/v1/heartbeat")
async def heartbeat(machine_fingerprint: str):
    """Heartbeat from client"""
    machine = get_machine_by_fingerprint(machine_fingerprint)
    if machine:
        update_machine_last_seen(machine['id'])
        return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
    return {"status": "not_found"}


@app.post("/api/v1/admin/revoke/{machine_id}")
async def revoke_machine_endpoint(machine_id: str, request: Request):
    """Revoke a machine's license"""
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
    
    return {"success": True, "message": "Machine license revoked"}


# ===========================================
# HEALTH & INFO ENDPOINTS
# ===========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "3.0",
        "docker_pat_configured": bool(DOCKER_PAT),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "service": "Advanced License Server",
        "version": "3.0",
        "status": "running",
        "features": [
            "Dynamic compose generation",
            "Encrypted Docker credentials",
            "Per-tier service control",
            "Certificate upgrades",
            "Offline validation support"
        ],
        "endpoints": {
            "activation": "POST /api/v1/activate",
            "validation": "POST /api/v1/validate",
            "upgrade": "POST /api/v1/upgrade",
            "compose": "GET /api/v1/compose/{fingerprint}",
            "public_key": "GET /api/v1/public-key"
        },
        "docs": "/docs"
    }

# ============================================================================
# DASHBOARD STATS ENDPOINT - ADD THIS TO server.py
# ============================================================================

# Add this import at the top with other db imports:
# from db import get_dashboard_stats, get_customers_summary, get_expiring_machines

# Then add these routes:

@app.get("/api/v1/dashboard/stats")
async def get_dashboard_statistics():
    """
    Get dashboard statistics
    
    Returns overall metrics for the admin dashboard:
    - Total customers
    - Active machines
    - Machines expiring soon (within 30 days)
    - Revoked machines
    - Expired machines
    """
    from db import get_dashboard_stats
    
    stats = get_dashboard_stats()
    return {
        "success": True,
        "stats": stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/v1/dashboard/customers-summary")
async def get_customers_summary_endpoint():
    """
    Get detailed summary of all customers with their machine statistics
    
    Returns list of customers with:
    - Customer info (name, product key, tier)
    - Machine counts (active, expired, revoked, expiring soon)
    """
    from db import get_customers_summary
    
    customers = get_customers_summary()
    
    return {
        "success": True,
        "customers": customers,
        "total": len(customers)
    }


@app.get("/api/v1/dashboard/expiring-machines")
async def get_expiring_machines_endpoint(days: int = 30):
    """
    Get machines expiring within specified days
    
    Query params:
        days: Number of days to look ahead (default 30)
    
    Returns list of machines expiring soon with:
    - Machine info
    - Customer info
    - Days remaining until expiry
    """
    from db import get_expiring_machines
    
    machines = get_expiring_machines(days=days)
    
    return {
        "success": True,
        "expiring_machines": machines,
        "total": len(machines),
        "days_threshold": days
    }


# ============================================================================
# ALTERNATIVE: COMBINED DASHBOARD ENDPOINT (ALL DATA AT ONCE)
# ============================================================================

@app.get("/api/v1/dashboard/overview")
async def get_dashboard_overview():
    """
    Get complete dashboard overview in one call
    
    Returns:
    - Statistics (totals)
    - Recent customers
    - Expiring machines
    """
    from db import (
        get_dashboard_stats,
        get_customers_summary,
        get_expiring_machines
    )
    
    stats = get_dashboard_stats()
    customers = get_customers_summary()
    expiring = get_expiring_machines(days=30)
    
    # Get only recent customers (last 5)
    recent_customers = customers[:5]
    
    return {
        "success": True,
        "stats": stats,
        "recent_customers": recent_customers,
        "expiring_machines": expiring,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
FRONTEND USAGE EXAMPLES:

1. Get just the stats (for dashboard cards):
   GET /api/v1/dashboard/stats
   
   Response:
   {
     "success": true,
     "stats": {
       "total_customers": 5,
       "active_machines": 3,
       "expiring_soon": 1,
       "revoked": 1,
       "expired": 2
     }
   }

2. Get customer summaries (for customers table):
   GET /api/v1/dashboard/customers-summary
   
   Response:
   {
     "success": true,
     "customers": [
       {
         "id": "...",
         "company_name": "ACME Corp",
         "product_key": "ACME-2025-...",
         "tier": "enterprise",
         "machine_stats": {
           "total": 2,
           "active": 2,
           "expired": 0,
           "revoked": 0,
           "expiring_soon": 0
         }
       }
     ]
   }

3. Get expiring machines (for alerts):
   GET /api/v1/dashboard/expiring-machines?days=30
   
   Response:
   {
     "success": true,
     "expiring_machines": [
       {
         "company_name": "Beta Inc",
         "hostname": "beta-machine-1",
         "expires_at": "2025-01-09T...",
         "days_remaining": 15
       }
     ]
   }

4. Get everything at once (one API call):
   GET /api/v1/dashboard/overview
   
   Response:
   {
     "success": true,
     "stats": {...},
     "recent_customers": [...],
     "expiring_machines": [...]
   }
"""
# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)