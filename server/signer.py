# signer.py
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
import base64

KEY_SIZE = 2048


# ------------------------------------------------------------
# GENERATE RSA PRIVATE + PUBLIC KEYS
# ------------------------------------------------------------
def generate_keys(private_path='private_key.pem', public_path='public_key.pem'):
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=KEY_SIZE,
        backend=default_backend()
    )

    # Write private key to file
    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    with open(private_path, 'wb') as f:
        f.write(priv_bytes)

    # Generate and write public key
    pub = private_key.public_key()
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with open(public_path, 'wb') as f:
        f.write(pub_bytes)

    print('Keys generated:', private_path, public_path)


# ------------------------------------------------------------
# SIGN DATA USING PRIVATE KEY
# ------------------------------------------------------------
def sign_data(private_key_path, data_bytes: bytes) -> str:
    with open(private_key_path, 'rb') as f:
        priv = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )

    signature = priv.sign(
        data_bytes,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    return base64.b64encode(signature).decode('ascii')


# ------------------------------------------------------------
# VERIFY SIGNATURE USING PUBLIC KEY
# ------------------------------------------------------------
def verify_signature(public_key_path, data_bytes: bytes, signature_b64: str) -> bool:
    with open(public_key_path, 'rb') as f:
        pub = serialization.load_pem_public_key(
            f.read(),
            backend=default_backend()
        )

    sig = base64.b64decode(signature_b64)

    try:
        pub.verify(
            sig,
            data_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False
