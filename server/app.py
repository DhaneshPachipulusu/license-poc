# app.py

from fastapi import FastAPI, HTTPException
from signer import generate_keys, sign_data
from models import RegisterRequest, LicenseResponse, RevokeRequest, ValidateRequest
from db import init_db, save_license, get_license_by_machine, revoke_license
import json
import uuid
from datetime import datetime, timedelta
from datetime import timezone
from dateutil import parser



PRIVATE_KEY = 'private_key.pem'
PUBLIC_KEY = 'public_key.pem'

app = FastAPI(title='License Server PoC')

# Initialize DB & keys
init_db()

# Generate RSA keys if not present
try:
    open(PRIVATE_KEY, 'rb')
except FileNotFoundError:
    generate_keys(PRIVATE_KEY, PUBLIC_KEY)


# ------------------------------------------------------------
# REGISTER MACHINE
# ------------------------------------------------------------
@app.post('/register', response_model=LicenseResponse)
def register(req: RegisterRequest):

    # If existing license for machine, return it
    existing = get_license_by_machine(req.machine_id)
    if existing:
        return {
            'license_id': existing.get('license_id', 'unknown'),
            'license': existing
        }

    # Create new license
    license_id = 'LIC-' + uuid.uuid4().hex[:12]
    issued = datetime.utcnow()
    valid_days = 30

    lic = {
        'license_id': license_id,
        'customer': req.customer,
        'machine_id': req.machine_id,
        'issued_on': issued.isoformat() + 'Z',
        'valid_till': (issued + timedelta(days=valid_days)).isoformat() + 'Z',
        'grace_days': 7,
        'features': {
            'moduleA': True,
            'moduleB': False
        },
        'revoked': False
    }

    # Sign license
    payload = json.dumps(lic, sort_keys=True).encode('utf-8')
    signature = sign_data(PRIVATE_KEY, payload)
    lic['signature'] = signature

    # Save license to DB
    save_license(license_id, req.customer, req.machine_id, lic)

    return {
        'license_id': license_id,
        'license': lic
    }


# ------------------------------------------------------------
# VALIDATE LICENSE (improved)
# ------------------------------------------------------------
@app.post('/validate')
def validate(req: ValidateRequest):
    lic = req.license

    # Debugging — show what server received
    print("VALIDATE RECEIVED:", lic)

    machine_id = lic.get("machine_id")
    license_id = lic.get("license_id")

    if not machine_id:
        raise HTTPException(status_code=400, detail="Missing machine_id in license")

    # Lookup by machine_id
    db_lic = get_license_by_machine(machine_id)

    # If lookup failed, try searching by license_id (improved)
    if db_lic is None and license_id:
        print("Machine lookup failed, trying license_id fallback...")
        # Add a fallback DB lookup
        import sqlite3, json
        conn = sqlite3.connect("licenses.db")
        cur = conn.cursor()
        cur.execute("SELECT license_json FROM licenses WHERE id = ?", (license_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            db_lic = json.loads(row[0])

    # If still not found → return error with details
    if db_lic is None:
        raise HTTPException(
            status_code=404,
            detail=f"License not found for machine_id={machine_id} license_id={license_id}"
        )

    # Check revoked
    if db_lic.get('revoked'):
        return {'valid': False, 'reason': 'revoked'}

    now=datetime.now(timezone.utc)
    valid_till = parser.isoparse(lic.get('valid_till'))


    if now > valid_till:
        return {'valid': False, 'reason': 'expired'}

    # OPTIONAL: verify signature server-side to avoid tampering
    import json
    payload = lic.copy()
    signature = payload.pop('signature', None)
    payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')

    from signer import verify_signature
    if not verify_signature(PUBLIC_KEY, payload_bytes, signature):
        return {'valid': False, 'reason': 'invalid_signature'}

    return {'valid': True, 'reason': 'ok'}



# ------------------------------------------------------------
# REVOKE LICENSE
# ------------------------------------------------------------
@app.post('/revoke')
def revoke(req: RevokeRequest):
    revoke_license(req.license_id)
    return {'revoked': True}


# ------------------------------------------------------------
# RETURN PUBLIC KEY TO CLIENT
# ------------------------------------------------------------
@app.get('/public_key')
def public_key():
    with open(PUBLIC_KEY, 'rb') as f:
        return f.read().decode('utf-8')
