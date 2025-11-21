'use client';

import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import StatCard from '@/components/StatCard';
import { licenseApi } from '@/lib/api';
import { 
  Key, 
  Users, 
  CheckCircle, 
  AlertCircle,
  TrendingUp,
  Activity
} from 'lucide-react';
import { getLicenseStatus, formatDateShort, isExpiringSoon } from '@/lib/utils';
// import './globals.css'

export default function Dashboard() {
  const [licenses, setLicenses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);

      // Step 1: Get all customers
      const customers = await licenseApi.getAllCustomers();

      // Step 2: Fetch details for each customer
      const details = await Promise.all(
        customers.map((c: any) => licenseApi.getCustomerDetails(c.id))
      );

      // Step 3: Convert machine+certificate to license format
      const converted = details.flatMap((c: any) =>
        c.machines.map((m: any) => ({
          license_id: m.certificate?.certificate_id || m.id,
          customer: c.customer.company_name,
          machine_id: m.fingerprint,
          revoked: m.status === 'revoked',
          created_at: m.certificate?.issued_at || new Date().toISOString(),
          license_json: {
            valid_till: m.certificate?.validity?.valid_until,
            allowed_services: m.certificate?.services
              ? Object.keys(m.certificate.services).filter(
                  (svc) => m.certificate.services[svc]?.enabled
                )
              : [],
          },
        }))
      );

      setLicenses(converted);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const stats = {
    total: licenses.length,
    active: licenses.filter(
      (l) => !l.revoked && !getLicenseStatus(l).status.includes('expired')
    ).length,
    expired: licenses.filter((l) => getLicenseStatus(l).status === 'expired')
      .length,
    revoked: licenses.filter((l) => l.revoked).length,
    expiringSoon: licenses.filter(
      (l) =>
        !l.revoked &&
        isExpiringSoon(l.license_json.valid_till, 7)
    ).length,
    customers: new Set(licenses.map((l) => l.customer)).size,
    machines: new Set(licenses.map((l) => l.machine_id)).size,
  };

  const recentLicenses = licenses
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() -
        new Date(a.created_at).getTime()
    )
    .slice(0, 5);

  if (loading) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 ml-64 p-8">
          <div className="flex items-center justify-center h-screen">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 ml-64">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-8 py-6">
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Overview of your license management system
          </p>
        </div>

        {/* Main Content */}
        <div className="p-8">
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatCard title="Total Licenses" value={stats.total} icon={Key} color="blue" />
            <StatCard title="Active Licenses" value={stats.active} icon={CheckCircle} color="green" />
            <StatCard title="Expiring Soon" value={stats.expiringSoon} icon={AlertCircle} color="yellow" />
            <StatCard title="Total Customers" value={stats.customers} icon={Users} color="purple" />
          </div>

          {/* Additional Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">License Status</h3>
                <Activity className="w-5 h-5 text-gray-400" />
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Active</span>
                  <span className="font-semibold text-green-600">{stats.active}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Expired</span>
                  <span className="font-semibold text-gray-600">{stats.expired}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Revoked</span>
                  <span className="font-semibold text-red-600">{stats.revoked}</span>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">System Health</h3>
              <p className="text-gray-600 text-sm">All systems operational.</p>
              <div className="mt-4">
                <p className="text-sm text-gray-600">Machines: {stats.machines}</p>
              </div>
            </div>

            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-sm p-6 text-white">
              <h3 className="text-lg font-semibold mb-2">Quick Actions</h3>
              <button className="w-full bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg">
                Create License
              </button>
            </div>
          </div>

          {/* Recent Licenses */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Recent Licenses</h2>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">License ID</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Customer</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Machine ID</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Valid Until</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Status</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {recentLicenses.map((l) => {
                    const stat = getLicenseStatus(l);
                    return (
                      <tr key={l.license_id}>
                        <td className="px-6 py-4 font-mono text-blue-600">{l.license_id}</td>
                        <td className="px-6 py-4">{l.customer}</td>
                        <td className="px-6 py-4 font-mono text-gray-500">
                          {l.machine_id.substring(0, 16)}...
                        </td>
                        <td className="px-6 py-4">{formatDateShort(l.license_json.valid_till)}</td>
                        <td className="px-6 py-4">{stat.label}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
