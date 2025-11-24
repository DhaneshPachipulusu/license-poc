'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { LayoutDashboard, Users, FileText, Lock } from 'lucide-react';

const navItems = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Customers',
    href: '/customers',
    icon: Users,
  },
  {
    name: 'Licenses',
    href: '/licenses',
    icon: FileText,
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside style={{
      position: 'fixed',
      left: 0,
      top: 0,
      height: '100vh',
      width: '256px',
      backgroundColor: '#ffffff',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Logo */}
      <div style={{
        padding: '24px',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '12px',
            backgroundColor: '#4f46e5',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 40px rgba(99, 102, 241, 0.15)',
          }}>
            <Lock size={24} color="white" />
          </div>
          <div>
            <h1 style={{ fontWeight: 'bold', color: 'var(--text-primary)', fontSize: '16px' }}>
              License Control
            </h1>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Admin Panel</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: '16px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {navItems.map((item) => {
            const isActive = pathname === item.href || 
              (item.href !== '/dashboard' && pathname.startsWith(item.href));
            const Icon = item.icon;
            
            return (
              <Link
                key={item.name}
                href={item.href}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px 16px',
                  borderRadius: '12px',
                  transition: 'all 0.2s',
                  backgroundColor: isActive ? 'rgba(79, 70, 229, 0.1)' : 'transparent',
                  color: isActive ? '#4f46e5' : '#334155',
                  border: isActive ? '1px solid rgba(79, 70, 229, 0.2)' : '1px solid transparent',
                  textDecoration: 'none',
                }}
              >
                <Icon size={20} />
                <span style={{ fontWeight: 500 }}>{item.name}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div style={{
        padding: '16px',
        borderTop: '1px solid var(--border-subtle)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '12px 16px',
          borderRadius: '12px',
          backgroundColor: 'var(--bg-tertiary)',
        }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: 'rgba(79, 70, 229, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <span style={{ fontSize: '14px', fontWeight: 500, color: '#4f46e5' }}>A</span>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>Admin</p>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>NAINOVATE</p>
          </div>
        </div>
      </div>
    </aside>
  );
}