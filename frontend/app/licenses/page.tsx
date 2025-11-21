'use client';

import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { licenseApi } from '@/lib/api';
import { Key, Search } from 'lucide-react';
import { formatDateShort, getLicenseStatus } from '@/lib/utils';
import './globals.css'
export default function LicensesPage() {
  const [licenses, setLicenses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadLicenses();
  }, []);

  const loadLicenses = async () => {
    try {
      setLoading(true);
      const data = await licenseApi.getAllLicenses();
      setLicenses(data);
    } catch (err) {
      console.error('Load license error:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = licenses.filter((lic) =>
    lic.license_id.toLowerCase().includes(search.toLowerCase()) ||
    lic.customer.toLowerCase().includes(search.toLowerCase()) ||
    lic.machine_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 ml-64 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Licenses</h1>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-2.5 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="Search licenses..."
            className="input pl-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin h-10 w-10 rounded-full border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <div className="bg-white border rounded-xl shadow-sm overflow-hidden">
            <table className="table">
              <thead>
                <tr>
                  <th>License ID</th>
                  <th>Customer</th>
                  <th>Machine</th>
                  <th>Valid Until</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {filtered.map((lic) => {
                  const status = getLicenseStatus(lic);
                  return (
                    <tr key={lic.license_id}>
                      <td className="font-mono text-blue-600">
                        {lic.license_id}
                      </td>
                      <td>{lic.customer}</td>
                      <td className="font-mono text-gray-500">
                        {lic.machine_id.slice(0, 16)}...
                      </td>
                      <td>{formatDateShort(lic.license_json.valid_till)}</td>
                      <td>
                        <span className={`status-badge status-${status.status}`}>
                          {status.label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
