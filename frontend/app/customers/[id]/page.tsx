'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getCustomer, revokeMachine, upgradeCertificate, deleteMachine } from '@/lib/api';
import { formatDate, formatDateTime, copyToClipboard } from '@/lib/utils';
import {
  ChevronRight, Copy, Check, Monitor, AlertTriangle, Ban,
  RefreshCw, FileText, X, Trash2
} from 'lucide-react';

interface Machine {
  id: string;
  customer_id: string;
  machine_id: string;
  fingerprint: string;
  hostname: string;
  os_info: string | null;
  app_version: string | null;
  ip_address: string | null;
  status: string;
  last_seen: string | null;
  created_at: string;
  certificate: any;
}

interface Customer {
  id: string;
  company_name: string;
  product_key: string;
  machine_limit: number;
  valid_days: number;
  revoked: boolean;
  created_at: string;
}

export default function CustomerDetailPage() {
  const params = useParams();
  const customerId = params.id as string;

  const [customer, setCustomer] = useState<Customer | null>(null);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [copiedKey, setCopiedKey] = useState(false);

  const [showRevokeModal, setShowRevokeModal] = useState(false);
  const [machineToRevoke, setMachineToRevoke] = useState<Machine | null>(null);
  const [revoking, setRevoking] = useState(false);

  const [showRenewModal, setShowRenewModal] = useState(false);
  const [machineToRenew, setMachineToRenew] = useState<Machine | null>(null);
  const [renewing, setRenewing] = useState(false);
  const [renewForm, setRenewForm] = useState({
    additional_days: 365,
    new_tier: '',
    new_machine_limit: 0,
  });

  const [showCertModal, setShowCertModal] = useState(false);
  const [selectedCert, setSelectedCert] = useState<any>(null);

  const [deletingMachineId, setDeletingMachineId] = useState<string | null>(null);

  useEffect(() => {
    loadCustomer();
  }, [customerId]);

  async function loadCustomer() {
    try {
      const data = await getCustomer(customerId);
      setCustomer(data.customer);
      setMachines(data.machines || []);
    } catch (error) {
      console.error('Failed to load customer:', error);
    } finally {
      setLoading(false);
    }
  }

  function handleCopyKey() {
    if (customer) {
      copyToClipboard(customer.product_key);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  }

  async function handleRevoke() {
    if (!machineToRevoke) return;
    setRevoking(true);
    try {
      await revokeMachine(machineToRevoke.id);
      await loadCustomer();
      setShowRevokeModal(false);
      setMachineToRevoke(null);
    } catch (error) {
      console.error('Failed to revoke machine:', error);
    } finally {
      setRevoking(false);
    }
  }

  async function handleRenew() {
    if (!machineToRenew) return;
    setRenewing(true);
    try {
      await upgradeCertificate({
        machine_fingerprint: machineToRenew.fingerprint,
        additional_days: renewForm.additional_days,
        new_tier: renewForm.new_tier || undefined,
        new_machine_limit: renewForm.new_machine_limit || undefined,
      });
      await loadCustomer();
      setShowRenewModal(false);
      setMachineToRenew(null);
    } catch (error) {
      console.error('Failed to renew:', error);
    } finally {
      setRenewing(false);
    }
  }

  async function handleDeleteMachine(machineId: string) {
    if (!confirm('Permanently delete this machine? This action cannot be undone.')) {
      return;
    }

    setDeletingMachineId(machineId);
    try {
      await deleteMachine(machineId);
      await loadCustomer();
    } catch (error) {
      console.error('Failed to delete machine:', error);
      alert('Failed to delete machine');
    } finally {
      setDeletingMachineId(null);
    }
  }

  function openRevokeModal(machine: Machine) {
    setMachineToRevoke(machine);
    setShowRevokeModal(true);
  }

  function openRenewModal(machine: Machine) {
    setMachineToRenew(machine);
    const cert = typeof machine.certificate === 'string' ? JSON.parse(machine.certificate) : machine.certificate;
    setRenewForm({
      additional_days: 365,
      new_tier: cert?.tier || '',
      new_machine_limit: customer?.machine_limit || 3,
    });
    setShowRenewModal(true);
  }

  function openCertModal(machine: Machine) {
    const cert = typeof machine.certificate === 'string' ? JSON.parse(machine.certificate) : machine.certificate;
    setSelectedCert(cert);
    setShowCertModal(true);
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ width: '40px', height: '40px', border: '2px solid #6366f1', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '64px 0' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '8px' }}>Customer Not Found</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>The customer you're looking for doesn't exist.</p>
        <Link href="/customers" className="btn btn-primary">
          Back to Customers
        </Link>
      </div>
    );
  }

  const getMachineStatusInfo = (machine: Machine) => {
    if (machine.status === 'revoked') {
      return { label: 'Revoked', bg: 'rgba(239, 68, 68, 0.2)', color: '#ef4444' };
    }

    let isExpired = false;

    try {
      const cert = typeof machine.certificate === 'string'
        ? JSON.parse(machine.certificate)
        : machine.certificate;

      const validUntilStr = cert?.validity?.valid_until;

      if (!validUntilStr) {
        return { label: 'Active', bg: 'rgba(16, 185, 129, 0.2)', color: '#10b981' };
      }

      const normalized = validUntilStr.replace('+00:00', 'Z');
      const validUntil = new Date(normalized);

      isExpired = Date.now() > validUntil.getTime();

      if (isExpired && machine.status === 'active') {
        fetch(`/api/v1/admin/machines/${machine.id}/mark-expired`, {
          method: 'POST',
        }).catch(() => {});
      }
    } catch (e) {}

    if (isExpired) {
      return { label: 'Expired', bg: 'rgba(239, 68, 68, 0.2)', color: '#ef4444' };
    }

    return { label: 'Active', bg: 'rgba(16, 185, 129, 0.2)', color: '#10b981' };
  };

  const activeCount = machines.filter(m => {
    if (m.status === 'revoked') return false;
    const info = getMachineStatusInfo(m);
    return info.label === 'Active';
  }).length;

  const totalActivated = machines.length;

  const getCustomerStatusInfo = () => {
    if (customer.revoked) {
      return { label: 'Revoked', bg: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: 'rgba(239, 68, 68, 0.35)' };
    }

    const hasRevokedMachine = machines.some(m => m.status === 'revoked');
    if (hasRevokedMachine) {
      return { label: 'Revoked', bg: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: 'rgba(239, 68, 68, 0.35)' };
    }

    if (totalActivated === 0) {
      return { label: 'No Activations', bg: 'rgba(234, 179, 8, 0.18)', color: '#ca8a04', border: 'rgba(234, 179, 8, 0.35)' };
    }

    if (activeCount === 0) {
      return { label: 'All Expired', bg: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: 'rgba(239, 68, 68, 0.35)' };
    }

    return { label: 'Active', bg: 'rgba(16, 185, 129, 0.2)', color: '#10b981', border: 'rgba(16, 185, 129, 0.35)' };
  };

  const statusInfo = getCustomerStatusInfo();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
        <Link href="/customers" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>
          Customers
        </Link>
        <ChevronRight size={16} color="var(--text-muted)" />
        <span style={{ color: 'var(--text-primary)' }}>{customer.company_name}</span>
      </div>

      {/* Header Card */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '24px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
                {customer.company_name}
              </h1>
              <span className="badge" style={{
                backgroundColor: statusInfo.bg,
                color: statusInfo.color,
                borderColor: statusInfo.border,
                padding: '6px 12px',
                fontSize: '13px',
                fontWeight: 500,
              }}>
                {statusInfo.label}
              </span>
            </div>
            <p style={{ color: 'var(--text-muted)' }}>
              Created on {formatDate(customer.created_at)}
            </p>
          </div>
        </div>

        {/* Info Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '24px' }}>
          <div style={{ backgroundColor: 'var(--bg-tertiary)', borderRadius: '12px', padding: '16px' }}>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Product Key</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <code style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '14px', color: '#6366f1', fontWeight: 500 }}>
                {customer.product_key}
              </code>
              <button onClick={handleCopyKey} style={{ padding: '6px', background: 'none', border: 'none', cursor: 'pointer', borderRadius: '6px' }}>
                {copiedKey ? <Check size={16} color="#10b981" /> : <Copy size={16} color="var(--text-muted)" />}
              </button>
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-tertiary)', borderRadius: '12px', padding: '16px' }}>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Machine Usage</p>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
              <span style={{ fontSize: '28px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
                {totalActivated}
              </span>
              <span style={{ fontSize: '20px', color: 'var(--text-muted)' }}>
                / {customer.machine_limit}
              </span>
              <span style={{ fontSize: '14px', color: 'var(--text-muted)', marginLeft: '8px' }}>
                used
              </span>
            </div>
            <div style={{ marginTop: '10px', height: '8px', backgroundColor: 'var(--bg-elevated)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                backgroundColor: totalActivated >= customer.machine_limit ? '#f97316' : '#10b981',
                width: `${Math.min((totalActivated / customer.machine_limit) * 100, 100)}%`,
                transition: 'width 0.4s ease'
              }} />
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
              {activeCount} currently active
            </p>
          </div>

          <div style={{ backgroundColor: 'var(--bg-tertiary)', borderRadius: '12px', padding: '16px' }}>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>License Duration</p>
            <p style={{ fontSize: '28px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
              {customer.valid_days} <span style={{ fontSize: '16px', fontWeight: 'normal', color: 'var(--text-muted)' }}>days</span>
            </p>
          </div>

          <div style={{ backgroundColor: 'var(--bg-tertiary)', borderRadius: '12px', padding: '16px' }}>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Customer ID</p>
            <code style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '14px', color: 'var(--text-secondary)' }}>
              {customer.id}
            </code>
          </div>
        </div>
      </div>

      {/* Activated Machines */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)' }}>
            Activated Machines
          </h2>
          <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
            {totalActivated} used • {activeCount} active
          </span>
        </div>

        {machines.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 0' }}>
            <div style={{ width: '64px', height: '64px', margin: '0 auto 16px', borderRadius: '50%', backgroundColor: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Monitor size={32} color="var(--text-muted)" />
            </div>
            <p style={{ color: 'var(--text-muted)' }}>No machines activated yet</p>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Customer needs to activate using the product key
            </p>
          </div>
        ) : (
          <div className="table-container">
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--bg-tertiary)' }}>
                  <th className="table-header">Hostname</th>
                  <th className="table-header">Fingerprint</th>
                  <th className="table-header">OS</th>
                  <th className="table-header">Version</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Last Seen</th>
                  <th className="table-header">Activated</th>
                  <th className="table-header">Actions</th>
                </tr>
              </thead>
              <tbody>
                {machines.map((machine, index) => {
                  const cert = typeof machine.certificate === 'string' ? JSON.parse(machine.certificate) : machine.certificate;
                  const tier = cert?.tier || 'basic';
                  const statusInfo = getMachineStatusInfo(machine);

                  return (
                    <tr key={machine.id} className="table-row" style={{ animationDelay: `${index * 0.03}s` }}>
                      <td className="table-cell">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div style={{ width: '32px', height: '32px', borderRadius: '8px', backgroundColor: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Monitor size={16} color="var(--text-muted)" />
                          </div>
                          <div>
                            <p style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{machine.hostname}</p>
                            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{machine.ip_address || 'No IP'}</p>
                          </div>
                        </div>
                      </td>
                      <td className="table-cell">
                        <code style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {machine.fingerprint?.slice(0, 16)}...
                        </code>
                      </td>
                      <td className="table-cell" style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                        {machine.os_info || '-'}
                      </td>
                      <td className="table-cell" style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                        {machine.app_version || '-'}
                      </td>
                      <td className="table-cell">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <span className="badge" style={{
                            backgroundColor: statusInfo.bg,
                            color: statusInfo.color,
                            padding: '6px 12px',
                            fontSize: '13px',
                            fontWeight: 500,
                          }}>
                            {statusInfo.label}
                          </span>
                          <span className="badge" style={{
                            backgroundColor: tier === 'enterprise' ? 'rgba(16, 185, 129, 0.2)' : tier === 'pro' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                            color: tier === 'enterprise' ? '#10b981' : tier === 'pro' ? '#a78bfa' : '#38bdf8',
                            fontSize: '10px',
                          }}>
                            {tier.toUpperCase()}
                          </span>
                        </div>
                      </td>
                      <td className="table-cell" style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
                        {machine.last_seen ? formatDateTime(machine.last_seen) : 'Never'}
                      </td>
                      <td className="table-cell" style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
                        {formatDate(machine.created_at)}
                      </td>
                      <td className="table-cell">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <button onClick={() => openCertModal(machine)} style={{ padding: '8px', background: 'none', border: 'none', cursor: 'pointer', borderRadius: '8px' }} title="View Certificate">
                            <FileText size={16} color="var(--text-muted)" />
                          </button>
                          {statusInfo.label === 'Active' && (
                            <>
                              <button onClick={() => openRenewModal(machine)} style={{ padding: '8px', background: 'none', border: 'none', cursor: 'pointer', borderRadius: '8px' }} title="Renew/Upgrade">
                                <RefreshCw size={16} color="#10b981" />
                              </button>
                              <button onClick={() => openRevokeModal(machine)} style={{ padding: '8px', background: 'none', border: 'none', cursor: 'pointer', borderRadius: '8px' }} title="Revoke">
                                <Ban size={16} color="#ef4444" />
                              </button>
                            </>
                          )}
                          {(statusInfo.label === 'Revoked' || statusInfo.label === 'Expired') && (
                            <button
                              onClick={() => handleDeleteMachine(machine.id)}
                              disabled={deletingMachineId === machine.id}
                              style={{
                                padding: '8px',
                                background: 'none',
                                border: 'none',
                                cursor: deletingMachineId === machine.id ? 'not-allowed' : 'pointer',
                                borderRadius: '8px',
                                opacity: deletingMachineId === machine.id ? 0.5 : 1
                              }}
                              title="Delete Permanently"
                            >
                              <Trash2 size={16} color="#ef4444" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Revoke Modal */}
      {showRevokeModal && machineToRevoke && (
        <div className="modal-overlay" onClick={() => setShowRevokeModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ width: '64px', height: '64px', margin: '0 auto 16px', borderRadius: '50%', backgroundColor: 'rgba(239, 68, 68, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <AlertTriangle size={32} color="#ef4444" />
              </div>
              <h3 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '8px' }}>
                Revoke Machine?
              </h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '8px' }}>
                Are you sure you want to revoke this machine?
              </p>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px' }}>
                <strong>{machineToRevoke.hostname}</strong> will no longer be able to use the license.
              </p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button onClick={() => setShowRevokeModal(false)} className="btn btn-secondary" style={{ flex: 1 }}>
                  Cancel
                </button>
                <button onClick={handleRevoke} disabled={revoking} className="btn btn-danger" style={{ flex: 1 }}>
                  {revoking ? 'Revoking...' : 'Revoke Machine'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Renew Modal */}
      {showRenewModal && machineToRenew && (
        <div className="modal-overlay" onClick={() => setShowRenewModal(false)}>
          <div className="modal-content" style={{ maxWidth: '480px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
              <h2 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)' }}>
                Renew / Upgrade License
              </h2>
              <button onClick={() => setShowRenewModal(false)} style={{ padding: '8px', background: 'none', border: 'none', cursor: 'pointer', borderRadius: '8px' }}>
                <X size={20} color="var(--text-muted)" />
              </button>
            </div>

            <div style={{ backgroundColor: 'var(--bg-tertiary)', borderRadius: '12px', padding: '16px', marginBottom: '24px' }}>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>Machine</p>
              <p style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{machineToRenew.hostname}</p>
            </div>

            <form onSubmit={(e) => { e.preventDefault(); handleRenew(); }} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label className="form-label">Extend by (days)</label>
                <input
                  type="number"
                  min="1"
                  max="3650"
                  value={renewForm.additional_days}
                  onChange={(e) => setRenewForm({ ...renewForm, additional_days: parseInt(e.target.value) })}
                  className="form-input"
                />
              </div>

              <div>
                <label className="form-label">Upgrade Tier (optional)</label>
                <select
                  value={renewForm.new_tier}
                  onChange={(e) => setRenewForm({ ...renewForm, new_tier: e.target.value })}
                  className="form-select"
                >
                  <option value="">Keep current tier</option>
                  <option value="trial">Trial</option>
                  <option value="basic">Basic</option>
                  <option value="pro">Pro</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>

              <div>
                <label className="form-label">New Machine Limit (optional)</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={renewForm.new_machine_limit}
                  onChange={(e) => setRenewForm({ ...renewForm, new_machine_limit: parseInt(e.target.value) })}
                  className="form-input"
                />
              </div>

              <div style={{ display: 'flex', gap: '12px', paddingTop: '16px' }}>
                <button type="button" onClick={() => setShowRenewModal(false)} className="btn btn-secondary" style={{ flex: 1 }}>
                  Cancel
                </button>
                <button type="submit" disabled={renewing} className="btn btn-primary" style={{ flex: 1 }}>
                  {renewing ? 'Processing...' : 'Renew License'}
                </button>
              </div>
            </form>

            <p style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '16px' }}>
              A new certificate will be generated with updated validity
            </p>
          </div>
        </div>
      )}

      {/* Certificate Viewer Modal */}
      {showCertModal && selectedCert && (
        <div className="modal-overlay" onClick={() => setShowCertModal(false)}>
          <div className="modal-content" style={{ maxWidth: '640px', maxHeight: '80vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
              <h2 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)' }}>
                Certificate Details
              </h2>
              <button onClick={() => setShowCertModal(false)} style={{ padding: '8px', background: 'none', border: 'none', cursor: 'pointer', borderRadius: '8px' }}>
                <X size={20} color="var(--text-muted)" />
              </button>
            </div>

            <pre style={{ backgroundColor: 'var(--bg-tertiary)', borderRadius: '12px', padding: '16px', overflow: 'auto', fontSize: '12px', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-secondary)' }}>
              {JSON.stringify(selectedCert, null, 2)}
            </pre>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button onClick={() => copyToClipboard(JSON.stringify(selectedCert, null, 2))} className="btn btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Copy size={16} /> Copy JSON
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}