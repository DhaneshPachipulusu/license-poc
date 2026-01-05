'use client';

import { useState, useEffect } from 'react';
import { FileText, Plus } from 'lucide-react';
import { useAuth } from '@/components/AuthGuard';
import { getCustomers } from '@/lib/api';
import FormModal, { FormField, SuccessConfig } from '@/components/FormModal';

export default function CreateCertificatePage() {
  const { isAuthenticated } = useAuth();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [customers, setCustomers] = useState<any[]>([]);
  const [machines, setMachines] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState('');

  // Fetch customers on mount (only if authenticated)
  useEffect(() => {
    if (isAuthenticated) {
      console.log('📄 Loading customers for certificates...');
      fetchCustomers();
    }
  }, [isAuthenticated]);

  // Fetch machines when customer selected
  useEffect(() => {
    if (selectedCustomer && isAuthenticated) {
      fetchMachines(selectedCustomer);
    }
  }, [selectedCustomer, isAuthenticated]);

  async function fetchCustomers() {
    try {
      const data = await getCustomers();
      console.log('Customers:', data);
      setCustomers(data.customers || []);
    } catch (err) {
      console.error('Failed to fetch customers:', err);
    }
  }

  async function fetchMachines(customerId: string) {
    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/customers/${customerId}/machines`,
        {
          credentials: 'include', // Sends HttpOnly cookie automatically
        }
      );

      if (!res.ok) {
        throw new Error('Failed to fetch machines');
      }

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
      default: true
    },
    {
      name: 'service_backend',
      label: 'Enable Backend',
      type: 'checkbox',
      default: true
    },
    {
      name: 'service_analytics',
      label: 'Enable Analytics',
      type: 'checkbox',
      default: false
    },
    {
      name: 'service_monitoring',
      label: 'Enable Monitoring',
      type: 'checkbox',
      default: false
    }
  ];

  async function handleGenerateCertificate(formData: Record<string, any>) {
    const payload = {
      customer_id: formData.customer_id,
      machine_fingerprint: formData.machine_fingerprint,
      hostname: formData.hostname,
      os_info: 'Windows 11',
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

    const res = await fetch(
      'http://localhost:8000/api/v1/certificates/custom-generate',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(payload)
      }
    );

    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Failed to generate certificate');
    }

    const result = await res.json();

    const blob = new Blob(
      [JSON.stringify(result.certificate, null, 2)],
      { type: 'application/json' }
    );
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
    <div style={{ padding: '3px' }}>
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '32px', fontWeight: 'bold' }}>
          Custom Certificate Builder
        </h1>
        <p>Create flexible, custom-configured certificates</p>
      </div>

      <button
        onClick={() => setIsModalOpen(true)}
        className="btn btn-primary"
        style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
      >
        <Plus size={20} />
        Generate Custom Certificate
      </button>

      <FormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Generate Custom Certificate"
        fields={certificateFields}
        submitLabel="Generate Certificate"
        onSubmit={handleGenerateCertificate}
        successConfig={successConfig}
        size="lg"
      />
    </div>
  );
}
