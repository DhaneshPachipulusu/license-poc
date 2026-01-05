import { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: number | string;
  icon?: ReactNode;
  active?: boolean;
  onClick?: () => void;
  variant: 'purple' | 'orange' | 'green' | 'yellow' | 'red';
}

const colorStyles: Record<StatCardProps['variant'], {
  bg: string;
  border: string;
  iconBg: string;
  iconColor: string;
  activeBorder?: string;
}> = {
  purple: {
    bg: '#eef2ff',
    border: '#c7d2fe',
    iconBg: '#e0e7ff',
    iconColor: '#6366f1',
    activeBorder: '#818cf8',
  },
  orange: {
    bg: '#fff7ed',
    border: '#fed7aa',
    iconBg: '#ffedd5',
    iconColor: '#f97316',
    activeBorder: '#fb923c',
  },
  green: {
    bg: '#f0fdf4',
    border: '#bbf7d0',
    iconBg: '#dcfce7',
    iconColor: '#22c55e',
    activeBorder: '#4ade80',
  },
  yellow: {
    bg: '#fffbeb',
    border: '#fde68a',
    iconBg: '#fef3c7',
    iconColor: '#f59e0b',
    activeBorder: '#fbbf24',
  },
  red: {
    bg: '#fef2f2',
    border: '#fecaca',
    iconBg: '#fee2e2',
    iconColor: '#ef4444',
    activeBorder: '#f87171',
  },
};

export default function StatCard({
  title,
  value,
  icon,
  active = false,
  onClick,
  variant,
}: StatCardProps) {
  const colors = colorStyles[variant];

  return (
    <div
      onClick={onClick}
      className="relative p-6 rounded-xl border transition-all duration-200 cursor-pointer hover:shadow-md"
      style={{
        backgroundColor: colors.bg,
        borderColor: active ? colors.activeBorder : colors.border,
        borderWidth: active ? '2px' : '1px',
        boxShadow: active ? `0 0 0 4px ${colors.activeBorder}20` : undefined,
      }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted-foreground uppercase tracking-wider mb-1">
            {title}
          </p>
          <p className="text-3xl font-bold text-foreground">
            {value}
          </p>
        </div>
        {icon && (
          <div
            className="p-3 rounded-lg"
            style={{
              backgroundColor: colors.iconBg,
              color: colors.iconColor,
            }}
          >
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}