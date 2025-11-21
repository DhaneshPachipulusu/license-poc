import axios from 'axios';

const API_URL =
  process.env.NEXT_PUBLIC_LICENSE_SERVER_URL ||
  'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

export const licenseApi = {
  // 🟦 1. Get all customers
  getAllCustomers: async () => {
    const res = await api.get('/admin/customers');
    return res.data.customers || [];
  },

  // 🟩 2. Get customer full details (machines + certificates)
  getCustomerDetails: async (customerId: string) => {
    const res = await api.get(`/admin/customers/${customerId}`);
    return res.data;
  },

  // 🟧 3. Convert ALL customers → ALL licenses (flat)
  getAllLicenses: async () => {
    const customerRes = await api.get('/admin/customers');
    const customers = customerRes.data.customers || [];

    const detailResponses = await Promise.all(
      customers.map((c: any) => api.get(`/admin/customers/${c.id}`))
    );

    return detailResponses.flatMap((res: any) => {
      const customer = res.data.customer;
      const machines = res.data.machines || [];

      return machines.map((m: any) => ({
        license_id: m.certificate?.certificate_id || m.id,
        customer: customer.company_name,
        machine_id: m.fingerprint,
        revoked: m.status === 'revoked',
        created_at: m.certificate?.issued_at || new Date().toISOString(),
        license_json: {
          valid_till: m.certificate?.validity?.valid_until,
          allowed_services: m.certificate?.services
            ? Object.keys(m.certificate.services).filter(
                (svc) => m.certificate.services[svc].enabled
              )
            : [],
        },
      }));
    });
  },
};

export default api;
