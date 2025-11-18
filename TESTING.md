# 🧪 Testing & Deployment Guide

## 🎯 Quick Start Test Flow

### 1. Start License Server

```bash
# Install dependencies
pip install fastapi uvicorn python-dateutil cryptography

# Start server
python app.py
# or
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Server should be at: `http://localhost:8000`

Test it:
```bash
curl http://localhost:8000/public_key
```

### 2. Build and Run Client

```bash
# Update LICENSE_SERVER_URL in docker-compose.yml
# Change to your actual server IP
LICENSE_SERVER_URL=http://192.168.1.204:8000

# Build
docker-compose build

# Run
docker-compose up
```

### 3. Watch the Magic! ✨

```bash
# Watch logs in real-time
docker-compose logs -f ai-dashboard-frontend-license
```

You should see:

```
🔐 ===== LICENSE AGENT STARTING =====
🖥️  Machine ID: MACHINE-abc123def456
📊 System: linux/x64, 4 CPUs, 8GB

📄 No license found. Attempting to register...
✅ License registered successfully!
   License ID: LIC-xyz789abc123
   Valid until: 2025-12-18T10:30:00Z

💓 Starting heartbeat (every 300s)

✅ ========================================
   LICENSE VALIDATED SUCCESSFULLY
========================================
   License ID: LIC-xyz789abc123
   Customer: default-customer
   Valid Until: 2025-12-18T10:30:00Z

   Enabled Features:
   ✓ moduleA

========================================

🎯 Starting Next.js application...
```

---

## 🧪 Test Scenarios

### Scenario 1: First Run (New Machine)

```bash
docker-compose up
```

**Expected**: 
- ✅ License auto-registers
- ✅ App starts successfully
- ✅ Creates `/var/license/license.json`

### Scenario 2: Restart Container (Same Machine)

```bash
docker-compose restart
```

**Expected**:
- ✅ Finds existing license
- ✅ Validates with server
- ✅ App starts without re-registering

### Scenario 3: Maximum Activations (3 Machines)

```bash
# Run on 3 different machines
machine1$ docker-compose up
machine2$ docker-compose up
machine3$ docker-compose up

# Try 4th machine
machine4$ docker-compose up
```

**Expected on 4th machine**:
```
❌ License registration failed: activation_limit_exceeded
Application cannot start without a valid license.
```

### Scenario 4: Expired License

```bash
# In admin dashboard, set valid_till to yesterday
# OR wait for expiry

docker-compose restart
```

**Expected**:
```
❌ License expired
Application cannot start without a valid license.
```

### Scenario 5: Revoked License

```bash
# In admin dashboard
curl http://localhost:8000/admin/revoke/LIC-xyz789

# Restart container
docker-compose restart
```

**Expected**:
```
❌ Server validation failed: revoked
Application cannot start without a valid license.
```

### Scenario 6: Server Offline (Offline Mode)

```bash
# Stop license server
# Stop the FastAPI server

# Restart client
docker-compose restart
```

**Expected** (if license not expired):
```
⚠️  Cannot reach license server. Using offline validation...
✅ License valid (offline mode)
```

### Scenario 7: Move License to Different Machine

```bash
# Copy license file from machine1
docker cp container1:/var/license/license.json ./

# Put on machine2
docker cp ./license.json container2:/var/license/

# Restart container2
docker-compose restart
```

**Expected**:
```
❌ Machine ID mismatch!
   Expected: MACHINE-abc123
   Current:  MACHINE-xyz789
```

---

## 🔍 Debugging

### Check Machine ID

```bash
docker exec -it <container> node -e "
const fp = require('./license-agent/fingerprint');
console.log(fp.generate());
"
```

### View License File

```bash
docker exec -it <container> cat /var/license/license.json
```

### Test License Validation Manually

```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d @/var/license/license.json
```

### Check Activations

```bash
# View all activations for a customer
curl http://localhost:8000/admin/activations/default-customer
```

---

## 📊 Admin Dashboard Testing

### View All Licenses
```
http://localhost:8000/admin/licenses
```

### View Specific License
```
http://localhost:8000/admin/license/LIC-xyz789abc123
```

### Renew License
1. Go to license detail page
2. Enter days to extend (e.g., 30)
3. Click "Renew License"

### Revoke License
1. Go to license list
2. Click "Revoke" button
3. Confirm

### View Customer Activations
```bash
curl http://localhost:8000/admin/activations/default-customer
```

Response:
```json
{
  "customer": "default-customer",
  "total_activations": 2,
  "max_activations": 3,
  "activations": [
    {
      "license_id": "LIC-abc123",
      "machine_id": "MACHINE-xyz789",
      "activated_at": "2025-11-18T10:00:00",
      "last_seen": "2025-11-18T10:35:00",
      "ip_address": "192.168.1.100"
    }
  ]
}
```

---

## 🚀 Production Deployment

### 1. Secure License Server

```bash
# Use HTTPS with proper SSL certificate
# Use nginx as reverse proxy

server {
    listen 443 ssl;
    server_name license.yourcompany.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
    }
}
```

### 2. Environment Variables

```yaml
# Production docker-compose.yml
environment:
  - LICENSE_SERVER_URL=https://license.yourcompany.com
  - CUSTOMER_NAME=${CUSTOMER_NAME}
  - NODE_ENV=production
```

### 3. Secure Private Key

```bash
# Store private key in secure vault
# Use environment variable or mounted secret

# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id license-private-key

# Kubernetes Secret
kubectl create secret generic license-keys \
  --from-file=private_key.pem
```

### 4. Rate Limiting

```python
# Add to app.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post('/register')
@limiter.limit("5/minute")
def register(...):
    ...
```

### 5. Monitoring

```python
# Add logging
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post('/register')
def register(...):
    logger.info(f"Registration attempt from {request.client.host} for {customer}")
    ...
```

---

## 🎛️ Configuration Options

### Change Activation Limit

```python
# app.py
MAX_ACTIVATIONS_PER_LICENSE = 5  # Change from 3 to 5
```

### Change Trial Period

```python
# app.py - register function
"valid_till": (issued + timedelta(days=90)).isoformat() + "Z",  # 90-day trial
```

### Change Grace Period

```javascript
// license-agent/start.js
const agent = new LicenseAgent({
  offlineGracePeriod: 14,  // 14 days offline grace
});
```

### Change Heartbeat Frequency

```javascript
// license-agent/start.js
const agent = new LicenseAgent({
  heartbeatInterval: 600000,  // 10 minutes (in milliseconds)
});
```

---

## 📝 Checklist Before Go-Live

- [ ] License server running on HTTPS
- [ ] Private key secured (not in git!)
- [ ] Database backed up regularly
- [ ] Admin dashboard password-protected
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Monitoring alerts set up
- [ ] Customer support process defined
- [ ] License terms & pricing decided
- [ ] Deactivation portal created (optional)

---

## 🆘 Common Issues

### Issue: "Module not found: license-agent"

**Fix**: Make sure `license-agent` folder is in your app root

```bash
ls -la /app/license-agent/
```

### Issue: "EACCES: permission denied /var/license"

**Fix**: Check volume permissions

```bash
# In Dockerfile
RUN chown -R appuser:appgroup /var/license
```

### Issue: "Cannot reach license server"

**Fix**: Check network connectivity

```bash
# From inside container
docker exec -it <container> curl http://192.168.1.204:8000/public_key
```

### Issue: "License file corrupted"

**Fix**: Delete and re-register

```bash
docker exec -it <container> rm /var/license/license.json
docker-compose restart
```

---

## 📞 Support Commands

```bash
# View all logs
docker-compose logs --tail=100

# Enter container
docker exec -it ai-dashboard-frontend-license sh

# Check license status
docker exec -it <container> cat /var/license/license.json | python -m json.tool

# Force re-registration
docker exec -it <container> rm -f /var/license/license.json
docker-compose restart

# Check volume
docker volume inspect license-data
```

---

## 🎓 Next Steps

1. ✅ Test locally with 1 machine
2. ✅ Test with 3 machines (activation limit)
3. ✅ Test offline mode
4. ✅ Test renewal via admin dashboard
5. ✅ Deploy license server to production
6. ✅ Update client docker-compose with prod URL
7. ✅ Distribute to customers
8. ✅ Monitor activations

---

Good luck with your license system! 🚀
