# 🔐 License-Controlled Docker Application

Complete license control system for your Node.js application with machine fingerprinting and activation limits.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Setup Instructions](#setup-instructions)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This system provides enterprise-grade license control for your containerized application with:

✅ **Machine fingerprinting** - Unique ID generation for Docker/EC2/Physical machines
✅ **Automatic registration** - First-run license acquisition from server
✅ **Offline grace period** - Continue working when server is unreachable
✅ **Heartbeat monitoring** - Regular check-ins to license server
✅ **Feature toggles** - Enable/disable features per license
✅ **Activation limits** - Control how many machines can use one license
✅ **Persistent storage** - License survives container restarts

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│  CLIENT DOCKER CONTAINER                        │
│                                                  │
│  ┌────────────────────────────────┐             │
│  │  License Agent (Node.js)       │             │
│  │  1. Generate Machine ID        │             │
│  │  2. Register with Server       │             │
│  │  3. Validate License           │             │
│  │  4. Send Heartbeats            │             │
│  └──────────────┬─────────────────┘             │
│                 │                                │
│                 ↓                                │
│  ┌────────────────────────────────┐             │
│  │  Your Next.js Application      │             │
│  │  (Only starts if license valid)│             │
│  └────────────────────────────────┘             │
│                                                  │
│  Volume: /var/license/                          │
│    ├── license.json                             │
│    └── public_key.pem                           │
└─────────────────────────────────────────────────┘
                    ↕ HTTPS
┌─────────────────────────────────────────────────┐
│  LICENSE SERVER (FastAPI)                       │
│  - Issue licenses                               │
│  - Track activations                            │
│  - Validate requests                            │
│  - Enforce machine limits                       │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Setup Instructions

### Step 1: License Server Setup

First, set up your license server (the FastAPI app you already have):

```bash
# Start license server
cd license-server
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

The server should be accessible at `http://your-server-ip:8000`

### Step 2: Prepare Your Application

Copy the `license-agent` folder to your application root:

```
your-app/
├── license-agent/
│   ├── agent.js
│   ├── fingerprint.js
│   ├── middleware.js
│   ├── start.js
│   └── index.js
├── Dockerfile
├── docker-compose.yml
├── package.json
└── ... (your app files)
```

### Step 3: Update docker-compose.yml

Edit the `LICENSE_SERVER_URL` to point to your license server:

```yaml
environment:
  - LICENSE_SERVER_URL=http://YOUR_LICENSE_SERVER_IP:8000
  - CUSTOMER_NAME=your-customer-name
```

### Step 4: Build and Run

```bash
# Build the Docker image
docker-compose build

# Start the container
docker-compose up -d

# Watch the logs to see license validation
docker-compose logs -f
```

---

## 📖 How It Works

### First Run (No License)

```
Container Starts
      ↓
License Agent Runs
      ↓
No license.json found
      ↓
Generate Machine ID: MACHINE-abc123...
      ↓
Contact Server: POST /register
      {
        "machine_id": "MACHINE-abc123...",
        "customer": "your-customer"
      }
      ↓
Server Response:
      {
        "license_id": "LIC-xyz789",
        "license": { ... }
      }
      ↓
Save license.json to /var/license/
      ↓
Download public_key.pem
      ↓
✅ License Valid - Start Application
      ↓
💓 Start Heartbeat (every 5 min)
```

### Subsequent Runs (License Exists)

```
Container Starts
      ↓
License Agent Runs
      ↓
Found license.json
      ↓
Load License & Check:
  ✓ Machine ID matches?
  ✓ Not expired (local check)?
      ↓
Contact Server: POST /validate
      {
        "license": { ... }
      }
      ↓
Server Validates:
  ✓ Signature valid?
  ✓ Not revoked?
  ✓ Within activation limit?
      ↓
✅ License Valid - Start Application
```

### Offline Mode

If the license server is unreachable:

```
Server Connection Failed
      ↓
Check Local Expiry Date
      ↓
Within Grace Period? (7 days default)
      ↓
✅ YES: Allow app to run (offline mode)
❌ NO:  Block app startup
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LICENSE_SERVER_URL` | URL of your license server | `http://localhost:8000` | ✅ Yes |
| `CUSTOMER_NAME` | Customer identifier | `default-customer` | No |
| `NODE_ENV` | Environment | `production` | No |

### License Agent Options

Edit `license-agent/start.js` to customize:

```javascript
const agent = new LicenseAgent({
  serverUrl: process.env.LICENSE_SERVER_URL,
  customerName: process.env.CUSTOMER_NAME,
  heartbeatInterval: 300000,  // 5 minutes (in ms)
  offlineGracePeriod: 7,      // 7 days
});
```

---

## 🔍 Machine ID Generation

The system generates a unique fingerprint based on:

1. **Host Machine ID** (`/etc/machine-id`) - Most reliable
2. **MAC Address** - Hardware identifier
3. **CPU Model** - Hardware fingerprint
4. **AWS EC2 Instance ID** - If running on AWS
5. **Hostname** - Fallback identifier

This ensures the **same machine ID** is generated even when:
- Container is restarted
- Container is rebuilt
- Container is moved to another host (will get NEW ID - as expected!)

---

## 📊 Server-Side: Track Activations

Update your `app.py` to enforce activation limits:

```python
from db import get_activations_count, save_activation

@app.post('/register')
def register(req: RegisterRequest):
    machine_id = req.machine_id
    customer = req.customer
    
    # Check activation limit (e.g., max 3 machines per customer)
    current_activations = get_activations_count(customer)
    
    if current_activations >= 3:
        raise HTTPException(403, 
            "Activation limit reached. This license is already active on 3 machines. "
            "Please deactivate a machine or contact support to upgrade."
        )
    
    # Check if THIS machine already has a license
    existing = get_license_by_machine(machine_id)
    if existing:
        return {"license_id": existing["license_id"], "license": existing}
    
    # Create new license
    license_id = "LIC-" + uuid.uuid4().hex[:12]
    # ... create license ...
    
    # Track this activation
    save_activation(license_id, machine_id, customer)
    
    return {"license_id": license_id, "license": lic}
```

### Database Schema for Activations

```python
# db.py - Add this table
def init_db():
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    
    # Existing licenses table
    c.execute('''CREATE TABLE IF NOT EXISTS licenses ...''')
    
    # NEW: Activations tracking
    c.execute('''
        CREATE TABLE IF NOT EXISTS activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_id TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            customer TEXT NOT NULL,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            UNIQUE(license_id, machine_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_activations_count(customer):
    """Count active machines for a customer"""
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(DISTINCT machine_id) FROM activations WHERE customer = ?', (customer,))
    count = c.fetchone()[0]
    conn.close()
    return count

def save_activation(license_id, machine_id, customer):
    """Record machine activation"""
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO activations (license_id, machine_id, customer, last_seen)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (license_id, machine_id, customer))
    conn.commit()
    conn.close()
```

---

## 🐛 Troubleshooting

### Issue: "License validation failed - machine_mismatch"

**Cause**: Machine ID has changed (moved to different host)

**Solution**: 
- Contact vendor to deactivate old machine
- OR: Delete `/var/license/license.json` and re-register

### Issue: "Cannot reach license server"

**Cause**: Network connectivity issue

**Solution**:
- Check `LICENSE_SERVER_URL` is correct
- Verify server is running: `curl http://your-server:8000/public_key`
- Check firewall rules
- App will work in offline mode if license is still valid

### Issue: "Activation limit reached"

**Cause**: License already active on maximum allowed machines

**Solution**:
- Deactivate unused machines via admin portal
- OR: Upgrade license to allow more activations

### Issue: Container restarts and loses license

**Cause**: Volume not mounted correctly

**Solution**:
```bash
# Check volume exists
docker volume ls | grep license

# Inspect volume
docker volume inspect license-data

# Verify mount in container
docker exec -it <container> ls -la /var/license/
```

---

## 📝 Logs & Monitoring

### View License Validation Logs

```bash
# Real-time logs
docker-compose logs -f ai-dashboard-frontend-license

# Filter for license events
docker-compose logs | grep "LICENSE"
docker-compose logs | grep "🔐"
```

### Check License Status

Inspect the license file:

```bash
# From host
docker exec -it <container> cat /var/license/license.json

# Or access the volume
docker volume inspect license-data
```

---

## 🎯 Feature Flags

Enable/disable features per license:

```javascript
// In your app code
const { LicenseAgent } = require('./license-agent');
const agent = new LicenseAgent();

// Check if feature is enabled
if (agent.isFeatureEnabled('moduleA')) {
  // Enable advanced features
}
```

Server-side (in license):

```json
{
  "features": {
    "moduleA": true,
    "moduleB": false,
    "premiumFeatures": true
  }
}
```

---

## 🔒 Security Best Practices

1. **Use HTTPS** for license server in production
2. **Secure private key** - never expose it
3. **Rotate keys** regularly
4. **Monitor activations** for suspicious activity
5. **Set grace periods** appropriately
6. **Implement rate limiting** on server

---

## 📞 Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Verify server connectivity
- Contact your vendor support team

---

## 📄 License

This license control system is proprietary software.
Unauthorized distribution or modification is prohibited.
