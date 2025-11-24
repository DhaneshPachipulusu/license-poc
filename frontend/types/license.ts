export interface Customer {
  id: string;
  company_name: string;
  product_key: string;
  machine_limit: number;
  valid_days: number;
  allowed_services: string[];
  revoked: boolean;
  created_at: string;
  updated_at: string;
}

export interface Machine {
  id: string;
  customer_id: string;
  machine_id: string;
  fingerprint: string;
  hostname: string;
  os_info: string | null;
  app_version: string | null;
  ip_address: string | null;
  status: 'active' | 'revoked';
  last_seen: string | null;
  created_at: string;
  certificate: Certificate | null;
}

export interface Certificate {
  certificate_id: string;
  customer_id: string;
  customer_name: string;
  machine_fingerprint: string;
  hostname: string;
  product_key: string;
  tier: 'trial' | 'basic' | 'pro' | 'enterprise';
  validity: {
    issued_at: string;
    valid_until: string;
    valid_days: number;
  };
  machine_limit: number;
  services: Record<string, { enabled: boolean }>;
  docker?: {
    registries: Record<string, { allowed_images: { image: string }[] }>;
  };
  signature: string;
}

export interface ActivityLog {
  id: string;
  action: string;
  customer_id: string | null;
  machine_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export interface DashboardStats {
  total_customers: number;
  active_machines: number;
  expiring_soon: number;
  revoked_licenses: number;
}

export type Tier = 'trial' | 'basic' | 'pro' | 'enterprise';