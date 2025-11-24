'use client';

import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: LucideIcon;
  color: 'blue' | 'green' | 'yellow' | 'red' | 'purple';
}

const colorClasses = {
  blue: {
    bg: 'bg-gradient-to-br from-blue-500 to-blue-600',
    iconBg: 'bg-blue-100',
    iconColor: 'text-blue-600',
    text: 'text-blue-600',
  },
  green: {
    bg: 'bg-gradient-to-br from-green-500 to-green-600',
    iconBg: 'bg-green-100',
    iconColor: 'text-green-600',
    text: 'text-green-600',
  },
  yellow: {
    bg: 'bg-gradient-to-br from-yellow-500 to-yellow-600',
    iconBg: 'bg-yellow-100',
    iconColor: 'text-yellow-600',
    text: 'text-yellow-600',
  },
  red: {
    bg: 'bg-gradient-to-br from-red-500 to-red-600',
    iconBg: 'bg-red-100',
    iconColor: 'text-red-600',
    text: 'text-red-600',
  },
  purple: {
    bg: 'bg-gradient-to-br from-purple-500 to-purple-600',
    iconBg: 'bg-purple-100',
    iconColor: 'text-purple-600',
    text: 'text-purple-600',
  },
};

export default function StatCard({
  title,
  value,
  change,
  changeType = 'neutral',
  icon: Icon,
  color,
}: StatCardProps) {
  const colors = colorClasses[color];
  
  return (
    <div className="group relative bg-white rounded-2xl shadow-lg border border-gray-100 p-6 hover:shadow-2xl transition-all duration-300 overflow-hidden">
      {/* Gradient accent bar */}
      <div className={`absolute top-0 left-0 right-0 h-1 ${colors.bg}`}></div>
      
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500 mb-2 uppercase tracking-wide">{title}</p>
          <p className="text-4xl font-bold text-gray-900 mb-2">{value}</p>
          {change && (
            <p
              className={`text-sm font-semibold ${
                changeType === 'positive'
                  ? 'text-green-600'
                  : changeType === 'negative'
                  ? 'text-red-600'
                  : 'text-gray-500'
              }`}
            >
              {change}
            </p>
          )}
        </div>
        <div className={`p-4 rounded-xl ${colors.iconBg} group-hover:scale-110 transition-transform duration-300`}>
          <Icon className={`w-7 h-7 ${colors.iconColor}`} />
        </div>
      </div>
      
      {/* Decorative background element */}
      <div className={`absolute -bottom-4 -right-4 w-24 h-24 ${colors.bg} opacity-5 rounded-full blur-2xl`}></div>
    </div>
  );
}