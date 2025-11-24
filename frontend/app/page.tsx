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
    <div className="flex min-h-screen">
      <Sidebar />

      <div className="flex-1 ml-64">
        {/* Header */}
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200/50 px-8 py-6 shadow-sm sticky top-0 z-40">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
                Dashboard
              </h1>
              <p className="text-gray-600 mt-1.5 text-sm">
                Overview of your license management system
              </p>
            </div>
          </div>
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
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-all duration-300">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-gray-900">License Status</h3>
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Activity className="w-5 h-5 text-blue-600" />
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                  <span className="text-sm font-medium text-gray-700">Active</span>
                  <span className="font-bold text-lg text-green-600">{stats.active}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                  <span className="text-sm font-medium text-gray-700">Expired</span>
                  <span className="font-bold text-lg text-gray-600">{stats.expired}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
                  <span className="text-sm font-medium text-gray-700">Revoked</span>
                  <span className="font-bold text-lg text-red-600">{stats.revoked}</span>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-all duration-300">
              <h3 className="text-lg font-bold text-gray-900 mb-4">System Health</h3>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                <p className="text-gray-700 font-medium">All systems operational</p>
              </div>
              <div className="mt-6 p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl">
                <p className="text-sm text-gray-600 mb-1">Total Machines</p>
                <p className="text-2xl font-bold text-gray-900">{stats.machines}</p>
              </div>
            </div>

            <div className="bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-600 rounded-2xl shadow-xl p-6 text-white hover:shadow-2xl transition-all duration-300 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16"></div>
              <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/10 rounded-full -ml-12 -mb-12"></div>
              <div className="relative z-10">
                <h3 className="text-lg font-bold mb-4">Quick Actions</h3>
                <button className="w-full bg-white/20 hover:bg-white/30 backdrop-blur-sm text-white px-4 py-3 rounded-xl font-semibold transition-all duration-200 hover:scale-105 shadow-lg">
                  Create License
                </button>
              </div>
            </div>
          </div>

          {/* Recent Licenses */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="px-6 py-5 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
              <h2 className="text-xl font-bold text-gray-900">Recent Licenses</h2>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50/50">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">License ID</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Customer</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Machine ID</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Valid Until</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {recentLicenses.map((l) => {
                    const stat = getLicenseStatus(l);
                    return (
                      <tr key={l.license_id} className="hover:bg-gray-50/50 transition-colors">
                        <td className="px-6 py-4 font-mono text-sm font-semibold text-blue-600">{l.license_id}</td>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">{l.customer}</td>
                        <td className="px-6 py-4 font-mono text-sm text-gray-600">
                          {l.machine_id.substring(0, 16)}...
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-700">{formatDateShort(l.license_json.valid_till)}</td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-700">
                            {stat.label}
                          </span>
                        </td>
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
