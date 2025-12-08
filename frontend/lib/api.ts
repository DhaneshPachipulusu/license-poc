import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Customer APIs
export async function getCustomers() {
  const { data } = await api.get<{ customers: any[] }>('/api/v1/admin/customers');
  return data;
}

export async function getCustomer(customerId: string) {
  const { data } = await api.get<{ customer: any; machines: any[] }>(`/api/v1/admin/customers/${customerId}`);
  return data;
}

export async function createCustomer(payload: {
  company_name: string;
  tier: string;
  machine_limit: number;
  valid_days: number;
  notes?: string;
}) {
  const { data } = await api.post<{ success: boolean; customer: any; tier: string; message: string }>(
    '/api/v1/admin/customers',
    payload
  );
  return data;
}

// Machine APIs
export async function revokeMachine(machineId: string) {
  const { data } = await api.post<{ success: boolean; message: string }>(
    `/api/v1/admin/revoke/${machineId}`
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

// Upgrade/Renew
export async function upgradeCertificate(payload: {
  machine_fingerprint: string;
  new_tier?: string;
  additional_days?: number;
  new_machine_limit?: number;
  additional_services?: string[];
}) {
  const { data } = await api.post<{ success: boolean; certificate: any }>(
    '/api/v1/upgrade',
    payload
  );
  return data;
}

// Health check
export async function healthCheck() {
  const { data } = await api.get<{ status: string; version: string }>('/health');
  return data;
}
