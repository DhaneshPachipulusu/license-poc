'use client';

import { useEffect, useState } from 'react';
import { getCustomers, getDashboardStats, getCustomer } from '@/lib/api';
import StatCard from '@/components/Statcard';
import { formatDate } from '@/lib/utils';
import { Users, Monitor, Clock, Ban } from 'lucide-react';

interface DashboardCustomer {
  id: string;
  company_name: string;
  product_key: string;
  machine_limit: number;
  valid_days: number;
  created_at: string;
  status: 'Active' | 'Revoked' | 'No License';
}

type FilterType = 'all' | 'active' | 'revoked' | 'expiring';

export default function DashboardPage() {
  const [customers, setCustomers] = useState<DashboardCustomer[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterType>('all');

  const [stats, setStats] = useState({
    total_customers: 0,
    active_machines: 0,
    expiring_soon: 0,
    revoked: 0,
  });

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      const dashboardStats = await getDashboardStats();
      const customersResp = await getCustomers();

      let activeMachines = 0;
      let revokedMachines = 0;

      const result: DashboardCustomer[] = [];

      for (const c of customersResp.customers) {
        const details = await getCustomer(c.id);

        const activeCount = details.machines.filter(
          (m: any) => m.status === 'active'
        ).length;

        const revokedCount = details.machines.filter(
          (m: any) => m.status === 'revoked'
        ).length;

        activeMachines += activeCount;
        revokedMachines += revokedCount;

        let status: DashboardCustomer['status'] = 'No License';
        if (activeCount > 0) status = 'Active';
        else if (revokedCount > 0) status = 'Revoked';

        result.push({
          id: c.id,
          company_name: c.company_name,
          product_key: c.product_key,
          machine_limit: c.machine_limit,
          valid_days: c.valid_days,
          created_at: c.created_at,
          status,
        });
      }

      setCustomers(result);

      setStats({
        total_customers: customersResp.customers.length,
        active_machines: activeMachines,
        expiring_soon: dashboardStats.stats.expiring_soon,
        revoked: revokedMachines,
      });
    } catch (err) {
      console.error('Dashboard load failed', err);
    } finally {
      setLoading(false);
    }
  }

  const filteredCustomers = customers.filter((c) => {
    if (filter === 'all') return true;
    if (filter === 'active') return c.status === 'Active';
    if (filter === 'revoked') return c.status === 'Revoked';
    if (filter === 'expiring') return c.valid_days <= 30;
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* HEADER */}
      <div>
        <h1 style={{ fontSize: '30px', fontWeight: 'bold' }}>Dashboard</h1>
        <p>License management overview</p>
      </div>

      {/* STAT CARDS */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '24px',
        }}
      >
        <div onClick={() => setFilter('all')} style={{ cursor: 'pointer' }}>
          <StatCard
            title="Total Customers"
            value={stats.total_customers}
            icon={<Users />}
            color="indigo"
          />
        </div>

        <div onClick={() => setFilter('active')} style={{ cursor: 'pointer' }}>
          <StatCard
            title="Active Machines"
            value={stats.active_machines}
            icon={<Monitor />}
            color="emerald"
          />
        </div>

        <div onClick={() => setFilter('expiring')} style={{ cursor: 'pointer' }}>
          <StatCard
            title="Expiring Soon"
            value={stats.expiring_soon}
            icon={<Clock />}
            color="amber"
          />
        </div>

        <div onClick={() => setFilter('revoked')} style={{ cursor: 'pointer' }}>
          <StatCard
            title="Revoked"
            value={stats.revoked}
            icon={<Ban />}
            color="red"
          />
        </div>
      </div>

      {/* CUSTOMERS TABLE */}
      <div className="card">
        <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '16px' }}>
          Customers
        </h2>

        {loading ? (
          <div style={{ padding: '40px 0', textAlign: 'center' }}>
            Loading…
          </div>
        ) : (
          <div className="table-container">
            <table style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th className="table-header">Company</th>
                  <th className="table-header">Product Key</th>
                  <th className="table-header">Machine Limit</th>
                  <th className="table-header">Valid Days</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Created</th>
                </tr>
              </thead>

              <tbody>
                {filteredCustomers.map((c) => (
                  <tr key={c.id} className="table-row">
                    <td className="table-cell">{c.company_name}</td>

                    <td className="table-cell">
                      <code
                        style={{
                          fontSize: '12px',
                          background: 'var(--bg-tertiary)',
                          padding: '4px 8px',
                          borderRadius: '4px',
                        }}
                      >
                        {c.product_key}
                      </code>
                    </td>

                    <td className="table-cell">{c.machine_limit}</td>
                    <td className="table-cell">{c.valid_days} days</td>

                    <td className="table-cell">
                      <span
                        className="badge"
                        style={{
                          backgroundColor:
                            c.status === 'Active'
                              ? 'rgba(16,185,129,0.15)'
                              : c.status === 'Revoked'
                              ? 'rgba(239,68,68,0.15)'
                              : 'rgba(156,163,175,0.15)',
                          color:
                            c.status === 'Active'
                              ? '#059669'
                              : c.status === 'Revoked'
                              ? '#dc2626'
                              : '#6b7280',
                        }}
                      >
                        {c.status}
                      </span>
                    </td>

                    <td className="table-cell">
                      {formatDate(c.created_at)}
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