export interface License {
  license_id: string;
  customer: string;
  machine_id: string;
  issued_on: string;
  valid_till: string;
  grace_days: number;
  features: {
    [key: string]: boolean;
  };
  allowed_services: string[];
  revoked: boolean;
  signature: string;
}

export interface LicenseEntry {
  license_id: string;
  customer: string;
  machine_id: string;
  created_at: string;
  revoked: boolean;
  license_json: License;
}

export interface DashboardStats {
  total_licenses: number;
  active_licenses: number;
  expired_licenses: number;
  revoked_licenses: number;
  total_customers: number;
  total_machines: number;
  expiring_soon: number;
}

export interface CustomerStats {
  customer: string;
  total_machines: number;
  active_machines: number;
  license_count: number;
  oldest_license: string;
  newest_license: string;
}

export interface EditLicenseData {
  license_id: string;
  allowed_services: string[];
  features: { [key: string]: boolean };
  valid_till: string;
  grace_days: number;
}