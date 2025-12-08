# AI Dashboard License Installer

## Overview

This installer activates the AI Dashboard license on a customer's machine.

## Components

```
installer/
├── installer.py              # Main GUI installer
├── container_validator.py    # Runs inside Docker container
├── Dockerfile.licensed       # Sample Dockerfile with license check
├── requirements.txt          # Python dependencies
├── build.bat                 # Windows build script
├── build.sh                  # Linux build script
└── README.md                 # This file
```

## Flow

### First Time Activation

1. Customer runs `AI-Dashboard-Setup.exe`
2. Enters product key (from Admin UI)
3. Installer:
   - Generates machine fingerprint
   - Sends to license server
   - Receives activation bundle (cert + docker creds + compose)
   - Saves encrypted files locally
   - Logs into Docker registry
   - Runs `docker-compose up`

### Subsequent Runs

1. Docker container starts
2. `container_validator.py` runs first
3. Validates:
   - Certificate exists
   - Fingerprint matches
   - Signature valid
   - Not expired
   - Service allowed
4. If valid → App starts
5. If invalid → Error page shown

## Building the Installer

### Windows

```batch
# Install Python 3.9+ first
cd installer
pip install -r requirements.txt
build.bat
```

Output: `dist/AI-Dashboard-Setup.exe`

### Linux

```bash
cd installer
pip install -r requirements.txt
chmod +x build.sh
./build.sh
```

Output: `dist/ai-dashboard-setup`

## Configuration

### Server URL

Update `LICENSE_SERVER` in `installer.py`:

```python
LICENSE_SERVER = "https://license.yourcompany.com"
```

### Docker PAT

Set on server as environment variable:

```bash
export DOCKER_PAT="dckr_pat_xxxxxxxxxxxxx"
```

## Files Created on Customer Machine

```
Windows: C:\ProgramData\AILicenseDashboard\
Linux:   /var/license/

├── license/
│   ├── certificate.json     # License certificate
│   ├── certificate.dat      # Encrypted certificate
│   ├── machine_id.json      # Machine fingerprint
│   ├── public_key.pem       # For offline verification
│   └── docker_credentials.dat  # Encrypted Docker PAT
└── docker-compose.yml       # Generated compose file
```

## Security

1. **Machine Fingerprint**: Generated from hardware (CPU, disk, machine GUID)
2. **Certificate**: Signed with RSA-4096, HMAC-SHA512
3. **Docker Credentials**: Encrypted with AES-256-GCM using machine fingerprint
4. **Cannot Copy**: Certificate bound to machine fingerprint

## Docker Integration

Update your Dockerfile:

```dockerfile
# Install Python for license validation
RUN apk add --no-cache python3 py3-pip && \
    pip3 install --break-system-packages cryptography

# Copy validator
COPY container_validator.py /app/license_validator.py

# Create license directory
RUN mkdir -p /var/license

# Startup: validate then start
CMD ["sh", "-c", "python3 /app/license_validator.py && npm run start"]
```

Volume mount in compose (auto-generated):

```yaml
volumes:
  - license-data:/var/license:ro
```

## Troubleshooting

### "Server connection failed"
- Check LICENSE_SERVER URL
- Ensure server is running
- Check firewall/network

### "Machine fingerprint mismatch"
- Certificate from different machine
- Re-run installer to activate this machine

### "Docker login failed"
- Docker PAT expired
- Contact admin for new activation

### "Service not allowed"
- Upgrade to higher tier
- Contact admin

## Tier Limits

| Tier | Services | Machines | Validity |
|------|----------|----------|----------|
| Trial | frontend | 1 | 14 days |
| Basic | frontend, backend | 3 | 365 days |
| Pro | + analytics | 10 | 365 days |
| Enterprise | all | 100 | 365 days |
version: '3.8'

services:
  ai-dashboard-frontend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3005:3005"
    environment:
      - NODE_ENV=production
      - DATA_SOURCE=mock
      - NEXT_PUBLIC_DATA_SOURCE=mock
      - BACKEND_URL=http://192.168.1.204:8000/api
      - DATA_FOLDER_PATH=./data/
    volumes:
      # Mount the data directory for JSON files
      # On Windows make sure host path is absolute and container path is absolute.
      # Use /app/data because the container's WORKDIR is /app in the Dockerfile.
      - ../data:/app/data:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3005/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s