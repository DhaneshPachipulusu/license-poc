# fake_client.py
import requests
import json
import hashlib
import os
import time
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64


SERVER = os.environ.get('LIC_SERVER', 'http://127.0.0.1:8000')
PUBLIC_KEY_URL = SERVER + '/public_key'




def compute_machine_id(mac='test-mac-00:11:22:33:44:55') -> str:
    s = mac + '-fixed-salt'
    return hashlib.sha256(s.encode('utf-8')).hexdigest()




def fetch_public_key():
    r = requests.get(PUBLIC_KEY_URL)
    r.raise_for_status()
    return r.text




def register(customer='TestOrg'):
    mid = compute_machine_id()
    r = requests.post(SERVER + '/register', json={'customer': customer, 'machine_id': mid})
    r.raise_for_status()
    obj = r.json()
    lic = obj['license']
    with open('license.json', 'w') as f:
       json.dump(lic, f, indent=2)