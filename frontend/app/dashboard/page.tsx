'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Search, ChevronRight, Trash2 } from 'lucide-react'; // ← Added Trash2
import { getCustomers, getCustomer, deleteCustomer } from '@/lib/api'; // ← Added deleteCustomer
import { formatDate, formatDateTime, daysUntilExpiry } from '@/lib/utils';

interface Customer {
  id: string;
  company_name: string;
  product_key: string;
  machine_limit: number;
  valid_days: number;
  revoked: number;
  created_at: string;
  tier: string;
}

interface MachineWithCustomer {
  id: string;
  customer_id: string;
  customer_name: string;
  product_key: string;
  fingerprint: string;
  hostname: string;
  os_info: string | null;
  status: string;
  tier: string;
  valid_until: string | null;
  last_seen: string | null;
  created_at: string;
}

type ActiveView = 'customers' | 'all' | 'active' | 'expiring' | 'revoked';

export default function DashboardPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [machines, setMachines] = useState<MachineWithCustomer[]>([]);
  const [activeView, setActiveView] = useState<ActiveView>('customers');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  // Delete modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [customerToDelete, setCustomerToDelete] = useState<Customer | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Load all data (customers + all machines across customers)
  useEffect(() => {
    async function loadAllData() {
      try {
        setLoading(true);

        // 1. Load customers list
        const customersData = await getCustomers();
        const customerList: Customer[] = customersData.customers || [];
        setCustomers(customerList);

        // 2. Load all machines
        const allMachines: MachineWithCustomer[] = [];

        for (const customer of customerList) {
          try {
            const details = await getCustomer(customer.id);
            const customerMachines = details.machines || [];

            for (const machine of customerMachines) {
              const cert = typeof machine.certificate === 'string'
                ? JSON.parse(machine.certificate)
                : machine.certificate || {};

              allMachines.push({
                id: machine.id,
                customer_id: customer.id,
                customer_name: customer.company_name,
                product_key: customer.product_key,
                fingerprint: machine.fingerprint,
                hostname: machine.hostname,
                os_info: machine.os_info,
                status: machine.status,
                tier: cert?.tier || 'basic',
                valid_until: cert?.validity?.valid_until || null,
                last_seen: machine.last_seen,
                created_at: machine.created_at,
              });
            }
          } catch (e) {
            console.error(`Failed to load machines for customer ${customer.id}`);
          }
        }

        setMachines(allMachines);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setLoading(false);
      }
    }

    loadAllData();
  }, []);

  // Compute stats from loaded machines
  const totalCustomers = customers.length;

  const stats = {
    total: machines.length,
    active: machines.filter(m =>
      m.status !== 'revoked' &&
      (!m.valid_until || daysUntilExpiry(m.valid_until) > 0)
    ).length,
    expiring: machines.filter(m =>
      m.valid_until &&
      daysUntilExpiry(m.valid_until) <= 30 &&
      daysUntilExpiry(m.valid_until) > 0
    ).length,
    revoked: machines.filter(m => m.status === 'revoked').length,
  };

  // Filter machines based on search + active view
  const filteredMachines = machines.filter(machine => {
    const matchesSearch =
      machine.hostname.toLowerCase().includes(searchTerm.toLowerCase()) ||
      machine.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      machine.fingerprint.toLowerCase().includes(searchTerm.toLowerCase());

    if (!matchesSearch) return false;

    if (activeView === 'active')
      return machine.status !== 'revoked' && (!machine.valid_until || daysUntilExpiry(machine.valid_until) > 0);
    if (activeView === 'expiring')
      return machine.valid_until && daysUntilExpiry(machine.valid_until) <= 30 && daysUntilExpiry(machine.valid_until) > 0;
    if (activeView === 'revoked')
      return machine.status === 'revoked';

    return true; // 'all'
  });

  // Open delete confirmation
  const openDeleteModal = (customer: Customer) => {
    setCustomerToDelete(customer);
    setShowDeleteModal(true);
  };

  // Handle actual deletion
  const handleDelete = async () => {
    if (!customerToDelete) return;

    setDeleting(true);
    try {
      await deleteCustomer(customerToDelete.id);
      // Remove from local state
      setCustomers(prev => prev.filter(c => c.id !== customerToDelete.id));
      setMachines(prev => prev.filter(m => m.customer_id !== customerToDelete.id));
      setShowDeleteModal(false);
      setCustomerToDelete(null);
    } catch (error) {
      console.error('Failed to delete customer:', error);
      alert('Failed to delete customer');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', padding: '3px' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: '30px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
          Dashboard
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
          License management overview
        </p>
      </div>

      {/* 5 Stat Cards - Clickable */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '16px' }}>
        <button
          onClick={() => setActiveView('customers')}
          className="card card-hover"
          style={{ borderColor: activeView === 'customers' ? '#818cf8' : 'var(--border-subtle)', cursor: 'pointer' }}
        >
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
            Total Customers
          </p>
          <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#818cf8' }}>
            {totalCustomers}
          </p>
        </button>

        <button
          onClick={() => setActiveView('all')}
          className="card card-hover"
          style={{ borderColor: activeView === 'all' ? '#818cf8' : 'var(--border-subtle)', cursor: 'pointer' }}
        >
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
            Total Machines
          </p>
          <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#818cf8' }}>
            {stats.total}
          </p>
        </button>

        <button
          onClick={() => setActiveView('active')}
          className="card card-hover"
          style={{ borderColor: activeView === 'active' ? '#34d399' : 'var(--border-subtle)', cursor: 'pointer' }}
        >
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
            Active
          </p>
          <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#34d399' }}>
            {stats.active}
          </p>
        </button>

        <button
          onClick={() => setActiveView('expiring')}
          className="card card-hover"
          style={{ borderColor: activeView === 'expiring' ? '#fbbf24' : 'var(--border-subtle)', cursor: 'pointer' }}
        >
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
            Expiring Soon
          </p>
          <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#fbbf24' }}>
            {stats.expiring}
          </p>
        </button>

        <button
          onClick={() => setActiveView('revoked')}
          className="card card-hover"
          style={{ borderColor: activeView === 'revoked' ? '#f87171' : 'var(--border-subtle)', cursor: 'pointer' }}
        >
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
            Revoked
          </p>
          <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#f87171' }}>
            {stats.revoked}
          </p>
        </button>
      </div>

      {/* Content Below Cards */}
      {activeView === 'customers' ? (
        /* Customers Table - WITH DELETE BUTTON */
        <div className="table-container">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--bg-tertiary)' }}>
                <th className="table-header">Company</th>
                <th className="table-header">Product Key</th>
                <th className="table-header">Tier</th>
                <th className="table-header">Machine Limit</th>
                <th className="table-header">Valid Days</th>
                <th className="table-header">Created</th>
                <th className="table-header">Actions</th> {/* ← New column */}
              </tr>
            </thead>
            <tbody>
              {customers.map((customer) => (
                <tr key={customer.id} className="table-row">
                  <td className="table-cell font-medium">{customer.company_name}</td>
                  <td className="table-cell">
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>
                      {customer.product_key}
                    </span>
                  </td>
                  <td className="table-cell">
                    <span className="badge" style={{
                      backgroundColor: customer.tier === 'enterprise' ? 'rgba(16,185,129,0.2)' : customer.tier === 'pro' ? 'rgba(139,92,246,0.2)' : 'rgba(56,189,248,0.2)',
                      color: customer.tier === 'enterprise' ? '#34d399' : customer.tier === 'pro' ? '#a78bfa' : '#38bdf8',
                    }}>
                      {customer.tier.toUpperCase()}
                    </span>
                  </td>
                  <td className="table-cell">{customer.machine_limit}</td>
                  <td className="table-cell">{customer.valid_days}</td>
                  <td className="table-cell">{formatDate(customer.created_at)}</td>
                  <td className="table-cell">
                    <button
                      onClick={() => openDeleteModal(customer)}
                      style={{
                        padding: '6px',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        borderRadius: '6px',
                      }}
                      title="Delete Customer"
                    >
                      <Trash2 size={16} color="#ef4444" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* Machines Table - UNCHANGED */
        <>
          {/* Search */}
          <div style={{ position: 'relative' }}>
            <Search size={20} color="var(--text-muted)" style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Search by hostname, customer, or fingerprint..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input"
              style={{ paddingLeft: '48px' }}
            />
          </div>

          {/* Machines Table */}
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '80px 0' }}>
              <div style={{ width: '40px', height: '40px', border: '2px solid #6366f1', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
            </div>
          ) : filteredMachines.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '64px 0' }}>
              <div style={{ width: '80px', height: '80px', margin: '0 auto 24px', borderRadius: '50%', backgroundColor: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Search size={40} color="var(--text-muted)" />
              </div>
              <h3 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '8px' }}>
                No machines found
              </h3>
              <p style={{ color: 'var(--text-muted)' }}>
                Try adjusting your search or filter
              </p>
            </div>
          ) : (
            <div className="table-container">
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: 'var(--bg-tertiary)' }}>
                    <th className="table-header">Machine</th>
                    <th className="table-header">Customer</th>
                    <th className="table-header">Tier</th>
                    <th className="table-header">Status</th>
                    <th className="table-header">Expires</th>
                    <th className="table-header">Last Seen</th>
                    <th className="table-header">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMachines.map((machine) => {
                    const daysLeft = machine.valid_until ? daysUntilExpiry(machine.valid_until) : null;

                    return (
                      <tr key={machine.id} className="table-row">
                        <td className="table-cell">
                          <div>
                            <p style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{machine.hostname}</p>
                            <p style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
                              {machine.fingerprint.slice(0, 20)}...
                            </p>
                          </div>
                        </td>
                        <td className="table-cell">
                          <Link href={`/customers/${machine.customer_id}`} style={{ color: '#818cf8', textDecoration: 'none' }}>
                            {machine.customer_name}
                          </Link>
                        </td>
                        <td className="table-cell">
                          <span className="badge" style={{
                            backgroundColor: machine.tier === 'enterprise' ? 'rgba(16, 185, 129, 0.2)' : machine.tier === 'pro' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                            color: machine.tier === 'enterprise' ? '#34d399' : machine.tier === 'pro' ? '#a78bfa' : '#38bdf8',
                          }}>
                            {machine.tier.toUpperCase()}
                          </span>
                        </td>
                        <td className="table-cell">
                          <span className="badge" style={{
                            backgroundColor: machine.status === 'revoked' || (daysLeft !== null && daysLeft <= 0) ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                            color: machine.status === 'revoked' || (daysLeft !== null && daysLeft <= 0) ? '#f87171' : '#34d399',
                          }}>
                            {machine.status === 'revoked' ? 'Revoked' : daysLeft !== null && daysLeft <= 0 ? 'Expired' : 'Active'}
                          </span>
                        </td>
                        <td className="table-cell">
                          {machine.valid_until ? (
                            <div>
                              <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                                {formatDate(machine.valid_until)}
                              </p>
                              {daysLeft !== null && daysLeft > 0 && (
                                <p style={{ fontSize: '12px', color: daysLeft <= 30 ? '#fbbf24' : 'var(--text-muted)' }}>
                                  {daysLeft} days left
                                </p>
                              )}
                            </div>
                          ) : (
                            <span style={{ color: 'var(--text-muted)' }}>-</span>
                          )}
                        </td>
                        <td className="table-cell" style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
                          {machine.last_seen ? formatDateTime(machine.last_seen) : 'Never'}
                        </td>
                        <td className="table-cell">
                          <Link href={`/customers/${machine.customer_id}`} style={{ color: '#818cf8', textDecoration: 'none', fontSize: '14px', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '4px' }}>
                            View Customer <ChevronRight size={16} />
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && customerToDelete && (
        <div className="modal-overlay" onClick={() => setShowDeleteModal(false)}>
          <div className="modal-content" style={{ maxWidth: '420px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ textAlign: 'center', padding: '24px' }}>
              <div style={{ width: '64px', height: '64px', margin: '0 auto 16px', borderRadius: '50%', backgroundColor: 'rgba(239, 68, 68, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Trash2 size={32} color="#ef4444" />
              </div>
              <h3 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '8px' }}>
                Delete Customer?
              </h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
                This will permanently delete <strong>{customerToDelete.company_name}</strong> and all associated machines.
              </p>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px' }}>
                This action cannot be undone.
              </p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  onClick={() => setShowDeleteModal(false)}
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                  disabled={deleting}
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  className="btn btn-danger"
                  style={{ flex: 1 }}
                  disabled={deleting}
                >
                  {deleting ? 'Deleting...' : 'Delete Customer'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}