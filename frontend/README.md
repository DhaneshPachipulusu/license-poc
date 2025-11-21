# License Admin Dashboard - Complete Setup Guide

## 🎯 Overview

A complete Next.js admin dashboard for managing your FastAPI License Server. Features include:

- 📊 **Dashboard**: Real-time statistics and overview
- 🔑 **License Management**: View, edit, renew, and revoke licenses
- 👥 **Customer Management**: Group licenses by customer with machine tracking
- 🔍 **Search & Filter**: Advanced filtering and search capabilities
- 📈 **Analytics**: Visual charts and reports
- ⚡ **Real-time Updates**: Live status monitoring

## 📦 What's Included

```
license-admin-ui/
├── app/                      # Next.js 14 App Router
│   ├── page.tsx             # Dashboard home
│   ├── licenses/            # License management
│   ├── customers/           # Customer management
│   ├── analytics/           # Analytics & reports
│   └── globals.css          # Global styles
├── components/              # Reusable React components
│   ├── Sidebar.tsx          # Navigation sidebar
│   └── StatCard.tsx         # Statistics cards
├── lib/                     # Utilities
│   ├── api.ts              # API client
│   └── utils.ts            # Helper functions
├── types/                   # TypeScript definitions
│   └── license.ts          # License types
└── package.json            # Dependencies
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.8+ (for FastAPI backend)
- Your FastAPI License Server running

### Step 1: Update FastAPI Backend

1. **Backup your current `app.py`**:
   ```bash
   cp app.py app.py.backup
   ```

2. **Replace with updated version** (includes CORS and JSON endpoints):
   ```bash
   # Use the updated_app.py file provided
   cp updated_app.py app.py
   ```

3. **Install CORS middleware** (if not already installed):
   ```bash
   pip install fastapi-cors
   ```

4. **Restart your FastAPI server**:
   ```bash
   uvicorn app:app --reload --port 8000
   ```

### Step 2: Setup Next.js Dashboard

1. **Navigate to the dashboard directory**:
   ```bash
   cd license-admin-ui
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Create environment file**:
   ```bash
   cp .env.example .env.local
   ```

4. **Edit `.env.local`** and set your license server URL:
   ```env
   NEXT_PUBLIC_LICENSE_SERVER_URL=http://localhost:8000
   ```

5. **Run the development server**:
   ```bash
   npm run dev
   ```

6. **Open your browser**:
   ```
   http://localhost:3000
   ```

## 🎨 Features Overview

### 1. Dashboard (Home Page)

- **Statistics Cards**: Total licenses, active, expiring, customers
- **System Health**: Uptime, machines, response time
- **Recent Licenses**: Latest 5 licenses with status
- **Quick Actions**: Create license, view reports

**URL**: `http://localhost:3000/`

### 2. License Management

- **Search**: Find licenses by ID, customer, or machine ID
- **Filters**: Filter by status (active, expired, expiring, revoked)
- **Sorting**: Sort by created date, expiry date, or customer
- **Actions**:
  - View details
  - Edit license
  - Renew (quick 30-day button)
  - Revoke with confirmation
  - Copy license ID

**URL**: `http://localhost:3000/licenses`

### 3. Customer Management

- **Customer List**: All customers with statistics
- **Expandable Details**: Click to see machines and licenses
- **Machine Tracking**: View all machines per customer
- **License Grouping**: See all licenses for each customer
- **Statistics**:
  - Total licenses
  - Active licenses
  - Total machines
  - Active machines

**URL**: `http://localhost:3000/customers`

### 4. Analytics (Coming Soon)

- Charts and graphs
- License trends
- Customer growth
- Revenue tracking

**URL**: `http://localhost:3000/analytics`

## 🔧 API Endpoints Used

The dashboard uses these FastAPI endpoints:

### New JSON Endpoints (Added)

```
GET  /admin/licenses/json          # Get all licenses
GET  /admin/license/{id}/json      # Get single license
GET  /admin/stats                   # Get dashboard stats
GET  /admin/search?q={query}        # Search licenses
POST /admin/update-license          # Update license details
```

### Existing Endpoints (Already Working)

```
POST /register                      # Register new license
POST /validate                      # Validate license
POST /renew                         # Renew license
POST /revoke                        # Revoke license
GET  /public_key                    # Get public key
```

## 📝 Configuration

### Environment Variables

Create `.env.local` file:

```env
# Required
NEXT_PUBLIC_LICENSE_SERVER_URL=http://localhost:8000

# Optional (for production)
NODE_ENV=production
NEXT_PUBLIC_API_TIMEOUT=10000
```

### FastAPI CORS Settings

In your `app.py`, CORS is configured for:
- `http://localhost:3000` (development)
- `http://127.0.0.1:3000` (alternative)

For production, update these origins in the CORS middleware.

## 🎯 Usage Examples

### Creating a New License

```typescript
import { licenseApi } from '@/lib/api';

const license = await licenseApi.registerLicense(
  'ACME-CORP',           // customer
  'machine-id-12345'     // machine_id
);
```

### Renewing a License

```typescript
await licenseApi.renewLicense('LIC-abc123', 30);  // 30 days
```

### Searching Licenses

```typescript
const results = await licenseApi.searchLicenses('ACME');
```

### Getting Statistics

```typescript
const stats = await licenseApi.getStats();
// Returns: { total_licenses, active_licenses, ... }
```

## 🏗️ Building for Production

### Build Next.js App

```bash
cd license-admin-ui
npm run build
npm start
```

### Deploy Options

1. **Vercel** (Recommended for Next.js):
   ```bash
   npm install -g vercel
   vercel deploy
   ```

2. **Docker**:
   ```dockerfile
   FROM node:18-alpine
   WORKDIR /app
   COPY package*.json ./
   RUN npm install
   COPY . .
   RUN npm run build
   CMD ["npm", "start"]
   ```

3. **Static Export** (if API is on same domain):
   ```bash
   npm run build
   # Upload 'out' folder to web server
   ```

## 🔐 Security Considerations

1. **API Authentication**: Add JWT or API keys to FastAPI
2. **HTTPS**: Use HTTPS in production
3. **CORS**: Restrict origins to your domain
4. **Rate Limiting**: Add rate limiting to API endpoints
5. **Input Validation**: Validate all user inputs

## 🐛 Troubleshooting

### CORS Errors

**Problem**: `Access to fetch has been blocked by CORS policy`

**Solution**:
1. Verify FastAPI is running with CORS middleware
2. Check `allow_origins` in `app.py` includes your Next.js URL
3. Restart FastAPI server after changes

### API Connection Failed

**Problem**: `Network Error` or `Failed to load`

**Solution**:
1. Verify FastAPI server is running: `curl http://localhost:8000/admin/stats`
2. Check `.env.local` has correct `NEXT_PUBLIC_LICENSE_SERVER_URL`
3. Verify no firewall blocking port 8000

### TypeScript Errors

**Problem**: Type errors during build

**Solution**:
```bash
npm run lint
# Fix any TypeScript errors shown
```

## 📚 Component Structure

### StatCard Component

```tsx
<StatCard
  title="Total Licenses"
  value={123}
  change="+12% from last month"
  changeType="positive"
  icon={Key}
  color="blue"
/>
```

### Status Badge

```tsx
// Auto-colored based on license status
<span className="status-badge status-active">
  Active
</span>
```

## 🎨 Customization

### Colors

Edit `tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        500: '#yourcolor',
      },
    },
  },
}
```

### Logo

Replace in `components/Sidebar.tsx`:

```tsx
<Shield className="w-6 h-6" />
// Replace with:
<img src="/logo.png" alt="Logo" className="w-6 h-6" />
```

## 📈 Future Enhancements

- [ ] Analytics dashboard with Chart.js
- [ ] Export reports (PDF, Excel)
- [ ] Email notifications for expiring licenses
- [ ] Bulk operations (renew multiple, bulk revoke)
- [ ] Activity logs and audit trail
- [ ] Role-based access control (RBAC)
- [ ] Dark mode
- [ ] Mobile responsive optimization

## 🤝 Support

For issues or questions:
1. Check troubleshooting section
2. Review FastAPI logs
3. Check browser console for errors
4. Verify all dependencies are installed

## 📄 License

This admin dashboard is part of your License Control Platform.

---

## ⚡ Quick Commands

```bash
# Development
npm run dev              # Start dev server
npm run build           # Build for production
npm run start           # Start production server
npm run lint            # Check for errors

# FastAPI Backend
uvicorn app:app --reload --port 8000    # Start server
python -m pytest tests/                  # Run tests
```

---

Made with ❤️ for License Control Platform