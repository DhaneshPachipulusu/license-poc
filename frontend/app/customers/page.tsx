'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getCustomers, createCustomer } from '@/lib/api';
import { formatDate, copyToClipboard } from '@/lib/utils';
import { Plus, Search, Users, Check, Copy, ChevronRight } from 'lucide-react';
import FormModal, { FormField, SuccessConfig } from '@/components/FormModal';

interface Customer {
  id: string;
  company_name: string;
  product_key: string;
  machine_limit: number;
  valid_days: number;
  revoked: boolean;
  created_at: string;
}

// Form fields configuration
const customerFields: FormField[] = [
  {
    name: 'company_name',
    label: 'Company Name',
    type: 'text',
    required: true,
    placeholder: 'Acme Corporation',
  },
  {
    name: 'tier',
    label: 'License Tier',
    type: 'select',
    default: 'basic',
    options: [
      { label: 'Trial', value: 'trial' },
      { label: 'Basic', value: 'basic' },
      { label: 'Pro', value: 'pro' },
      { label: 'Enterprise', value: 'enterprise' },
    ],
  },
  {
    name: 'machine_limit',
    label: 'Machine Limit',
    type: 'number',
    default: 3,
    min: 1,
    max: 100,
  },
  {
    name: 'valid_days',
    label: 'Valid Days',
    type: 'number',
    default: 365,
    min: 1,
    max: 3650,
  },
  {
    name: 'notes',
    label: 'Notes',
    type: 'textarea',
    placeholder: 'Any additional notes...',
    required: false,
  },
];

// Success configuration
const customerSuccessConfig: SuccessConfig = {
  title: 'Customer Created!',
  message: 'Share this product key with your customer:',
  highlightField: 'customer.product_key',
  highlightLabel: 'Product Key',
  copyable: true,
  viewLink: {
    label: 'View Customer',
    href: (result) => `/customers/${result.customer.id}`,
  },
};

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  useEffect(() => {
    loadCustomers();
  }, []);

  async function loadCustomers() {
    try {
      const data = await getCustomers();
      setCustomers(data.customers || []);
    } catch (error) {
      console.error('Failed to load customers:', error);
    } finally {
      setLoading(false);
    }
  }

  function handleCopyKey(key: string) {
    copyToClipboard(key);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  }

  const filteredCustomers = customers.filter(c =>
    c.company_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.product_key.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '30px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
            Customers
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
            Manage your licensed customers
          </p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Plus size={20} />
          Add Customer
        </button>
      </div>

      {/* Search Bar */}
      <div style={{ position: 'relative' }}>
        <Search size={20} color="var(--text-muted)" style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)' }} />
        <input
          type="text"
          placeholder="Search customers by name or product key..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="form-input"
          style={{ paddingLeft: '48px' }}
        />
      </div>

      {/* Customers Table */}
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '80px 0' }}>
          <div style={{ width: '40px', height: '40px', border: '2px solid #4f46e5', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        </div>
      ) : filteredCustomers.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '64px 0' }}>
          <div style={{ width: '80px', height: '80px', margin: '0 auto 24px', borderRadius: '50%', backgroundColor: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Users size={40} color="var(--text-muted)" />
          </div>
          <h3 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '8px' }}>
            {searchTerm ? 'No customers found' : 'No customers yet'}
          </h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>
            {searchTerm ? 'Try a different search term' : 'Get started by adding your first customer'}
          </p>
          {!searchTerm && (
            <button onClick={() => setShowModal(true)} className="btn btn-primary">
              Add Your First Customer
            </button>
          )}
        </div>
      ) : (
        <div className="table-container">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--bg-tertiary)' }}>
                <th className="table-header">Company</th>
                <th className="table-header">Product Key</th>
                <th className="table-header">Machine Limit</th>
                <th className="table-header">Valid Days</th>
                <th className="table-header">Status</th>
                <th className="table-header">Created</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCustomers.map((customer, index) => (
                <tr key={customer.id} className="table-row" style={{ animationDelay: `${index * 0.03}s` }}>
                  <td className="table-cell">
                    <Link href={`/customers/${customer.id}`} style={{ fontWeight: 500, color: 'var(--text-primary)', textDecoration: 'none' }}>
                      {customer.company_name}
                    </Link>
                  </td>
                  <td className="table-cell">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <code style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', backgroundColor: 'var(--bg-tertiary)', padding: '4px 8px', borderRadius: '4px', color: '#4f46e5' }}>
                        {customer.product_key}
                      </code>
                      <button
                        onClick={() => handleCopyKey(customer.product_key)}
                        style={{ padding: '4px', background: 'none', border: 'none', cursor: 'pointer', borderRadius: '4px' }}
                        title="Copy to clipboard"
                      >
                        {copiedKey === customer.product_key ? (
                          <Check size={16} color="#059669" />
                        ) : (
                          <Copy size={16} color="var(--text-muted)" />
                        )}
                      </button>
                    </div>
                  </td>
                  <td className="table-cell" style={{ color: 'var(--text-secondary)' }}>
                    {customer.machine_limit}
                  </td>
                  <td className="table-cell" style={{ color: 'var(--text-secondary)' }}>
                    {customer.valid_days} days
                  </td>
                  <td className="table-cell">
                    <span className="badge" style={{
                      backgroundColor: customer.revoked ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                      color: customer.revoked ? '#dc2626' : '#059669',
                      borderColor: customer.revoked ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                    }}>
                      {customer.revoked ? 'Revoked' : 'Active'}
                    </span>
                  </td>
                  <td className="table-cell" style={{ color: 'var(--text-muted)' }}>
                    {formatDate(customer.created_at)}
                  </td>
                  <td className="table-cell">
                    <Link href={`/customers/${customer.id}`} style={{ color: '#4f46e5', textDecoration: 'none', fontSize: '14px', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '4px' }}>
                      View Details <ChevronRight size={16} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Customer Modal */}
      <FormModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Add New Customer"
        subtitle="Create a new licensed customer"
        fields={customerFields}
        submitLabel="Create Customer"
        onSubmit={(data) => createCustomer(data)}
        onSuccess={() => loadCustomers()}
        successConfig={customerSuccessConfig}
        size="md"
      />
    </div>
  );
}