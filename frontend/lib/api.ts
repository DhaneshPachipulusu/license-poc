import axios from 'axios';

// Axios instance with automatic HttpOnly cookie support
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Critical for HttpOnly cookies
  timeout: 10000,
});

// Auth APIs
export async function login(username: string, password: string) {
  const { data } = await api.post('/auth/login', { username, password });
  return data;
}

export async function logout() {
  const { data } = await api.post('/auth/logout');
  return data;
}

export async function authMe() {
  const { data } = await api.get('/auth/me');
  return data;
}

// Dashboard Stats
export async function getDashboardStats() {
  const { data } = await api.get<{
    success: boolean;
    stats: {
      total_customers: number;
      active_machines: number;
      expiring_soon: number;
      revoked: number;
      expired: number;
    };
    timestamp: string;
  }>('/api/v1/dashboard/stats');
  return data;
}

// Customer APIs
export async function getCustomers() {
  const { data } = await api.get<{ customers: any[] }>('/api/v1/admin/customers');
  return data;
}

export async function getCustomer(customerId: string) {
  const { data } = await api.get<{ customer: any; machines: any[] }>(`/api/v1/admin/customers/${customerId}`);
  return data;
}

// FIXED: createCustomer - now properly defined and typed
export async function createCustomer(payload: {
  company_name: string;
  tier?: string;
  machine_limit?: number;
  valid_days?: number;
  notes?: string;
}) {
  const { data } = await api.post<{
    success: boolean;
    customer: any;
    message: string;
  }>('/api/v1/admin/customers', {
    company_name: payload.company_name,
    tier: payload.tier || 'basic',
    machine_limit: payload.machine_limit || 3,
    valid_days: payload.valid_days || 365,
    notes: payload.notes || '',
  });

  return data;
}

// Machine APIs
export async function revokeMachine(machineId: string) {
  const { data } = await api.post(
    `/api/v1/admin/machines/${machineId}/revoke`
  );
  return data;
}

// Upgrade/Renew
export async function upgradeCertificate(payload: {
  machine_fingerprint: string;
  additional_days?: number;
  new_tier?: string;
  new_machine_limit?: number;
}) {
  const { data } = await api.post<{ success: boolean; certificate: any }>(
    '/api/v1/admin/upgrade',
    payload
  );
  return data;
}

// Activation (for testing)
export async function activateMachine(payload: {
  product_key: string;
  machine_fingerprint: string;
  hostname: string;
  os_info?: string;
  app_version?: string;
}) {
  const { data } = await api.post<{ success: boolean; message: string; certificate: any }>(
    '/api/v1/activate',
    payload
  );
  return data;
}

// Health check
export async function healthCheck() {
  const { data } = await api.get<{ status: string; version: string }>('/health');
  return data;
}

export default api;