'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getCustomers, getCustomer } from '@/lib/api';
import { formatDate, formatDateTime, daysUntilExpiry } from '@/lib/utils';
import { Search, FileText, ChevronRight } from 'lucide-react';

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

export default function LicensesPage() {
  const [machines, setMachines] = useState<MachineWithCustomer[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'active' | 'expiring' | 'revoked'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadAllMachines();
  }, []);

  async function loadAllMachines() {
    try {
      const customersData = await getCustomers();
      const customers = customersData.customers || [];
      
      const allMachines: MachineWithCustomer[] = [];
      
      for (const customer of customers) {
        try {
          const details = await getCustomer(customer.id);
          const customerMachines = details.machines || [];
          
          for (const machine of customerMachines) {
            const cert = typeof machine.certificate === 'string' 
              ? JSON.parse(machine.certificate) 
              : machine.certificate;
            
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
      console.error('Failed to load machines:', error);
    } finally {
      setLoading(false);
    }
  }

  const filteredMachines = machines.filter(machine => {
    const matchesSearch = 
      machine.hostname.toLowerCase().includes(searchTerm.toLowerCase()) ||
      machine.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      machine.fingerprint.toLowerCase().includes(searchTerm.toLowerCase());

    if (!matchesSearch) return false;

    switch (filter) {
      case 'active':
        return machine.status !== 'revoked' && (!machine.valid_until || daysUntilExpiry(machine.valid_until) > 0);
      case 'expiring':
        return machine.valid_until && daysUntilExpiry(machine.valid_until) <= 30 && daysUntilExpiry(machine.valid_until) > 0;
      case 'revoked':
        return machine.status === 'revoked';
      default:
        return true;
    }
  });

  const stats = {
    total: machines.length,
    active: machines.filter(m => m.status !== 'revoked').length,
    expiring: machines.filter(m => m.valid_until && daysUntilExpiry(m.valid_until) <= 30 && daysUntilExpiry(m.valid_until) > 0).length,
    revoked: machines.filter(m => m.status === 'revoked').length,
  };

  const filterButtons = [
    { key: 'all', label: 'Total', value: stats.total, color: '#818cf8' },
    { key: 'active', label: 'Active', value: stats.active, color: '#34d399' },
    { key: 'expiring', label: 'Expiring Soon', value: stats.expiring, color: '#fbbf24' },
    { key: 'revoked', label: 'Revoked', value: stats.revoked, color: '#f87171' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: '30px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
          All Licenses
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
          View all activated machines and licenses across customers
        </p>
      </div>

      {/* Quick Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
        {filterButtons.map((btn) => (
          <button
            key={btn.key}
            onClick={() => setFilter(btn.key as any)}
            className="card card-hover"
            style={{ 
              textAlign: 'left', 
              cursor: 'pointer',
              borderColor: filter === btn.key ? btn.color : 'var(--border-subtle)',
            }}
          >
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>{btn.label}</p>
            <p style={{ fontSize: '24px', fontWeight: 'bold', color: btn.color }}>{btn.value}</p>
          </button>
        ))}
      </div>

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
            <FileText size={40} color="var(--text-muted)" />
          </div>
          <h3 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '8px' }}>
            {searchTerm || filter !== 'all' ? 'No licenses found' : 'No activated licenses yet'}
          </h3>
          <p style={{ color: 'var(--text-muted)' }}>
            {searchTerm ? 'Try a different search term' : filter !== 'all' ? 'No licenses match this filter' : 'Licenses will appear here once customers activate'}
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
              {filteredMachines.map((machine, index) => {
                const daysLeft = machine.valid_until ? daysUntilExpiry(machine.valid_until) : null;
                
                return (
                  <tr key={machine.id} className="table-row" style={{ animationDelay: `${index * 0.02}s` }}>
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
                        borderColor: machine.tier === 'enterprise' ? 'rgba(16, 185, 129, 0.3)' : machine.tier === 'pro' ? 'rgba(139, 92, 246, 0.3)' : 'rgba(56, 189, 248, 0.3)',
                      }}>
                        {machine.tier.toUpperCase()}
                      </span>
                    </td>
                    <td className="table-cell">
                      <span className="badge" style={{
                        backgroundColor: machine.status === 'revoked' ? 'rgba(239, 68, 68, 0.2)' : daysLeft !== null && daysLeft <= 0 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                        color: machine.status === 'revoked' ? '#f87171' : daysLeft !== null && daysLeft <= 0 ? '#f87171' : '#34d399',
                        borderColor: machine.status === 'revoked' ? 'rgba(239, 68, 68, 0.3)' : daysLeft !== null && daysLeft <= 0 ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)',
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
    </div>
  );
}