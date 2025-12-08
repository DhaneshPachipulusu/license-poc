import requests
import json

url = "http://localhost:8000/api/v1/certificates/custom-generate"

data = {
    "customer_id": "98478a5e-55b9-4fd1-b840-a3a113fadcba",  # ← Real customer ID
    "machine_fingerprint": "6c9ea83e7ce10dc1a357a76f127a8c536a936be9f371a66ad2391963b664e98a30780632378c6c5648b9f0c1769cea5c076305f678fbc8f72a642c9029a2018a",  # ← Real fingerprint
    "hostname": "Dhanesh",
    "os_info": "Windows 11",
    "services": {
        "frontend": True,
        "backend": True,
        "analytics": False
    },
    "machine_limit": 5,
    "valid_days": 180,
    "max_models": 10,
    "max_data_gb": 200,
    "tier": "custom"
}

response = requests.post(url, json=data)

print("Status Code:", response.status_code)
print("\nResponse:")
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
    print("\n✅ Certificate generated successfully!")
else:
    print(response.text)