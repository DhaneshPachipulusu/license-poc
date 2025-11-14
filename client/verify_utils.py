# verify_utils.py

import json
import hashlib
import base64
from signer import verify_signature


# ------------------------------------------------------------
# Load public key from server URL
# ------------------------------------------------------------
def load_public_key_from_url(url: str) -> str:
    import requests
    r = requests.get(url)
    r.raise_for_status()
    return r.text


# ------------------------------------------------------------
# Compute machine ID (POC)
# ------------------------------------------------------------
def compute_machine_id(mac='test-mac-00:11:22:33:44:55') -> str:
    # Simple deterministic ID for testing
    s = mac + '-fixed-salt'
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


# ------------------------------------------------------------
# Verify license signature (two modes supported)
#   1. public_key_path_or_pem = path to .pem file
#   2. public_key_path_or_pem = PEM text (string)
# ------------------------------------------------------------
def verify_license(public_key_path_or_pem, license_obj: dict) -> bool:
    payload = license_obj.copy()
    sig = payload.pop("signature", None)

    if sig is None:
        return False

    # Convert dict → JSON bytes
    data = json.dumps(payload, sort_keys=True).encode("utf-8")

    # If it's a file path, use verify_signature()
    try:
        with open(public_key_path_or_pem, "rb") as _:
            return verify_signature(
                public_key_path_or_pem,
                data,
                sig
            )
    except Exception:
        pass

    # Otherwise assume it's PEM text directly
    try:
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend

        pem_bytes = (
            public_key_path_or_pem.encode("utf-8")
            if isinstance(public_key_path_or_pem, str)
            else public_key_path_or_pem
        )

        public_key = serialization.load_pem_public_key(
            pem_bytes,
            backend=default_backend()
        )

        public_key.verify(
            base64.b64decode(sig),
            data,
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        return True

    except Exception:
        return False
