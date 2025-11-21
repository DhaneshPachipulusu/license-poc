'use client';

import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { licenseApi } from '@/lib/api';
import { Monitor, ChevronRight, Users } from 'lucide-react';

export default function CustomersPage() {
  const [customers, setCustomers] = useState<any[]>([]);
  const [expandedCustomer, setExpandedCustomer] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadCustomers();
  }, []);

  const loadCustomers = async () => {
    try {
      setLoading(true);

      const list = await licenseApi.getAllCustomers();

      const details = await Promise.all(
        list.map((c: any) => licenseApi.getCustomerDetails(c.id))
      );

      setCustomers(details);
    } catch (err) {
      console.error('Customer load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = customers.filter((c) =>
    c.customer.company_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 ml-64 p-8">
        <h1 className="text-2xl font-bold mb-2 text-gray-900">Customers</h1>
        <p className="text-gray-600 mb-6">View customers and their machines</p>

        {/* Search */}
        <input
          type="text"
          placeholder="Search customers..."
          className="input w-full mb-6"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin h-12 w-12 rounded-full border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map((c) => {
              const cust = c.customer;
              const machines = c.machines || [];

              return (
                <div key={cust.id} className="bg-white border rounded-xl shadow-sm">
                  {/* Header */}
                  <div
                    className="p-5 flex items-center justify-between cursor-pointer hover:bg-gray-50"
                    onClick={() =>
                      setExpandedCustomer(
                        expandedCustomer === cust.id ? null : cust.id
                      )
                    }
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-lg bg-blue-600 text-white flex items-center justify-center text-lg font-bold">
                        {cust.company_name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <h2 className="text-lg font-semibold text-gray-900">
                          {cust.company_name}
                        </h2>
                        <p className="text-gray-600 text-sm">
                          Machine limit: {cust.machine_limit}
                        </p>
                      </div>
                    </div>

                    <ChevronRight
                      className={`w-5 h-5 text-gray-500 transition-transform ${
                        expandedCustomer === cust.id ? 'rotate-90' : ''
                      }`}
                    />
                  </div>

                  {/* Expanded */}
                  {expandedCustomer === cust.id && (
                    <div className="border-t p-6 bg-gray-50">
                      <h3 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
                        <Monitor className="w-4 h-4" />
                        Machines ({machines.length})
                      </h3>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {machines.map((m: any) => (
                          <div
                            key={m.id}
                            className="p-4 bg-white border rounded-lg shadow-sm"
                          >
                            <p className="font-mono text-xs text-gray-600">
                              {m.fingerprint.slice(0, 20)}...
                            </p>
                            <p className="text-sm text-gray-700">
                              Hostname: {m.hostname}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
