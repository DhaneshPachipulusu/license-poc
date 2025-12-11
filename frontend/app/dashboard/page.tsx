'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getCustomers, getDashboardStats } from '@/lib/api';
import StatCard from '@/components/Statcard';
import { formatDate } from '@/lib/utils';
import { Users, Monitor, Clock, Ban, Plus, UserPlus } from 'lucide-react';

interface CustomerSummary {
  id: string;
  company_name: string;
  product_key: string;
  machine_limit: number;
  valid_days: number;
  revoked: boolean;
  created_at: string;
  active_machines?: number;
}

export default function DashboardPage() {
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total_customers: 0,
    active_machines: 0,
    expiring_soon: 0,
    revoked: 0,
  });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      // Fetch dashboard stats from backend
      const statsData = await getDashboardStats();
      
      // Fetch customers list for table
      const customersData = await getCustomers();
      
      // Update state with real data from backend
      setStats({
        total_customers: statsData.stats.total_customers,
        active_machines: statsData.stats.active_machines,
        expiring_soon: statsData.stats.expiring_soon,
        revoked: statsData.stats.revoked,
      });
      
      setCustomers(customersData.customers || []);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '30px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
            Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
            License management overview
          </p>
        </div>
        
      </div>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '24px' }}>
        <StatCard
          title="Total Customers"
          value={stats.total_customers}
          icon={<Users size={24} />}
          color="indigo"
        />
        <StatCard
          title="Active Machines"
          value={stats.active_machines}
          icon={<Monitor size={24} />}
          color="emerald"
        />
        <StatCard
          title="Expiring Soon"
          value={stats.expiring_soon}
          subtitle="Within 30 days"
          icon={<Clock size={24} />}
          color="amber"
        />
        <StatCard
          title="Revoked"
          value={stats.revoked}
          icon={<Ban size={24} />}
          color="red"
        />
      </div>

      {/* Recent Customers */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)' }}>
            Recent Customers
          </h2>
          <Link href="/customers" style={{ fontSize: '14px', color: '#818cf8', textDecoration: 'none' }}>
            View all →
          </Link>
        </div>

        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 0' }}>
            <div style={{ 
              width: '32px', 
              height: '32px', 
              border: '2px solid #6366f1', 
              borderTopColor: 'transparent', 
              borderRadius: '50%', 
              animation: 'spin 1s linear infinite' 
            }} />
          </div>
        ) : customers.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 0' }}>
            <div style={{ 
              width: '64px', 
              height: '64px', 
              margin: '0 auto 16px', 
              borderRadius: '50%', 
              backgroundColor: 'var(--bg-tertiary)', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}>
              <Users size={32} color="var(--text-muted)" />
            </div>
            <p style={{ color: 'var(--text-muted)' }}>No customers yet</p>
            <Link href="/customers" className="btn btn-primary" style={{ marginTop: '16px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <UserPlus size={18} />
              Add Your First Customer
            </Link>
          </div>
        ) : (
          <div className="table-container">
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--bg-tertiary)' }}>
                  <th className="table-header">Company</th>
                  <th className="table-header">Product Key</th>
                  <th className="table-header">Machine Limit</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Created</th>
                </tr>
              </thead>
              <tbody>
                {customers.slice(0, 5).map((customer, index) => (
                  <tr 
                    key={customer.id} 
                    className="table-row"
                    style={{ animationDelay: `${index * 0.05}s` }}
                  >
                    <td className="table-cell">
                      <Link 
                        href={`/customers/${customer.id}`}
                        style={{ fontWeight: 500, color: 'var(--text-primary)', textDecoration: 'none' }}
                      >
                        {customer.company_name}
                      </Link>
                    </td>
                    <td className="table-cell">
                      <code style={{ 
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: '12px', 
                        backgroundColor: 'var(--bg-tertiary)', 
                        padding: '4px 8px', 
                        borderRadius: '4px', 
                        color: '#818cf8' 
                      }}>
                        {customer.product_key}
                      </code>
                    </td>
                    <td className="table-cell" style={{ color: 'var(--text-secondary)' }}>
                      {customer.machine_limit} machines
                    </td>
                    <td className="table-cell">
                      <span className="badge" style={{
                        backgroundColor: customer.revoked ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                        color: customer.revoked ? '#f87171' : '#34d399',
                        borderColor: customer.revoked ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)',
                      }}>
                        {customer.revoked ? 'Revoked' : 'Active'}
                      </span>
                    </td>
                    <td className="table-cell" style={{ color: 'var(--text-muted)' }}>
                      {formatDate(customer.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}