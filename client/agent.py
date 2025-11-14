#!/usr/bin/env python3
"""
agent.py - Simple License Agent (PoC)

Features:
- Generate machine fingerprint (MAC + system UUID)
- Register with license server (/register)
- Save license.json to disk
- Verify signature locally using server public key (/public_key)
- Periodic validation (heartbeat) and offline grace handling
- Example enforcement: writes lock file if invalid
"""

import os
import sys
import json
import time
import hashlib
import logging
import platform
import requests
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateparser
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

# -----------------------
# Configuration (edit if needed)
# -----------------------
SERVER = os.environ.get("LIC_SERVER", "http://127.0.0.1:8000")
PUBLIC_KEY_URL = SERVER.rstrip("/") + "/public_key"
REGISTER_URL = SERVER.rstrip("/") + "/register"
VALIDATE_URL = SERVER.rstrip("/") + "/validate"
RENEW_URL = SERVER.rstrip("/") + "/renew"   # optional if you implement

# Persistent location for license on different OS
if platform.system() == "Windows":
    LICENSE_DIR = os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "license_agent")
else:
    LICENSE_DIR = "/etc/license_agent"  # use /var/lib/... on real deployments

LICENSE_PATH = os.path.join(LICENSE_DIR, "license.json")
PUBLIC_KEY_PATH = os.path.join(LICENSE_DIR, "public_key.pem")
LOG_PATH = os.path.join(LICENSE_DIR, "agent.log")
LOCK_FLAG = os.path.join(LICENSE_DIR, "license_locked")

# How often to heartbeat (seconds)
HEARTBEAT_INTERVAL = 60 * 60    # 1 hour
# How often to try online registration when no license (seconds)
REGISTER_RETRY = 60             # 1 minute
# How often to check locally (seconds)
LOCAL_CHECK_INTERVAL = 30       # 30 sec

# Setup logging
os.makedirs(LICENSE_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[
                        logging.FileHandler(LOG_PATH),
                        logging.StreamHandler(sys.stdout)
                    ])
log = logging.getLogger("license_agent")


# -----------------------
# Machine fingerprint
# -----------------------
def get_mac_addresses():
    macs = set()
    try:
        import psutil
        for nic, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if getattr(addr, "family", None) == getattr(psutil.AF_LINK, "family", None) or addr.family.name == 'AF_LINK' if hasattr(addr.family, 'name') else False:
                    macs.add(addr.address)
    except Exception:
        # fallback: use uuid.getnode
        import uuid
        macs.add(':'.join(['%02x' % ((uuid.getnode() >> ele) & 0xff)
                           for ele in range(0,8*6,8)][::-1]))
    return [m for m in macs if m and m != "00:00:00:00:00:00"]


def get_system_uuid():
    try:
        system = platform.system()
        if system == "Windows":
            # wmic may be deprecated on some Windows but still often present
            import subprocess
            out = subprocess.check_output(["wmic", "csproduct", "get", "UUID"], text=True).splitlines()
            for line in out:
                line = line.strip()
                if line and line.lower() != "uuid":
                    return line
        elif system == "Linux":
            for p in ("/sys/class/dmi/id/product_uuid", "/sys/class/dmi/id/product_serial"):
                if os.path.exists(p):
                    with open(p, "r") as f:
                        s = f.read().strip()
                        if s:
                            return s
        elif system == "Darwin":
            import subprocess
            out = subprocess.check_output(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], text=True)
            for line in out.splitlines():
                if "IOPlatformUUID" in line:
                    return line.split('=')[-1].strip().strip('\"')
    except Exception as e:
        log.debug("system uuid error: %s", e)
    return None


def compute_machine_id():
    macs = get_mac_addresses()
    sys_uuid = get_system_uuid() or ""
    # sort macs to be deterministic
    macs_sorted = sorted(macs)
    joined = "|".join(macs_sorted) + "|" + sys_uuid + "|" + platform.node()
    # add a salt
    salt = "LIC_AGENT_V1"
    h = hashlib.sha256((joined + salt).encode("utf-8")).hexdigest()
    return h


# -----------------------
# Cryptography helpers
# -----------------------

def save_public_key(pem_text: str):
    # Remove quotes if present
    if pem_text.startswith('"') and pem_text.endswith('"'):
        pem_text = pem_text[1:-1]

    # Convert literal "\n" to actual newlines
    pem_text = pem_text.replace("\\n", "\n")

    # Save in binary mode
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(pem_text.encode("utf-8"))


def load_public_key():
    if not os.path.exists(PUBLIC_KEY_PATH):
        return None
    with open(PUBLIC_KEY_PATH, "rb") as f:
        return f.read()


def verify_signature_with_pem(public_pem_bytes: bytes, license_obj: dict) -> bool:
    payload = license_obj.copy()
    signature_b64 = payload.pop("signature", None)
    if signature_b64 is None:
        log.warning("No signature present in license")
        return False
    data = json.dumps(payload, sort_keys=True).encode("utf-8")
    from base64 import b64decode
    sig = b64decode(signature_b64)
    public_key = serialization.load_pem_public_key(public_pem_bytes)
    try:
        public_key.verify(sig, data, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception as e:
        log.warning("Signature verify failed: %s", e)
        return False


# -----------------------
# Server interactions
# -----------------------
def fetch_public_key_from_server():
    try:
        r = requests.get(PUBLIC_KEY_URL, timeout=10)
        r.raise_for_status()
        save_public_key(r.text)
        log.info("Fetched public key from server")
        return r.text
    except Exception as e:
        log.error("Failed to fetch public key: %s", e)
        return None


def register_with_server(customer_name="TestCustomer"):
    machine_id = compute_machine_id()
    payload = {"customer": customer_name, "machine_id": machine_id}
    try:
        r = requests.post(REGISTER_URL, json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        license_obj = data.get("license")
        if license_obj:
            with open(LICENSE_PATH, "w", encoding="utf-8") as f:
                json.dump(license_obj, f, indent=2)
            log.info("Registered and saved license to %s", LICENSE_PATH)
            return license_obj
    except Exception as e:
        log.error("Registration failed: %s", e)
    return None


def server_validate(license_obj):
    try:
        r = requests.post(VALIDATE_URL, json={"license": license_obj}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("Server-side validate failed: %s", e)
        return {"valid": False, "reason": "server_unreachable"}


# -----------------------
# Local verification & enforcement
# -----------------------
def load_local_license():
    if not os.path.exists(LICENSE_PATH):
        return None
    with open(LICENSE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def is_license_expired(license_obj):
    try:
        valid_till = dateparser.isoparse(license_obj.get("valid_till"))
        now = datetime.now(timezone.utc)
        return now > valid_till
    except Exception:
        return True


def is_within_grace(license_obj):
    try:
        # if expired, allow grace_days more
        valid_till = dateparser.isoparse(license_obj.get("valid_till"))
        grace = int(license_obj.get("grace_days", 0))
        limit = valid_till + timedelta(days=grace)
        now = datetime.now(timezone.utc)
        return now <= limit
    except Exception:
        return False


def enforce_invalid():
    # Example enforcement: create a lock file that your app checks before starting
    try:
        with open(LOCK_FLAG, "w", encoding="utf-8") as f:
            f.write("license_invalid\n")
        log.warning("License invalid — enforcement applied (lock file created).")
    except Exception as e:
        log.error("Could not write lock flag: %s", e)


def remove_enforcement():
    try:
        if os.path.exists(LOCK_FLAG):
            os.remove(LOCK_FLAG)
            log.info("Removed lock flag.")
    except Exception as e:
        log.error("Could not remove lock flag: %s", e)


# -----------------------
# Main agent loop
# -----------------------
def agent_loop(customer_name="TestCustomer"):
    # Ensure we have public key
    if not os.path.exists(PUBLIC_KEY_PATH):
        fetch_public_key_from_server()

    # If no local license, try to register
    license_obj = load_local_license()
    if license_obj is None:
        log.info("No local license found, attempting registration...")
        license_obj = register_with_server(customer_name)
        if license_obj is None:
            log.error("Registration attempt failed. Will retry later.")
            time.sleep(REGISTER_RETRY)
            return

    # Verify signature locally
    public_pem = load_public_key()
    if public_pem is None:
        log.error("No public key available to verify license.")
        return

    sig_ok = verify_signature_with_pem(public_pem, license_obj)
    if not sig_ok:
        log.error("Local signature verification failed.")
        enforce_invalid()
        return

    # Local expiration check
    if is_license_expired(license_obj):
        if is_within_grace(license_obj):
            log.warning("License expired but within grace period.")
        else:
            log.error("License expired and grace period exceeded.")
            enforce_invalid()
            return
    else:
        remove_enforcement()

    # Try online validation (best-effort)
    server_result = server_validate(license_obj)
    if server_result.get("valid"):
        log.info("Server validation: valid")
        remove_enforcement()
    else:
        reason = server_result.get("reason")
        log.warning("Server validation returned invalid or unreachable (%s).", reason)
        # If server unreachable, we allow offline mode until grace expires (already checked)
        if reason == "revoked":
            enforce_invalid()
            return

    # Save maybe-updated license (server could send revocation/updates later)
    # (In our PoC server we don't auto-update license, but keep hook here)
    try:
        with open(LICENSE_PATH, "w", encoding="utf-8") as f:
            json.dump(license_obj, f, indent=2)
    except Exception as e:
        log.warning("Failed to re-save license: %s", e)


def run_daemon(customer_name="TestCustomer"):
    log.info("Starting license agent daemon (PoC).")
    # simple loop — in prod you'd run as a service, here we do periodic checks
    last_heartbeat = 0
    while True:
        try:
            agent_loop(customer_name)
        except Exception as e:
            log.exception("Agent loop error: %s", e)
        # Sleep until next iteration
        time.sleep(LOCAL_CHECK_INTERVAL)


# -----------------------
# CLI entrypoint
# -----------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="License Agent PoC")
    parser.add_argument("--customer", default="TestCustomer", help="Customer name to register")
    parser.add_argument("--once", action="store_true", help="Run one check and exit (non-daemon)")
    args = parser.parse_args()

    if args.once:
        agent_loop(args.customer)
        sys.exit(0)
    else:
        run_daemon(args.customer)
