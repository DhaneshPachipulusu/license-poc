# LICENSE CONTROL SYSTEM - PHASE 1

**Status:** ✅ Complete - Ready to Test!

## 🎯 What Phase 1 Delivers

✅ Product key generation with validation  
✅ Machine fingerprinting support  
✅ Certificate generation with RSA signing  
✅ Activation API with machine limit enforcement  
✅ Validation API  
✅ Heartbeat API  
✅ Admin APIs for customer management  
✅ Audit logging  
✅ SQLite database with proper schema  

---

## 📁 Files Included

```
phase1/
├── server.py           → FastAPI server (main file)
├── db.py              → Database operations
├── models.py          → Pydantic models for validation
├── certificate.py     → Certificate generation & signing
├── db_schema.sql      → Database schema
├── requirements.txt   → Python dependencies
└── README.md          → This file
```

---

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
cd phase1
pip install -r requirements.txt
```

### Step 2: Initialize Database

```bash
# Database will auto-initialize on first run
# Or manually:
python -c "from db import init_db; init_db()"
```

### Step 3: Start Server

```bash
python server.py
```

Server will start at: http://localhost:8000

---

## 📊 API Endpoints

### **Activation (Main Endpoint)**

```http
POST /api/v1/activate
Content-Type: application/json

{
  "product_key": "TEST-2024-DEMO-ABC",
  "machine_fingerprint": "abc123xyz789...",
  "hostname": "OFFICE-PC",
  "os_info": "Windows 11 Pro",
  "app_version": "1.0.0"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "certificate": {
    "version": "1.0",
    "customer_id": "test-customer-001",
    "customer_name": "Test Company",
    "machine_id": "uuid...",
    "machine_fingerprint": "abc123...",
    "hostname": "OFFICE-PC",
    "product_key": "TEST-2024-DEMO-ABC",
    "issued_at": "2024-11-20T10:30:00+00:00",
    "valid_until": "2025-11-20T10:30:00+00:00",
    "allowed_services": ["dashboard", "analytics"],
    "metadata": {...},
    "signature": "hex..."
  },
  "message": "Activation successful (1/3 machines)"
}
```

**Error Response - Machine Limit (403):**
```json
{
  "success": false,
  "message": "Machine limit reached (3/3)",
  "error": "limit_exceeded",
  "active_machines": [
    {
      "hostname": "OFFICE-PC",
      "last_seen": "2024-11-20T09:00:00",
      "activated_at": "2024-11-15T10:00:00"
    },
    // ... more machines
  ]
}
```

---

### **Validation**

```http
POST /api/v1/validate
Content-Type: application/json

{
  "certificate": {
    "machine_id": "uuid",
    "machine_fingerprint": "abc123...",
    "signature": "...",
    ...
  }
}
```

**Response:**
```json
{
  "valid": true,
  "reason": "valid"
}
```

---

### **Heartbeat**

```http
POST /api/v1/heartbeat
Content-Type: application/json

{
  "machine_id": "uuid",
  "app_version": "1.0.0",
  "status": "running"
}
```

**Response:**
```json
{
  "status": "ok",
  "cert_update": null,
  "message": null
}
```

---

### **Public Key**

```http
GET /api/v1/public-key
```

Returns RSA public key in PEM format for client-side signature verification.

---

### **Admin - Create Customer**

```http
POST /api/v1/admin/customers
Content-Type: application/json

{
  "company_name": "Acme Corporation",
  "machine_limit": 5,
  "valid_days": 365,
  "allowed_services": ["dashboard", "analytics", "reports"],
  "notes": "Premium customer"
}
```

**Response:**
```json
{
  "id": "uuid",
  "company_name": "Acme Corporation",
  "product_key": "ACME-2024-X7H9-K2P",
  "machine_limit": 5,
  "valid_days": 365,
  "allowed_services": ["dashboard", "analytics", "reports"],
  "created_at": "2024-11-20T10:00:00",
  "updated_at": "2024-11-20T10:00:00",
  "revoked": false,
  "notes": "Premium customer"
}
```

---

### **Admin - List Customers**

```http
GET /api/v1/admin/customers
```

**Response:**
```json
[
  {
    "id": "uuid",
    "company_name": "Test Company",
    "product_key": "TEST-2024-DEMO-ABC",
    "machine_limit": 3,
    "active_machines": 2,
    "last_activity": "2024-11-20T09:00:00",
    "created_at": "2024-11-15T10:00:00",
    "revoked": false
  },
  // ... more customers
]
```

---

### **Admin - Get Customer Details**

```http
GET /api/v1/admin/customers/{customer_id}
```

**Response:**
```json
{
  "customer": {
    "id": "uuid",
    "company_name": "Test Company",
    "product_key": "TEST-2024-DEMO-ABC",
    "machine_limit": 3,
    "valid_days": 365,
    "allowed_services": ["dashboard"],
    "created_at": "2024-11-15T10:00:00",
    "revoked": false,
    "notes": null
  },
  "machines": [
    {
      "id": "machine-uuid",
      "hostname": "OFFICE-PC",
      "fingerprint": "abc123xyz...",
      "os_info": "Windows 11 Pro",
      "activated_at": "2024-11-15T10:30:00",
      "last_seen": "2024-11-20T09:00:00",
      "status": "active"
    },
    // ... more machines
  ]
}
```

---

### **Admin - Revoke Machine**

```http
POST /api/v1/admin/machines/{machine_id}/revoke
```

**Response:**
```json
{
  "success": true,
  "message": "Machine revoked"
}
```

---

### **Admin - Audit Log**

```http
GET /api/v1/admin/audit-log?customer_id=uuid&limit=50
```

---

## 🧪 Testing

### Test with cURL

**1. Create a customer:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/customers \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Corp",
    "machine_limit": 3,
    "valid_days": 365
  }'
```

**2. Activate first machine:**
```bash
curl -X POST http://localhost:8000/api/v1/activate \
  -H "Content-Type: application/json" \
  -d '{
    "product_key": "TEST-2024-DEMO-ABC",
    "machine_fingerprint": "fingerprint-machine-1",
    "hostname": "PC-001"
  }'
```

**3. Activate second machine:**
```bash
curl -X POST http://localhost:8000/api/v1/activate \
  -H "Content-Type: application/json" \
  -d '{
    "product_key": "TEST-2024-DEMO-ABC",
    "machine_fingerprint": "fingerprint-machine-2",
    "hostname": "LAPTOP-001"
  }'
```

**4. Try to exceed limit (will fail):**
```bash
# Activate machine 4 (limit is 3)
curl -X POST http://localhost:8000/api/v1/activate \
  -H "Content-Type: application/json" \
  -d '{
    "product_key": "TEST-2024-DEMO-ABC",
    "machine_fingerprint": "fingerprint-machine-4",
    "hostname": "PC-004"
  }'
```

### Test with Python

```python
import requests

API_URL = "http://localhost:8000/api/v1"

# 1. Create customer
response = requests.post(f"{API_URL}/admin/customers", json={
    "company_name": "My Company",
    "machine_limit": 2,
    "valid_days": 30
})
customer = response.json()
product_key = customer["product_key"]
print(f"Product Key: {product_key}")

# 2. Activate machine
response = requests.post(f"{API_URL}/activate", json={
    "product_key": product_key,
    "machine_fingerprint": "test-fingerprint-123",
    "hostname": "TEST-PC"
})
result = response.json()

if result["success"]:
    certificate = result["certificate"]
    print("✓ Activation successful!")
    print(f"Certificate: {certificate['machine_id']}")
else:
    print(f"✗ Activation failed: {result['message']}")
```

---

## 🔒 Security Features

### Product Key Validation
- Format: `CUST-YEAR-RAND-CHECK`
- Includes check digits to catch typos
- Example: `ACME-2024-X7H9-K2P`

### Certificate Signing
- RSA-2048 with SHA-256
- Private key on server (never shared)
- Public key distributed to clients
- Prevents certificate tampering

### Machine Fingerprinting
- Unique hardware-based identifier
- Prevents license copying
- Validated on each activation

### Machine Limits
- Configurable per customer
- Enforced server-side
- Returns active machines on limit exceeded

### Audit Logging
- Every action logged
- Includes IP address
- Tracks who did what when

---

## 📊 Database Schema

### Customers Table
```sql
id, company_name, product_key, machine_limit, valid_days,
allowed_services, created_at, updated_at, created_by, revoked, notes
```

### Machines Table
```sql
id, customer_id, machine_id, fingerprint, hostname, os_info,
app_version, activated_at, last_seen, status, certificate, ip_address
```

### Audit Log Table
```sql
id, customer_id, machine_id, action, details, ip_address,
user_agent, performed_by, timestamp
```

---

## 🎯 What's Working

✅ **Product Key System**
- Auto-generation with check digits
- Format validation
- Unique per customer

✅ **Activation Flow**
- Validates product key
- Checks machine limit
- Generates signed certificate
- Saves machine record
- Returns certificate to client

✅ **Machine Limit Enforcement**
- Tracks active machines per customer
- Rejects when limit reached
- Returns list of active machines

✅ **Certificate System**
- RSA-2048 signing
- Includes all necessary data
- Signature verification ready

✅ **Admin Management**
- Create customers
- View all customers
- View customer details with machines
- Revoke machines
- Audit log

✅ **Database**
- Proper schema with indexes
- Foreign keys
- Sample data for testing

---

## 🚧 What's Next (Phase 2)

Phase 2 will add:
- Admin web portal (Next.js)
- Customer self-service portal
- Certificate renewal UI
- Usage analytics
- Better error messages
- Offline grace period
- Heartbeat monitoring dashboard

---

## 🐛 Troubleshooting

### Server won't start
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Or use a different port
uvicorn server:app --port 8001
```

### Database errors
```bash
# Delete and recreate database
rm licenses.db
python -c "from db import init_db; init_db()"
```

### Import errors
```bash
# Make sure you're in the phase1 directory
cd phase1

# Reinstall dependencies
pip install -r requirements.txt
```

---

## 📖 API Documentation

Once server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## ✅ Phase 1 Complete!

**What you can do now:**
1. ✅ Create customers via API
2. ✅ Generate product keys automatically
3. ✅ Activate machines with product keys
4. ✅ Enforce machine limits
5. ✅ Generate signed certificates
6. ✅ Validate certificates
7. ✅ Track all activations
8. ✅ Revoke specific machines
9. ✅ View audit logs

**Next:**
- Test the server thoroughly
- Build client-side validation (Day 2)
- Create admin portal (Phase 2)

---

**Phase 1 Status:** ✅ COMPLETE  
**Ready for:** Integration and Testing  
**Time Taken:** Day 1  
**Lines of Code:** ~1,500

---

Let's test it! 🚀