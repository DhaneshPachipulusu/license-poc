# Production Deployment Guide

This guide explains how to deploy the License POC on another laptop or production environment.

## Prerequisites

- **Python 3.11+** (tested on 3.13)
- **Node.js 18+**
- **Git** (for cloning the repository)

---

## Quick Start - New Laptop Deployment

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd license-poc
```

### 2. Backend Setup

```bash
cd server

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your production values (see Configuration section below)

# Seed admin user
python seed_admin_quick.py
```

### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your backend API URL

# Build for production
npm run build
```

### 4. Run the Application

**Backend** (in `server/` directory with venv activated):
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

**Frontend** (in `frontend/` directory):
```bash
# Development mode
npm run dev

# Production mode
npm run build
npm start
```

---

## Configuration

### Backend Configuration (`server/.env`)

```env
# Admin credentials (one-time seed only)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# CORS origins (comma-separated)
# Development:
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
# Production:
CORS_ORIGINS=https://your-frontend-domain.com

# Cookie settings
# Development (HTTP):
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_DOMAIN=
# Production (HTTPS):
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_DOMAIN=.yourdomain.com
```

### Frontend Configuration (`frontend/.env.local`)

```env
# Backend API URL
# Development:
NEXT_PUBLIC_API_URL=http://localhost:8000
# Production:
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

---

## Production Deployment Scenarios

### Scenario 1: Same Machine (Different IP/Domain)

If deploying on a laptop with a different IP address:

1. Update `server/.env`:
   ```env
   CORS_ORIGINS=http://<new-ip>:3000
   SESSION_COOKIE_SECURE=false
   SESSION_COOKIE_DOMAIN=
   ```

2. Update `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://<new-ip>:8000
   ```

3. Run both servers and access via `http://<new-ip>:3000`

### Scenario 2: HTTPS Production (Recommended)

With proper SSL certificates (Let's Encrypt, AWS ACM, etc.):

1. Update `server/.env`:
   ```env
   CORS_ORIGINS=https://yourdomain.com
   SESSION_COOKIE_SECURE=true
   SESSION_COOKIE_DOMAIN=.yourdomain.com
   ```

2. Update `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=https://api.yourdomain.com
   ```

3. Set up reverse proxy (Nginx, Caddy, Traefik) to handle SSL termination
4. Point frontend and backend to respective domains

### Scenario 3: Docker Deployment

```bash
# Build and run with docker-compose
cd set/
docker-compose up -d
```

Update `docker-compose.yml` environment variables as needed.

---

## Security Checklist for Production

- [ ] Change default admin credentials immediately after first login
- [ ] Set `SESSION_COOKIE_SECURE=true` (HTTPS only)
- [ ] Use strong passwords (minimum 12 characters)
- [ ] Restrict CORS origins to only trusted domains
- [ ] Enable firewall rules to limit backend port access
- [ ] Use environment variables (never commit `.env` files)
- [ ] Set proper `SESSION_COOKIE_DOMAIN` for your domain
- [ ] Consider using a reverse proxy (Nginx, Caddy) for SSL termination
- [ ] Back up SQLite database regularly (`server/licenses.db`)

---

## Troubleshooting

### Issue: 401 Unauthorized on Login

**Cause**: CORS or cookie configuration mismatch

**Fix**:
1. Check browser console for CORS errors
2. Verify `CORS_ORIGINS` matches your frontend URL exactly
3. Ensure `SESSION_COOKIE_SECURE=false` for HTTP, `true` for HTTPS
4. Clear browser cookies and try again

### Issue: Cannot connect to backend

**Cause**: Backend not running or wrong API URL

**Fix**:
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
3. Ensure firewall allows port 8000

### Issue: Admin login fails

**Cause**: Admin user not seeded or wrong credentials

**Fix**:
1. Run `python server/seed_admin_quick.py` to reset admin user
2. Default credentials: `admin` / `Nainovate@ai`
3. Check `server/licenses.db` exists

---

## Database Management

### Seed Admin User

```bash
cd server
python seed_admin_quick.py
```

This will:
- Delete existing admins
- Create new admin with credentials from `.env` (or default `admin/Nainovate@ai`)
- Hash password with bcrypt

### Backup Database

```bash
# Backup
cp server/licenses.db server/licenses.db.backup

# Restore
cp server/licenses.db.backup server/licenses.db
```

---

## Development vs Production

| Feature | Development | Production |
|---------|-------------|------------|
| Frontend | `npm run dev` (port 3000) | `npm run build && npm start` |
| Backend | `uvicorn server:app --reload` | `uvicorn server:app --host 0.0.0.0` |
| HTTPS | Not required | **Required** for `SESSION_COOKIE_SECURE=true` |
| CORS Origins | `localhost:3000` | Your production domain |
| Cookie Secure | `false` | `true` |

---

## Port Reference

- **Frontend**: 3000 (default Next.js)
- **Backend**: 8000 (FastAPI/Uvicorn)

Ensure these ports are available or update configurations accordingly.
