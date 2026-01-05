'use client';

import { useEffect, useState } from 'react';
import { Search, Users } from 'lucide-react';

interface Resource {
  used: number;
  limit: number;
}

interface Subscription {
  id: string;
  client: string;
  orgs: Resource;
  spaces: Resource;
  users: Resource;
  tokens: Resource;
}

export default function SubscriptionsPage() {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    async function fetchSubscriptions() {
      try {
        const res = await fetch('/subscriptions.json');
        const data: Subscription[] = await res.json();
        setSubscriptions(data);
      } catch (error) {
        console.error('Failed to load subscriptions:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchSubscriptions();
  }, []);

  const filteredSubscriptions = subscriptions.filter((sub) =>
    sub.client.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatUsedLimit = (resource: Resource) => `${resource.used}/${resource.limit}`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '30px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
            Subscriptions
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
            Client resource usage overview
          </p>
        </div>
      </div>

      {/* Search */}
      <div style={{ position: 'relative' }}>
        <Search size={20} color="var(--text-muted)" style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)' }} />
        <input
          type="text"
          placeholder="Search clients..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="form-input"
          style={{ paddingLeft: '48px' }}
        />
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '80px 0' }}>
          <div style={{ width: '40px', height: '40px', border: '2px solid #6366f1', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        </div>
      ) : filteredSubscriptions.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '64px 0' }}>
          <div style={{ width: '80px', height: '80px', margin: '0 auto 24px', borderRadius: '50%', backgroundColor: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Users size={40} color="var(--text-muted)" />
          </div>
          <h3 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '8px' }}>
            {searchTerm ? 'No subscriptions found' : 'No subscriptions yet'}
          </h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>
            {searchTerm ? 'Try a different search term' : 'Subscription data will appear here'}
          </p>
        </div>
      ) : (
        <div className="table-container">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--bg-tertiary)' }}>
                <th className="table-header">Client</th>
                <th className="table-header">No of Orgs</th>
                <th className="table-header">No of Spaces</th>
                <th className="table-header">Users</th>
                <th className="table-header">Token Count</th>
              </tr>
            </thead>
            <tbody>
              {filteredSubscriptions.map((sub, index) => (
                <tr key={sub.id} className="table-row" style={{ animationDelay: `${index * 0.03}s` }}>
                  <td className="table-cell">
                    <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                      {sub.client}
                    </span>
                  </td>
                  <td className="table-cell" style={{ color: 'var(--text-secondary)' }}>
                    {formatUsedLimit(sub.orgs)}
                  </td>
                  <td className="table-cell" style={{ color: 'var(--text-secondary)' }}>
                    {formatUsedLimit(sub.spaces)}
                  </td>
                  <td className="table-cell" style={{ color: 'var(--text-secondary)' }}>
                    {formatUsedLimit(sub.users)}
                  </td>
                  <td className="table-cell" style={{ color: 'var(--text-secondary)' }}>
                    {formatUsedLimit(sub.tokens)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}