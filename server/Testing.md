# PHASE 1 - TESTING GUIDE

## 🧪 Complete Testing Checklist

### ✅ **TEST 1: Server Startup**

```bash
# Start server
python server.py

# Expected output:
# 🚀 Starting License Server...
# ✓ Database initialized
# ✓ RSA keys ready
# ✓ Server ready!
# INFO: Uvicorn running on http://0.0.0.0:8000
```

**Success criteria:**
- [ ] Server starts without errors
- [ ] RSA keys generated (private_key.pem, public_key.pem)
- [ ] Database created (licenses.db)
- [ ] Can access http://localhost:8000/health

---

### ✅ **TEST 2: Create Customer**

```bash
curl -X POST http://localhost:8000/api/v1/admin/customers \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Company Alpha",
    "machine_limit": 3,
    "valid_days": 365,
    "allowed_services": ["dashboard", "analytics"]
  }'
```

**Expected Response:**
```json
{
  "id": "uuid...",
  "company_name": "Test Company Alpha",
  "product_key": "TEST-2024-XXXXXXXX-XXX",
  "machine_limit": 3,
  "valid_days": 365,
  ...
}
```

**Success criteria:**
- [ ] Status 200
- [ ] Product key generated in correct format
- [ ] Check digits valid
- [ ] Customer saved in database

**Save the product_key for next tests!**

---

### ✅ **TEST 3: First Machine Activation (Should Succeed)**

```bash
curl -X POST http://localhost:8000/api/v1/activate \
  -H "Content-Type: application/json" \
  -d '{
    "product_key": "YOUR-PRODUCT-KEY-HERE",
    "machine_fingerprint": "test-machine-001-fingerprint",
    "hostname": "OFFICE-PC-001",
    "os_info": "Windows 11 Pro",
    "app_version": "1.0.0"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "certificate": {
    "version": "1.0",
    "customer_id": "...",
    "machine_id": "...",
    "machine_fingerprint": "test-machine-001-fingerprint",
    "hostname": "OFFICE-PC-001",
    "issued_at": "...",
    "valid_until": "...",
    "signature": "..."
  },
  "message": "Activation successful (1/3 machines)"
}
```

**Success criteria:**
- [ ] Status 200
- [ ] success = true
- [ ] Certificate contains all fields
- [ ] Signature is hex string
- [ ] Message shows "1/3 machines"

---

### ✅ **TEST 4: Same Machine Activation (Should Return Existing)**

```bash
# Use SAME fingerprint as Test 3
curl -X POST http://localhost:8000/api/v1/activate \
  -H "Content-Type: application/json" \
  -d '{
    "product_key": "YOUR-PRODUCT-KEY-HERE",
    "machine_fingerprint": "test-machine-001-fingerprint",
    "hostname": "OFFICE-PC-001"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "certificate": {...same as before...},
  "message": "Machine already activated. Returning existing certificate."
}
```

**Success criteria:**
- [ ] Status 200
- [ ] Returns SAME certificate (same machine_id)
- [ ] Message indicates "already activated"
- [ ] Machine count still 1/3

---

### ✅ **TEST 5: Second Machine Activation (Should Succeed)**

```bash
curl -X POST http://localhost:8000/api/v1/activate \
  -H "Content-Type: application/json" \
  -d '{
    "product_key": "YOUR-PRODUCT-KEY-HERE",
    "machine_fingerprint": "test-machine-002-fingerprint",
    "hostname": "LAPTOP-001"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Activation successful (2/3 machines)"
}
```

**Success criteria:**
- [ ] Status 200
- [ ] New certificate (different machine_id)
- [ ] Message shows "2/3 machines"

---

### ✅ **TEST 6: Third Machine Activation (Should Succeed)**

```bash
curl -X POST http://localhost:8000/api/v1/activate \
  -H "Content-Type: application/json" \
  -d '{
    "product_key": "YOUR-PRODUCT-KEY-HERE",
    "machine_fingerprint": "test-machine-003-fingerprint",
    "hostname": "HOME-PC-001"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Activation successful (3/3 machines)"
}
```

**Success criteria:**
- [ ] Status 200
- [ ] Message shows "3/3 machines" (limit reached)

---

### ✅ **TEST 7: Fourth Machine Activation (Should FAIL - Limit Exceeded)**

```bash
curl -X POST http://localhost:8000/api/v1/activate \
  -H "Content-Type: application/json" \
  -d '{
    "product_key": "YOUR-PRODUCT-KEY-HERE",
    "machine_fingerprint": "test-machine-004-fingerprint",
    "hostname": "EXTRA-PC"
  }'
```

**Expected Response:**
```json
{
  "success": false,
  "message": "Machine limit reached (3/3)",
  "error": "limit_exceeded",
  "active_machines": [
    {
      "hostname": "OFFICE-PC-001",
      "last_seen": "...",
      "activated_at": "..."
    },
    {
      "hostname": "LAPTOP-001",
      ...
    },
    {
      "hostname": "HOME-PC-001",
      ...
    }
  ]
}
```

**Success criteria:**
- [ ] Status 200 (not an error, just rejection)
- [ ] success = false
- [ ] error = "limit_exceeded"
- [ ] Lists all 3 active machines
- [ ] Machine NOT saved in database

---

### ✅ **TEST 8: Invalid Product Key (Should FAIL)**

```bash
curl -X POST http://localhost:8000/api/v1/activate \
  -H "Content-Type: application/json" \
  -d '{
    "product_key": "INVALID-KEY-123",
    "machine_fingerprint": "test-machine-xxx"
  }'
```

**Expected Response:**
```json
{
  "success": false,
  "message": "Invalid product key format",
  "error": "invalid_key_format"
}
```

**Success criteria:**
- [ ] Rejects invalid format keys

---

### ✅ **TEST 9: Non-existent Product Key (Should FAIL)**

```bash
curl -X POST http://localhost:8000/api/v1/activate \
  -H "Content-Type: application/json" \
  -d '{
    "product_key": "FAKE-2024-NOTREAL-XYZ",
    "machine_fingerprint": "test-machine-xxx"
  }'
```

**Expected Response:**
```json
{
  "success": false,
  "message": "Product key not found",
  "error": "invalid_key"
}
```

**Success criteria:**
- [ ] Rejects keys not in database

---

### ✅ **TEST 10: List All Customers**

```bash
curl http://localhost:8000/api/v1/admin/customers
```

**Expected Response:**
```json
[
  {
    "id": "...",
    "company_name": "Test Company Alpha",
    "product_key": "...",
    "machine_limit": 3,
    "active_machines": 3,
    "last_activity": "...",
    "created_at": "...",
    "revoked": false
  },
  ...
]
```

**Success criteria:**
- [ ] Returns array of customers
- [ ] Shows active_machines count
- [ ] Shows last_activity

---

### ✅ **TEST 11: Get Customer Details**

```bash
# Replace {customer_id} with actual ID from TEST 10
curl http://localhost:8000/api/v1/admin/customers/{customer_id}
```

**Expected Response:**
```json
{
  "customer": {
    "id": "...",
    "company_name": "Test Company Alpha",
    "product_key": "...",
    "machine_limit": 3,
    ...
  },
  "machines": [
    {
      "id": "...",
      "hostname": "OFFICE-PC-001",
      "fingerprint": "test-machine-001...",
      "os_info": "Windows 11 Pro",
      "activated_at": "...",
      "last_seen": "...",
      "status": "active"
    },
    ... (2 more machines)
  ]
}
```

**Success criteria:**
- [ ] Shows customer details
- [ ] Lists all 3 machines
- [ ] Shows machine status

---

### ✅ **TEST 12: Revoke a Machine**

```bash
# Get a machine_id from TEST 11
curl -X POST http://localhost:8000/api/v1/admin/machines/{machine_id}/revoke
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Machine revoked"
}
```

**Now try to activate the 4th machine - should succeed now (2/3 active):**

```bash
curl -X POST http://localhost:8000/api/v1/activate \
  -H "Content-Type: application/json" \
  -d '{
    "product_key": "YOUR-PRODUCT-KEY-HERE",
    "machine_fingerprint": "test-machine-004-fingerprint",
    "hostname": "EXTRA-PC"
  }'
```

**Success criteria:**
- [ ] Machine revoked successfully
- [ ] Fourth machine can now activate (since one was revoked)
- [ ] Active count is 3 again

---

### ✅ **TEST 13: Certificate Validation**

```bash
# Use certificate from TEST 3
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{
    "certificate": {
      "machine_id": "...",
      "machine_fingerprint": "...",
      "signature": "...",
      ... (entire certificate)
    }
  }'
```

**Expected Response:**
```json
{
  "valid": true,
  "reason": "valid"
}
```

**Success criteria:**
- [ ] Valid certificate returns valid=true
- [ ] Signature verification works

---

### ✅ **TEST 14: Get Public Key**

```bash
curl http://localhost:8000/api/v1/public-key
```

**Expected Response:**
```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----
```

**Success criteria:**
- [ ] Returns PEM formatted public key
- [ ] Can be used for signature verification

---

### ✅ **TEST 15: Heartbeat**

```bash
# Use machine_id from an active machine
curl -X POST http://localhost:8000/api/v1/heartbeat \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "YOUR-MACHINE-ID",
    "app_version": "1.0.0",
    "status": "running"
  }'
```

**Expected Response:**
```json
{
  "status": "ok",
  "cert_update": null,
  "message": null
}
```

**Success criteria:**
- [ ] Returns status=ok
- [ ] Updates last_seen in database

---

### ✅ **TEST 16: Audit Log**

```bash
curl http://localhost:8000/api/v1/admin/audit-log?limit=20
```

**Expected Response:**
```json
[
  {
    "id": "...",
    "customer_id": "...",
    "machine_id": "...",
    "action": "activation_success",
    "details": {...},
    "ip_address": "127.0.0.1",
    "timestamp": "..."
  },
  ... (more log entries)
]
```

**Success criteria:**
- [ ] Shows all actions performed
- [ ] Includes activation_success, activation_failed, machine_revoked, etc.
- [ ] Timestamps are correct

---

## 📊 **COMPLETE TEST RESULTS**

| Test | Description | Status |
|------|-------------|--------|
| 1 | Server startup | ☐ |
| 2 | Create customer | ☐ |
| 3 | First activation | ☐ |
| 4 | Same machine (existing) | ☐ |
| 5 | Second activation | ☐ |
| 6 | Third activation (limit reached) | ☐ |
| 7 | Fourth activation (should fail) | ☐ |
| 8 | Invalid key format | ☐ |
| 9 | Non-existent key | ☐ |
| 10 | List customers | ☐ |
| 11 | Customer details | ☐ |
| 12 | Revoke machine | ☐ |
| 13 | Certificate validation | ☐ |
| 14 | Get public key | ☐ |
| 15 | Heartbeat | ☐ |
| 16 | Audit log | ☐ |

---

## 🐛 **Common Issues**

### Port already in use
```bash
# Kill process using port 8000
lsof -i :8000
kill -9 <PID>

# Or use different port
uvicorn server:app --port 8001
```

### Database locked
```bash
# Close all connections and restart server
rm licenses.db
python -c "from db import init_db; init_db()"
```

### Import errors
```bash
# Ensure you're in phase1 directory
cd phase1
python -c "import sys; print(sys.path)"
```

---

## ✅ **Phase 1 Testing Complete!**

If all tests pass, Phase 1 is fully functional and ready for:
- Integration with client application
- Phase 2 development (Admin Portal)
- Production deployment testing

---

**Next Steps:**
1. Complete all tests above
2. Document any failures
3. Fix issues
4. Move to Day 2 (Client-side validation)