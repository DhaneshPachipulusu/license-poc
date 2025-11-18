#!/usr/bin/env python3

import os
import sys
import json
import time
import hashlib
import logging
import platform
import threading
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateparser

import requests
from flask import Flask, jsonify

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

# -------------------------------------------------------
# CONFIG
# -------------------------------------------------------
SERVER = os.environ.get("LIC_SERVER", "http://127.0.0.1:8000")
PUBLIC_KEY_URL = SERVER + "/public_key"
REGISTER_URL = SERVER + "/register"
VALIDATE_URL = SERVER + "/validate"

# Storage locations
if platform.system() == "Windows":
    BASE_DIR = os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "license_agent")
else:
    BASE_DIR = "/etc/license_agent"

LICENSE_PATH = os.path.join(BASE_DIR, "license.json")
PUBLIC_KEY_PATH = os.path.join(BASE_DIR, "public_key.pem")
LOCK_FLAG = os.path.join(BASE_DIR, "license_locked")
LOG_PATH = os.path.join(BASE_DIR, "agent.log")

HEARTBEAT_INTERVAL = 60 * 60     # 1 hour
LOCAL_CHECK_INTERVAL = 30        # 30 seconds

os.makedirs(BASE_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("license_agent")


# -------------------------------------------------------
# MACHINE FINGERPRINT
# -------------------------------------------------------
def get_mac_addresses():
    macs = set()
    try:
        import psutil
        for nic, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if getattr(addr, "family", None) == getattr(psutil.AF_LINK, "family", None):
                    macs.add(addr.address)
    except Exception:
        import uuid
        macs.add(':'.join(['%02x' % ((uuid.getnode() >> ele) & 0xff)
                           for ele in range(0, 8 * 6, 8)][::-1]))
    return sorted([m for m in macs if m != "00:00:00:00:00:00"])


def get_system_uuid():
    try:
        if platform.system() == "Windows":
            import subprocess
            out = subprocess.check_output(["wmic", "csproduct", "get", "UUID"], text=True)
            return out.split("\n")[1].strip()
    except:
        pass
    return ""


def compute_machine_id():
    macs = get_mac_addresses()
    sys_uuid = get_system_uuid()

    joined = "|".join(macs) + "|" + sys_uuid + "|" + platform.node()
    salt = "LIC_AGENT_V1"
    return hashlib.sha256((joined + salt).encode("utf-8")).hexdigest()


# -------------------------------------------------------
# CRYPTO HELPERS
# -------------------------------------------------------
def save_public_key(pem_text):
    # Clean formatting
    pem_text = pem_text.strip().replace("\\n", "\n").replace('"', '')
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(pem_text.encode("utf-8"))
    log.info("Public key saved.")


def load_public_key():
    if not os.path.exists(PUBLIC_KEY_PATH):
        return None
    with open(PUBLIC_KEY_PATH, "rb") as f:
        return f.read()


def verify_signature(public_key_bytes, license_obj):
    payload = license_obj.copy()
    sig = payload.pop("signature", None)
    if not sig:
        return False

    data = json.dumps(payload, sort_keys=True).encode("utf-8")
    from base64 import b64decode
    signature = b64decode(sig)

    public_key = serialization.load_pem_public_key(public_key_bytes)

    try:
        public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception as e:
        log.warning(f"Signature invalid: {e}")
        return False


# -------------------------------------------------------
# LICENSE OPERATIONS
# -------------------------------------------------------
def fetch_public_key():
    try:
        r = requests.get(PUBLIC_KEY_URL, timeout=10)
        r.raise_for_status()
        save_public_key(r.text)
        return True
    except Exception as e:
        log.error(f"Failed to fetch public key: {e}")
        return False


def register_with_server(customer="TestCustomer"):
    try:
        payload = {"customer": customer, "machine_id": compute_machine_id()}
        r = requests.post(REGISTER_URL, json=payload, timeout=10)
        r.raise_for_status()
        lic = r.json().get("license")
        with open(LICENSE_PATH, "w") as f:
            json.dump(lic, f, indent=2)
        log.info("Registered successfully.")
        return lic
    except Exception as e:
        log.error(f"Registration failed: {e}")
        return None


def load_license():
    if not os.path.exists(LICENSE_PATH):
        return None
    with open(LICENSE_PATH, "r") as f:
        return json.load(f)


def local_valid(license_obj):
    try:
        # signature
        pub = load_public_key()
        if not pub:
            return False, "no_public_key"

        if not verify_signature(pub, license_obj):
            return False, "bad_signature"

        # expiry
        valid_till = dateparser.isoparse(license_obj["valid_till"])
        now = datetime.now(timezone.utc)

        if now > valid_till:
            # maybe grace?
            grace = license_obj.get("grace_days", 0)
            if now <= valid_till + timedelta(days=grace):
                return True, "grace"
            return False, "expired"

        if license_obj.get("revoked"):
            return False, "revoked"

        return True, "ok"
    except Exception as e:
        return False, f"error:{e}"


def server_validate(license_obj):
    try:
        r = requests.post(VALIDATE_URL, json={"license": license_obj}, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return {"valid": False, "reason": "server_unreachable"}


def enforce_invalid():
    with open(LOCK_FLAG, "w") as f:
        f.write("locked")


def clear_enforcement():
    if os.path.exists(LOCK_FLAG):
        os.remove(LOCK_FLAG)


# -------------------------------------------------------
# BACKGROUND AGENT LOOP
# -------------------------------------------------------
def agent_loop(customer="TestCustomer"):
    # Ensure public key
    if not os.path.exists(PUBLIC_KEY_PATH):
        fetch_public_key()

    lic = load_license()
    if not lic:
        lic = register_with_server(customer)
        if not lic:
            return

    valid, reason = local_valid(lic)
    if not valid:
        enforce_invalid()
        return
    else:
        clear_enforcement()

    # optional server validation
    server_res = server_validate(lic)
    if not server_res.get("valid"):
        if server_res.get("reason") == "revoked":
            enforce_invalid()
            return

    clear_enforcement()


def agent_daemon(customer="TestCustomer"):
    log.info("Agent daemon started.")
    while True:
        try:
            agent_loop(customer)
        except Exception as e:
            log.error(f"Agent error: {e}")
        time.sleep(LOCAL_CHECK_INTERVAL)


# -------------------------------------------------------
# FLASK SIDECAR
# -------------------------------------------------------
app = Flask("license_sidecar")


@app.get("/license/status")
def side_status():
    lic = load_license()
    if not lic:
        return jsonify({"valid": False, "reason": "no_license"})

    valid, reason = local_valid(lic)
    return jsonify({
        "valid": valid,
        "reason": reason,
        "license": lic
    })


@app.get("/license/features")
def side_features():
    lic = load_license()
    if not lic:
        return jsonify({"features": {}, "valid": False})
    return jsonify({
        "features": lic.get("features", {}),
        "valid": True
    })


@app.get("/license/info")
def side_info():
    lic = load_license()
    return jsonify(lic if lic else {})


@app.get("/license/expiry")
def side_expiry():
    lic = load_license()
    if not lic:
        return jsonify({"valid": False})

    valid_till = dateparser.isoparse(lic["valid_till"])
    now = datetime.now(timezone.utc)
    remaining = (valid_till - now).total_seconds()

    return jsonify({
        "valid": remaining > 0,
        "remaining_seconds": max(0, remaining),
        "valid_till": lic["valid_till"]
    })


# -------------------------------------------------------
# MAIN ENTRYPOINT
# -------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--customer", default="TestCustomer")
    args = parser.parse_args()

    # Start agent loop in background
    t = threading.Thread(target=agent_daemon, args=(args.customer,), daemon=True)
    t.start()

    # Start local HTTP sidecar
    app.run(host="127.0.0.1", port=5050)
