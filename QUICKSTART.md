# ⚡ QUICK START GUIDE

## 🎯 What You Got

A **complete license control system** for your Docker Node.js application with:

✅ Machine fingerprinting (works on Docker/EC2/Physical)
✅ Automatic license registration
✅ 3-machine activation limit
✅ Offline grace period (7 days)
✅ Heartbeat monitoring
✅ Beautiful admin dashboard

---

## 📦 Files Delivered

```
your-project/
├── license-agent/          ⭐ COPY THIS TO YOUR PROJECT
│   ├── agent.js           (Main license logic)
│   ├── fingerprint.js     (Machine ID generator)
│   ├── middleware.js      (Express middleware)
│   ├── start.js           (Startup wrapper)
│   └── index.js           (Exports)
│
├── Dockerfile              ⭐ REPLACE YOUR DOCKERFILE
├── docker-compose.yml      ⭐ REPLACE YOUR COMPOSE FILE
│
├── app_updated.py          ⭐ UPDATE YOUR LICENSE SERVER
├── db_updated.py           ⭐ UPDATE YOUR DATABASE CODE
│
├── templates/              (Already have these)
│   ├── licenses.html
│   └── license_view.html
│
└── docs/
    ├── README.md           (Complete documentation)
    ├── TESTING.md          (Testing guide)
    └── VISUAL_GUIDE.md     (Architecture diagrams)
```

---

## 🚀 Setup in 5 Minutes

### Step 1: Update License Server (2 min)

```bash
cd your-license-server/

# Backup current files
cp app.py app.py.backup
cp db.py db.py.backup

# Replace with new versions
cp app_updated.py app.py
cp db_updated.py db.py

# Restart server
python app.py
# or
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

✅ Server now tracks activations and enforces 3-machine limit

### Step 2: Update Client App (3 min)

```bash
cd your-frontend-app/

# 1. Copy license agent
cp -r license-agent/ .

# 2. Replace Dockerfile
cp Dockerfile.new Dockerfile

# 3. Update docker-compose.yml
# Change this line:
LICENSE_SERVER_URL=http://YOUR_SERVER_IP:8000

# 4. Build and run
docker-compose build
docker-compose up -d

# 5. Watch the magic!
docker-compose logs -f
```

---

## 📋 What Happens Now

### First Run:
```
🔐 LICENSE AGENT STARTING
🖥️  Machine ID: MACHINE-abc123
📄 No license found. Attempting to register...
✅ License registered successfully!
💓 Starting heartbeat
✅ LICENSE VALIDATED
🎯 Starting Next.js application...
```

### Subsequent Runs:
```
🔐 LICENSE AGENT STARTING
🖥️  Machine ID: MACHINE-abc123
📄 License file found. Validating...
✅ License validated successfully!
🎯 Starting Next.js application...
```

### 4th Machine (Over Limit):
```
🔐 LICENSE AGENT STARTING
❌ License registration failed: activation_limit_exceeded
❌ Application cannot start without a valid license.
```

---

## 🎛️ Key Configuration

### In `docker-compose.yml`:

```yaml
environment:
  # Point to your license server
  - LICENSE_SERVER_URL=http://192.168.1.204:8000
  
  # Customer identifier
  - CUSTOMER_NAME=acme-corp
```

### In `app.py` (server):

```python
# Change activation limit
MAX_ACTIVATIONS_PER_LICENSE = 3  # or 5, 10, etc.

# Change trial period
"valid_till": (issued + timedelta(days=30)).isoformat()  # 30 days
```

---

## 📊 Admin Dashboard

**View all licenses:**
```
http://your-server:8000/admin/licenses
```

**View activations for a customer:**
```bash
curl http://your-server:8000/admin/activations/acme-corp
```

**Renew a license:**
- Go to license detail page
- Enter days to extend
- Click "Renew"

**Revoke a license:**
- Click "Revoke" button
- Confirm

---

## 🔍 How Machine ID Works

### Docker Container:
```
Reads: /etc/machine-id (host machine ID)
Plus: MAC address, CPU model
Result: MACHINE-a1b2c3d4e5f6

✅ Same ID across container restarts
✅ Different ID if moved to different host
```

### AWS EC2:
```
Reads: Instance metadata (169.254.169.254)
Result: AWS-i-0123456789abcdef

✅ Unique per EC2 instance
```

### Physical Machine:
```
Reads: Hardware identifiers
Result: MACHINE-x9y8z7w6v5u4

✅ Stable machine ID
```

---

## 🐛 Troubleshooting

### License Not Activating?

```bash
# Check if server is reachable
docker exec -it <container> curl http://192.168.1.204:8000/public_key

# Check logs
docker-compose logs -f | grep LICENSE

# Check license file
docker exec -it <container> cat /var/license/license.json
```

### Container Exits Immediately?

```bash
# View logs to see error
docker-compose logs ai-dashboard-frontend-license

# Common issues:
# - LICENSE_SERVER_URL wrong
# - Server not running
# - Activation limit reached
```

### Need to Reset License?

```bash
# Delete license and restart
docker exec -it <container> rm /var/license/license.json
docker-compose restart
```

---

## 📝 Testing Checklist

- [ ] Single machine: Works ✅
- [ ] Restart container: License persists ✅
- [ ] 3 machines: All work ✅
- [ ] 4th machine: Blocked ✅
- [ ] Server offline: Offline mode works ✅
- [ ] License expired: App blocks ✅
- [ ] License revoked: App blocks ✅
- [ ] Admin dashboard: Can view/renew/revoke ✅

---

## 🎓 Key Concepts

### Machine Fingerprint
- Unique ID per physical/virtual machine
- Based on hardware + system IDs
- Persistent across container restarts
- Changes if moved to different host

### Activation Limit
- Max 3 machines per customer (configurable)
- Tracked in database
- Enforced at registration time
- Can deactivate machines via API

### Offline Grace Period
- 7 days by default (configurable)
- Allows app to run when server unreachable
- Based on local license expiry check
- Blocks after grace period ends

### Heartbeat
- Sent every 5 minutes
- Updates last_seen in database
- For monitoring and analytics
- Non-blocking (continues if fails)

---

## 🔐 Security Notes

1. **Private key**: Never share or commit to git
2. **HTTPS**: Use in production for license server
3. **Rate limiting**: Add to prevent abuse
4. **Monitoring**: Watch for suspicious activations
5. **Backup**: Database regularly

---

## 📞 Common Questions

**Q: What if container restarts?**
A: License file persists in `/var/license` volume. Works automatically.

**Q: Can I move license to another machine?**
A: No, license is bound to machine ID. Need to deactivate first.

**Q: What happens if I hit 3-machine limit?**
A: 4th machine will fail to start. Deactivate one machine or upgrade.

**Q: How do I deactivate a machine?**
A: Use API: `POST /admin/deactivate` with customer and machine_id

**Q: Does it work on EC2?**
A: Yes! Detects EC2 instance ID automatically.

**Q: What if server is down?**
A: App continues in offline mode for 7 days (grace period).

---

## 🎯 Next Steps

1. ✅ Test locally with single machine
2. ✅ Test with 3 machines
3. ✅ Test offline mode
4. ✅ Deploy license server to production
5. ✅ Update docker-compose with production URL
6. ✅ Distribute to customers

---

## 📚 Full Documentation

- **README.md** - Complete system documentation
- **TESTING.md** - Detailed testing scenarios
- **VISUAL_GUIDE.md** - Architecture diagrams

---

## 💪 You're Ready!

Your license system is **production-ready** with:

✅ Automatic registration
✅ Machine binding
✅ Activation limits
✅ Offline support
✅ Beautiful admin UI
✅ Monitoring & heartbeat

Just update the server URL and you're good to go! 🚀

---

**Questions?** Check the full README.md or TESTING.md

**Need help?** All code includes comments and examples

**Want to customize?** Everything is documented and configurable
