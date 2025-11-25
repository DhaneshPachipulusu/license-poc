
import json
from certificate import AdvancedCertificateGenerator

# Load cert from license folder
with open('C:/ProgramData/AILicenseDashboard/license/certificate.json', 'r') as f:
    cert = json.load(f)

# Try to verify with server's current keys
gen = AdvancedCertificateGenerator('private_key.pem')

# Manual verification
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

with open('public_key.pem', 'rb') as f:
    pub_key = serialization.load_pem_public_key(f.read(), backend=default_backend())

signature = base64.b64decode(cert['signature'])
cert_copy = cert.copy()
cert_copy.pop('signature', None)
cert_copy.pop('signature_timestamp', None)
cert_bytes = json.dumps(cert_copy, sort_keys=True).encode()

try:
    pub_key.verify(signature, cert_bytes, padding.PSS(mgf=padding.MGF1(hashes.SHA512()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA512())
    print('SERVER CAN VERIFY: YES')
except Exception as e:
    print(f'SERVER CAN VERIFY: NO - {e}')
