from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    JSONResponse
)
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from signer import generate_keys, sign_data, verify_signature
from models import RegisterRequest, LicenseResponse, RevokeRequest, ValidateRequest, RenewRequest
from db import (
    init_db,
    save_license,
    get_license_by_machine,
    get_license_by_id,
    revoke_license,
    update_license,
    get_all_licenses
)

import json
import uuid
from datetime import datetime, timedelta, timezone
from dateutil import parser
from typing import List, Dict, Any


PRIVATE_KEY = 'private_key.pem'
PUBLIC_KEY = 'public_key.pem'

app = FastAPI(title='License Server PoC')

# Add CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
init_db()

# Generate RSA keys if needed
try:
    open(PRIVATE_KEY, 'rb')
except FileNotFoundError:
    generate_keys(PRIVATE_KEY, PUBLIC_KEY)


templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------
# REGISTER LICENSE
# ---------------------------------------------------------
@app.post('/register', response_model=LicenseResponse)
def register(req: RegisterRequest):
    machine_id = req.machine_id

    # If machine already has a license → return it
    existing = get_license_by_machine(machine_id)
    if existing:
        return {
            "license_id": existing["license_id"],
            "license": existing
        }

    license_id = "LIC-" + uuid.uuid4().hex[:12]
    issued = datetime.utcnow()

    lic = {
        "license_id": license_id,
        "customer": req.customer,
        "machine_id": machine_id,
        "issued_on": issued.isoformat() + "Z",
        "valid_till": (issued + timedelta(days=30)).isoformat() + "Z",
        "grace_days": 7,
        "features": {
            "moduleA": True,
            "moduleB": False
        },
        "allowed_services": ["frontend"],  # default
        "revoked": False
    }

    # Sign the license
    payload = json.dumps(lic, sort_keys=True).encode("utf-8")
    signature = sign_data(PRIVATE_KEY, payload)
    lic["signature"] = signature

    save_license(license_id, req.customer, machine_id, lic)

    return {
        "license_id": license_id,
        "license": lic
    }


@app.post('/validate')
def validate(req: ValidateRequest):
    client_lic = req.license   # untrusted
    machine_id = client_lic.get("machine_id")
    license_id = client_lic.get("license_id")

    if not machine_id:
        raise HTTPException(400, "Missing machine_id")

    # Lookup DB license
    db_entry = get_license_by_machine(machine_id)
    if db_entry is None and license_id:
        db_entry = get_license_by_id(license_id)

    if db_entry is None:
        raise HTTPException(404, "License not found")

    lic = db_entry["license_json"]   # The REAL source of truth

    # Check revoked
    if db_entry["revoked"]:
        return {"valid": False, "reason": "revoked"}

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
# RENEW LICENSE
# ---------------------------------------------------------
@app.post("/renew")
def renew(req: RenewRequest):
    lic = get_license_by_id(req.license_id)
    if not lic:
        raise HTTPException(404, "License not found")

    lic_obj = lic["license_json"]

    old_valid = parser.isoparse(lic_obj["valid_till"])
    new_valid = old_valid + timedelta(days=req.extend_days)
    lic_obj["valid_till"] = new_valid.isoformat() + "Z"

    # re-sign
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
    revoke_license(req.license_id)
    return {"revoked": True}


# ---------------------------------------------------------
# PUBLIC KEY (RAW PEM)
# ---------------------------------------------------------
@app.get("/public_key", response_class=PlainTextResponse)
def public_key():
    with open(PUBLIC_KEY, "r") as f:
        return f.read()


# ---------------------------------------------------------
# JSON API ENDPOINTS FOR NEXT.JS DASHBOARD
# ---------------------------------------------------------

@app.get("/admin/licenses/json")
def admin_licenses_json():
    """Get all licenses as JSON for Next.js dashboard"""
    licenses = get_all_licenses()
    return JSONResponse(content=licenses)


@app.get("/admin/license/{license_id}/json")
def admin_license_json(license_id: str):
    """Get single license as JSON"""
    lic = get_license_by_id(license_id)
    if not lic:
        raise HTTPException(404, "License not found")
    return JSONResponse(content=lic)


@app.get("/admin/stats")
def admin_stats():
    """Get dashboard statistics"""
    licenses = get_all_licenses()
    
    now = datetime.now(timezone.utc)
    active = 0
    expired = 0
    expiring_soon = 0
    
    for lic in licenses:
        if lic["revoked"]:
            continue
        valid_till = parser.isoparse(lic["license_json"]["valid_till"])
        days_left = (valid_till - now).days
        
        if days_left < 0:
            expired += 1
        elif days_left <= 7:
            expiring_soon += 1
        else:
            active += 1
    
    customers = set(lic["customer"] for lic in licenses)
    machines = set(lic["machine_id"] for lic in licenses)
    
    return {
        "total_licenses": len(licenses),
        "active_licenses": active,
        "expired_licenses": expired,
        "revoked_licenses": sum(1 for lic in licenses if lic["revoked"]),
        "total_customers": len(customers),
        "total_machines": len(machines),
        "expiring_soon": expiring_soon,
    }


@app.get("/admin/search")
def admin_search(q: str):
    """Search licenses by query"""
    licenses = get_all_licenses()
    query = q.lower()
    
    filtered = [
        lic for lic in licenses
        if query in lic["license_id"].lower()
        or query in lic["customer"].lower()
        or query in lic["machine_id"].lower()
    ]
    
    return JSONResponse(content=filtered)


@app.post("/admin/update-license")
def admin_update_license(data: Dict[str, Any]):
    """Update license details"""
    license_id = data.get("license_id")
    if not license_id:
        raise HTTPException(400, "Missing license_id")
    
    lic = get_license_by_id(license_id)
    if not lic:
        raise HTTPException(404, "License not found")
    
    lic_obj = lic["license_json"]
    
    # Update fields
    if "allowed_services" in data:
        lic_obj["allowed_services"] = data["allowed_services"]
    if "features" in data:
        lic_obj["features"] = data["features"]
    if "valid_till" in data:
        lic_obj["valid_till"] = data["valid_till"]
    if "grace_days" in data:
        lic_obj["grace_days"] = data["grace_days"]
    
    # Re-sign
    payload = json.dumps(lic_obj, sort_keys=True).encode("utf-8")
    signature = sign_data(PRIVATE_KEY, payload)
    lic_obj["signature"] = signature
    
    update_license(license_id, lic_obj)
    
    return {"status": "updated", "license": lic_obj}


# ---------------------------------------------------------
# HTML ADMIN DASHBOARD (Legacy - keeping for compatibility)
# ---------------------------------------------------------
@app.get("/admin/licenses", response_class=HTMLResponse)
def admin_list(request: Request):
    licenses = get_all_licenses()
    return templates.TemplateResponse("licenses.html", {"request": request, "licenses": licenses})


@app.get("/admin/license/{license_id}", response_class=HTMLResponse)
def admin_view_license(request: Request, license_id: str):
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

    # extend
    new_valid = old_valid + timedelta(days=extend_days)
    lic_obj["valid_till"] = new_valid.isoformat() + "Z"

    # re-sign
    payload = json.dumps(lic_obj, sort_keys=True).encode("utf-8")
    signature = sign_data(PRIVATE_KEY, payload)
    lic_obj["signature"] = signature

    update_license(license_id, lic_obj)

    return RedirectResponse("/admin/licenses", status_code=302)


@app.get("/admin/revoke/{license_id}")
def admin_revoke(license_id: str):
    revoke_license(license_id)
    return RedirectResponse("/admin/licenses", status_code=302)