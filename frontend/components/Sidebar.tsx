'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Users, 
  Key, 
  BarChart3, 
  Settings, 
  Shield,
  FileText
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Licenses', href: '/licenses', icon: Key },
  { name: 'Customers', href: '/customers', icon: Users },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Reports', href: '/reports', icon: FileText },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 bg-gradient-to-b from-gray-900 via-gray-900 to-gray-800 min-h-screen fixed left-0 top-0 text-white shadow-2xl z-50">
      {/* Header */}
      <div className="p-6 border-b border-gray-700/50 bg-gradient-to-r from-gray-900 to-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">License Server</h1>
            <p className="text-xs text-gray-400">Admin Dashboard</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-2 mt-2">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`
                group flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 relative
                ${isActive 
                  ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-500/30' 
                  : 'text-gray-300 hover:bg-gray-800/50 hover:text-white hover:translate-x-1'
                }
              `}
            >
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-white rounded-r-full"></div>
              )}
              <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-gray-400 group-hover:text-white'} transition-colors`} />
              <span className={`font-medium ${isActive ? 'text-white' : 'text-gray-300'}`}>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-700/50 bg-gray-900/50 backdrop-blur-sm">
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-gray-800/50 hover:bg-gray-800 transition-colors cursor-pointer">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center shadow-md">
            <span className="text-sm font-bold text-white">A</span>
          </div>
          <div className="flex-1">
            <p className="text-sm font-semibold text-white">Admin User</p>
            <p className="text-xs text-gray-400">admin@company.com</p>
          </div>
        </div>
      </div>
    </div>
  );
}