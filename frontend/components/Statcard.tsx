import { withRouter } from "next/router";

interface StatCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: React.ReactNode;
  color: 'indigo' | 'emerald' | 'amber' | 'red';
}

const colorStyles = {
  indigo: {
    bg: 'rgba(79, 70, 229, 0.08)',
    border: 'rgba(79, 70, 229, 0.15)',
    icon: '#6861ceff',
  },
  emerald: {
    bg: 'rgba(16, 185, 129, 0.08)',
    border: 'rgba(255, 255, 255, 0.15)',
    icon: '#059669',
  },
  amber: {
    bg: 'rgba(245, 158, 11, 0.08)',
    border: 'rgba(245, 158, 11, 0.15)',
    icon: '#d97706',
  },
  red: {
    bg: 'rgba(239, 68, 68, 0.08)',
    border: 'rgba(239, 68, 68, 0.15)',
    icon: '#dc2626',
  },
  white: {
    bg: 'rgba(255, 255, 255, 0.08)',
    border: 'rgba(255, 255, 255, 0.15)',
    icon: '#ff0000ff',
  }
};

export default function StatCard({ title, value, subtitle, icon, color }: StatCardProps) {
  const colors = colorStyles[color];

  return (
    <div
      style={{
        padding: '24px',
        borderRadius: '12px',
        backgroundColor: colors.bg,
        border: `1px solid ${colors.border}`,
        transition: 'all 0.2s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px' }}>{title}</p>
          <p style={{ fontSize: '30px', fontWeight: 'bold', color: 'var(--text-primary)' }}>{value}</p>
          {subtitle && (
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>{subtitle}</p>
          )}
        </div>
        <div style={{ 
          padding: '12px', 
          borderRadius: '12px', 
          backgroundColor: colors.bg,
          color: colors.icon,
        }}>
          {icon}
        </div>
      </div>
    </div>
  );
}