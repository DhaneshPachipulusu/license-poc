from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from signer import generate_keys, sign_data, verify_signature
from models import RegisterRequest, LicenseResponse, RevokeRequest, ValidateRequest, RenewRequest
from db import (
    init_db,
    save_license,
    get_license_by_machine,
    get_license_by_id,
    revoke_license,
    update_license,
    get_all_licenses,
    # NEW: Activation tracking
    get_activations_count,
    save_activation,
    get_customer_activations,
    deactivate_machine,
    update_heartbeat
)

import json
import uuid
from datetime import datetime, timedelta, timezone
from dateutil import parser

PRIVATE_KEY = 'private_key.pem'
PUBLIC_KEY = 'public_key.pem'

# Configuration
MAX_ACTIVATIONS_PER_LICENSE = 3  # Maximum machines per customer

app = FastAPI(title='License Server PoC')

# Initialize DB
init_db()

# Generate RSA keys if needed
try:
    open(PRIVATE_KEY, 'rb')
except FileNotFoundError:
    generate_keys(PRIVATE_KEY, PUBLIC_KEY)


# ---------------------------------------------------------
# REGISTER LICENSE WITH ACTIVATION TRACKING
# ---------------------------------------------------------
@app.post('/register', response_model=LicenseResponse)
def register(req: RegisterRequest, request: Request):
    """
    Register a new license or return existing one
    Enforces activation limits per customer
    """
    machine_id = req.machine_id
    customer = req.customer

    # Check activation limit FIRST
    current_activations = get_activations_count(customer)
    
    print(f"📊 Customer '{customer}' has {current_activations}/{MAX_ACTIVATIONS_PER_LICENSE} activations")
    
    # If machine already has a license → return it
    existing = get_license_by_machine(machine_id)
    if existing:
        print(f"✅ Machine {machine_id} already has license: {existing['license_id']}")
        
        # Update heartbeat
        save_activation(
            existing['license_id'], 
            machine_id, 
            customer,
            ip_address=request.client.host
        )
        
        return {
            "license_id": existing["license_id"],
            "license": existing["license_json"]
        }

    # Check if customer has reached activation limit
    if current_activations >= MAX_ACTIVATIONS_PER_LICENSE:
        print(f"❌ Activation limit reached for customer '{customer}'")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "activation_limit_exceeded",
                "message": f"This license is already activated on {MAX_ACTIVATIONS_PER_LICENSE} machines. "
                          f"Please deactivate a machine or contact support to upgrade your plan.",
                "current_activations": current_activations,
                "max_activations": MAX_ACTIVATIONS_PER_LICENSE
            }
        )

    # Create new license
    license_id = "LIC-" + uuid.uuid4().hex[:12]
    issued = datetime.utcnow()

    lic = {
        "license_id": license_id,
        "customer": customer,
        "machine_id": machine_id,
        "issued_on": issued.isoformat() + "Z",
        "valid_till": (issued + timedelta(days=30)).isoformat() + "Z",
        "grace_days": 7,
        "features": {
            "moduleA": True,
            "moduleB": False
        },
        "allowed_services": ["frontend"],
        "revoked": False
    }

    # Sign the license
    payload = json.dumps(lic, sort_keys=True).encode("utf-8")
    signature = sign_data(PRIVATE_KEY, payload)
    lic["signature"] = signature

    # Save license
    save_license(license_id, customer, machine_id, lic)
    
    # Track activation
    save_activation(
        license_id, 
        machine_id, 
        customer,
        ip_address=request.client.host
    )

    print(f"✅ New license created: {license_id} for {customer} (machine: {machine_id})")
    
    return {
        "license_id": license_id,
        "license": lic
    }


# ---------------------------------------------------------
# VALIDATE LICENSE
# ---------------------------------------------------------
@app.post('/validate')
def validate(req: ValidateRequest):
    """Validate a license"""
    client_lic = req.license
    machine_id = client_lic.get("machine_id")
    license_id = client_lic.get("license_id")

    if not machine_id:
        raise HTTPException(400, "Missing machine_id")

    # Lookup DB license
    db_entry = get_license_by_machine(machine_id)
    if db_entry is None and license_id:
        db_entry = get_license_by_id(license_id)

    if db_entry is None:
        return {"valid": False, "reason": "license_not_found"}

    lic = db_entry["license_json"]

    # Check revoked
    if db_entry["revoked"]:
        return {"valid": False, "reason": "revoked"}

    # Check machine ID match
    if lic.get("machine_id") != machine_id:
        return {"valid": False, "reason": "machine_mismatch"}

    # Check expiry
    valid_till = parser.isoparse(lic["valid_till"])
    now = datetime.now(timezone.utc)
    if now > valid_till:
        return {"valid": False, "reason": "expired"}

    # Signature verification
    lic_copy = lic.copy()
    signature = lic_copy.pop("signature")
    payload = json.dumps(lic_copy, sort_keys=True).encode("utf-8")

    if not verify_signature(PUBLIC_KEY, payload, signature):
        return {"valid": False, "reason": "invalid_signature"}

    # Service validation (optional)
    if "allowed_services" in lic:
        service = client_lic.get("service", None)
        if service and service not in lic["allowed_services"]:
            return {"valid": False, "reason": "service_not_allowed"}

    return {"valid": True, "reason": "ok"}


# ---------------------------------------------------------
# HEARTBEAT (NEW)
# ---------------------------------------------------------
@app.post("/heartbeat")
def heartbeat(data: dict):
    """
    Receive heartbeat from client
    Updates last_seen timestamp
    """
    license_id = data.get("license_id")
    machine_id = data.get("machine_id")
    
    if not license_id or not machine_id:
        raise HTTPException(400, "Missing license_id or machine_id")
    
    update_heartbeat(license_id, machine_id)
    
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ---------------------------------------------------------
# RENEW LICENSE
# ---------------------------------------------------------
@app.post("/renew")
def renew(req: RenewRequest):
    """Renew a license by extending validity"""
    lic = get_license_by_id(req.license_id)
    if not lic:
        raise HTTPException(404, "License not found")

    lic_obj = lic["license_json"]

    old_valid = parser.isoparse(lic_obj["valid_till"])
    new_valid = old_valid + timedelta(days=req.extend_days)
    lic_obj["valid_till"] = new_valid.isoformat() + "Z"

    # Re-sign
    payload = json.dumps(lic_obj, sort_keys=True).encode("utf-8")
    signature = sign_data(PRIVATE_KEY, payload)
    lic_obj["signature"] = signature

    update_license(req.license_id, lic_obj)

    return {"status": "renewed", "license": lic_obj}


# ---------------------------------------------------------
# REVOKE
# ---------------------------------------------------------
@app.post("/revoke")
def revoke(req: RevokeRequest):
    """Revoke a license"""
    revoke_license(req.license_id)
    return {"revoked": True}


# ---------------------------------------------------------
# PUBLIC KEY
# ---------------------------------------------------------
@app.get("/public_key", response_class=PlainTextResponse)
def public_key():
    """Return public key for signature verification"""
    with open(PUBLIC_KEY, "r") as f:
        return f.read()


# ---------------------------------------------------------
# ADMIN DASHBOARD
# ---------------------------------------------------------
templates = Jinja2Templates(directory="templates")


@app.get("/admin/licenses", response_class=HTMLResponse)
def admin_list(request: Request):
    """List all licenses"""
    licenses = get_all_licenses()
    return templates.TemplateResponse("licenses.html", {"request": request, "licenses": licenses})


@app.get("/admin/license/{license_id}", response_class=HTMLResponse)
def admin_view_license(request: Request, license_id: str):
    """View license details"""
    lic = get_license_by_id(license_id)
    if not lic:
        return HTMLResponse("License not found", status_code=404)
    return templates.TemplateResponse("license_view.html", {"request": request, "lic": lic})


@app.post("/admin/renew")
def admin_renew(
    request: Request,
    license_id: str = Form(...),
    extend_days: int = Form(...)
):
    """Admin renew license"""
    lic = get_license_by_id(license_id)
    if not lic:
        raise HTTPException(404, "License not found")

    lic_obj = lic["license_json"]

    # Fix timezone format
    raw = lic_obj["valid_till"]
    raw = raw.replace("+00:00Z", "Z")
    if raw.endswith("Z"):
        raw = raw.replace("Z", "+00:00")

    old_valid = parser.isoparse(raw)
    new_valid = old_valid + timedelta(days=extend_days)
    lic_obj["valid_till"] = new_valid.isoformat() + "Z"

    # Re-sign
    payload = json.dumps(lic_obj, sort_keys=True).encode("utf-8")
    signature = sign_data(PRIVATE_KEY, payload)
    lic_obj["signature"] = signature

    update_license(license_id, lic_obj)

    return RedirectResponse("/admin/licenses", status_code=302)


@app.get("/admin/revoke/{license_id}")
def admin_revoke(license_id: str):
    """Admin revoke license"""
    revoke_license(license_id)
    return RedirectResponse("/admin/licenses", status_code=302)


# ---------------------------------------------------------
# ACTIVATION MANAGEMENT (NEW)
# ---------------------------------------------------------
@app.get("/admin/activations/{customer}")
def view_activations(customer: str):
    """View all activations for a customer"""
    activations = get_customer_activations(customer)
    count = get_activations_count(customer)
    
    return {
        "customer": customer,
        "total_activations": count,
        "max_activations": MAX_ACTIVATIONS_PER_LICENSE,
        "activations": activations
    }


@app.post("/admin/deactivate")
def admin_deactivate(customer: str = Form(...), machine_id: str = Form(...)):
    """Deactivate a specific machine"""
    success = deactivate_machine(customer, machine_id)
    
    if success:
        return {"status": "deactivated", "customer": customer, "machine_id": machine_id}
    else:
        raise HTTPException(404, "Activation not found")