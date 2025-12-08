'use client';

import { useState, useEffect } from 'react';
import { FileText, Plus } from 'lucide-react';
import FormModal, { FormField, SuccessConfig } from '@/components/FormModal';

export default function CreateCertificatePage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [customers, setCustomers] = useState<any[]>([]);
  const [machines, setMachines] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState('');

  // Fetch customers on mount
  useEffect(() => {
    fetchCustomers();
  }, []);

  // Fetch machines when customer selected
  useEffect(() => {
    if (selectedCustomer) {
      fetchMachines(selectedCustomer);
    }
  }, [selectedCustomer]);

  async function fetchCustomers() {
  try {
    const res = await fetch('http://localhost:8000/api/v1/admin/customers');
    const data = await res.json();
    
    console.log('Customers:', data);
    
    setCustomers(data.customers || []);
  } catch (err) {
    console.error('Failed to fetch customers:', err);
  }
}

  async function fetchMachines(customerId: string) {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/customers/${customerId}/machines`);
      const data = await res.json();
      setMachines(data.machines || []);
    } catch (err) {
      console.error('Failed to fetch machines:', err);
      setMachines([]);
    }
  }

  const certificateFields: FormField[] = [
    {
      name: 'customer_id',
      label: 'Customer',
      type: 'select',
      required: true,
      options: customers.map(c => ({
        label: `${c.company_name} (${c.product_key})`,
        value: c.id
      })),
      helpText: 'Select the customer for this certificate'
    },
    {
      name: 'machine_fingerprint',
      label: 'Machine Fingerprint',
      type: 'text',
      required: true,
      placeholder: 'Enter machine fingerprint or generate new',
      helpText: 'Hardware fingerprint to bind this certificate to'
    },
    {
      name: 'hostname',
      label: 'Hostname',
      type: 'text',
      required: true,
      placeholder: 'e.g., DESKTOP-ABC123',
      helpText: 'Computer name for identification'
    },
    {
      name: 'tier',
      label: 'Tier',
      type: 'select',
      default: 'custom',
      options: ['trial', 'basic', 'pro', 'enterprise', 'custom'],
      helpText: 'License tier (use "custom" for flexible config)'
    },
    {
      name: 'valid_days',
      label: 'Valid Days',
      type: 'number',
      default: 365,
      min: 1,
      max: 3650,
      required: true,
      helpText: 'How many days this certificate is valid'
    },
    {
      name: 'machine_limit',
      label: 'Machine Limit',
      type: 'number',
      default: 3,
      min: 1,
      max: 1000,
      helpText: 'Maximum machines allowed for this customer'
    },
    {
      name: 'max_models',
      label: 'Max AI Models',
      type: 'number',
      default: 5,
      min: 1,
      max: 100,
      helpText: 'Maximum number of AI models allowed'
    },
    {
      name: 'max_data_gb',
      label: 'Max Data (GB)',
      type: 'number',
      default: 100,
      min: 1,
      max: 10000,
      helpText: 'Maximum data storage in gigabytes'
    },
    {
      name: 'max_concurrent_users',
      label: 'Max Concurrent Users',
      type: 'number',
      default: 10,
      min: 1,
      max: 1000,
      helpText: 'Maximum simultaneous users'
    },
    {
      name: 'service_frontend',
      label: 'Enable Frontend',
      type: 'checkbox',
      default: true,
      placeholder: 'Include frontend service'
    },
    {
      name: 'service_backend',
      label: 'Enable Backend',
      type: 'checkbox',
      default: true,
      placeholder: 'Include backend service'
    },
    {
      name: 'service_analytics',
      label: 'Enable Analytics',
      type: 'checkbox',
      default: false,
      placeholder: 'Include analytics service'
    },
    {
      name: 'service_monitoring',
      label: 'Enable Monitoring',
      type: 'checkbox',
      default: false,
      placeholder: 'Include monitoring service'
    }
  ];

  async function handleGenerateCertificate(formData: Record<string, any>) {
    // Transform form data to API format
    const payload = {
      customer_id: formData.customer_id,
      machine_fingerprint: formData.machine_fingerprint,
      hostname: formData.hostname,
      os_info: 'Windows 11', // You can make this dynamic
      tier: formData.tier,
      valid_days: formData.valid_days,
      machine_limit: formData.machine_limit,
      max_models: formData.max_models,
      max_data_gb: formData.max_data_gb,
      max_concurrent_users: formData.max_concurrent_users,
      services: {
        frontend: formData.service_frontend,
        backend: formData.service_backend,
        analytics: formData.service_analytics,
        monitoring: formData.service_monitoring
      },
      save_to_db: true
    };

    const res = await fetch('http://localhost:8000/api/v1/certificates/custom-generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Failed to generate certificate');
    }

    const result = await res.json();
    
    // Download certificate
    const blob = new Blob([JSON.stringify(result.certificate, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = result.download_filename || 'certificate.json';
    a.click();
    URL.revokeObjectURL(url);

    return result;
  }

  const successConfig: SuccessConfig = {
    title: 'Certificate Generated!',
    message: 'Custom certificate has been created and downloaded',
    highlightField: 'certificate.certificate_id',
    highlightLabel: 'Certificate ID',
    copyable: true,
    viewLink: {
      label: 'View Details',
      href: (data) => `/certificates/${data.certificate.certificate_id}`
    }
  };

  return (
    <div style={{ padding: '32px' }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '32px', fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '8px' }}>
          Custom Certificate Builder
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Create flexible, custom-configured certificates for B2B customers
        </p>
      </div>

      {/* Action Button */}
      <button
        onClick={() => setIsModalOpen(true)}
        className="btn btn-primary"
        style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
      >
        <Plus size={20} />
        Generate Custom Certificate
      </button>

      {/* Info Cards */}
      <div style={{ marginTop: '32px', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}>
        <div className="stat-card">
          <FileText size={24} color="#4f46e5" />
          <div style={{ marginTop: '12px' }}>
            <h3 style={{ fontSize: '28px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
              {customers.length}
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Available Customers</p>
          </div>
        </div>

        <div className="stat-card">
          <FileText size={24} color="#059669" />
          <div style={{ marginTop: '12px' }}>
            <h3 style={{ fontSize: '28px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
              Custom
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Flexible Configuration</p>
          </div>
        </div>

        <div className="stat-card">
          <FileText size={24} color="#f59e0b" />
          <div style={{ marginTop: '12px' }}>
            <h3 style={{ fontSize: '28px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
              Instant
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Generate & Download</p>
          </div>
        </div>
      </div>

      {/* Form Modal */}
      <FormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Generate Custom Certificate"
        subtitle="Configure services, limits, and validity period"
        fields={certificateFields}
        submitLabel="Generate Certificate"
        onSubmit={handleGenerateCertificate}
        successConfig={successConfig}
        size="lg"
      />
    </div>
  );
}