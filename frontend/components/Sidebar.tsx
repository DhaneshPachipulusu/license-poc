'use client';

import React from 'react';
import { useRouter, usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Users,
  FileText,
  LogOut,
  ChevronLeft,
} from 'lucide-react';
import { logout } from '@/app/actions';

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
  { id: 'customers', label: 'Customers', icon: Users, href: '/customers' },
  { id: 'subscriptions', label: 'Subscriptions', icon: FileText, href: '/subscriptions' },
  { id: 'certificates', label: 'Certificates', icon: FileText, href: '/certificates/create' },
];

export default function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();

  const [dropdownOpen, setDropdownOpen] = React.useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = React.useState(false);

  const avatarRef = React.useRef<HTMLButtonElement>(null);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!dropdownOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (
        !avatarRef.current?.contains(e.target as Node) &&
        !dropdownRef.current?.contains(e.target as Node)
      ) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [dropdownOpen]);

  const isActive = (href: string) => {
    if (href === '/dashboard') return pathname === '/dashboard';
    return pathname.startsWith(href);
  };

  // This calls the server action → securely deletes token + redirects
  const handleLogout = async () => {
    setDropdownOpen(false);
    await logout(); // This will delete cookies and redirect to /login
  };


  return (
    <>
      {/* Mobile Sidebar */}
      {mobileSidebarOpen && (
        <>
          <div className="fixed inset-0 bg-black/30 z-50" onClick={() => setMobileSidebarOpen(false)} />
          <div className="fixed left-0 top-0 h-full w-64 bg-background border-r border-border shadow-xl z-50 flex flex-col">
            <div className="h-16 flex items-center justify-between px-4 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white shadow flex items-center justify-center">
                  <img src="/X_Light_Mode.svg" alt="Logo" className="w-7 h-7" />
                </div>
                <div>
                  <h1 className="font-bold text-lg">License Control</h1>
                  <p className="text-xs text-muted-foreground">Admin Panel</p>
                </div>
              </div>
              <button onClick={() => setMobileSidebarOpen(false)} className="p-2 rounded hover:bg-muted">
                <ChevronLeft className="w-5 h-5" />
              </button>
            </div>

            <nav className="flex-1 p-4">
              {menuItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      router.push(item.href);
                      setMobileSidebarOpen(false);
                    }}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors ${
                      active ? 'text-indigo-600' : 'hover:bg-muted'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{item.label}</span>
                  </button>
                );
              })}
            </nav>

            <div className="border-t border-border p-4">
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-red-50 text-red-600 font-medium transition-colors"
              >
                <LogOut className="w-5 h-5" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </>
      )}

      {/* Desktop Compact Sidebar */}
      <div className="fixed left-0 top-0 h-screen w-20 bg-background border-r border-border flex flex-col items-center py-6 z-40">
        {/* Logo */}
        <div className="mb-10">
          <div className="w-10 h-10 rounded-xl bg-white shadow flex items-center justify-center">
            <img src="/X_Light_Mode.svg" alt="Logo" className="w-7 h-7" />
          </div>
        </div>

        {/* Menu Items */}
        <nav className="flex-1 flex flex-col items-center gap-6">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <button
                key={item.id}
                onClick={() => router.push(item.href)}
                className="group relative flex flex-col items-center gap-2 px-3 py-3 rounded-xl transition-all hover:bg-muted"
              >
                <Icon className={`w-6 h-6 ${active ? 'text-indigo-600' : 'text-muted-foreground'}`} />
                <span className={`text-xs font-medium ${active ? 'text-indigo-600' : 'text-muted-foreground'}`}>
                  {item.id === 'certificates' ? 'Certificates' : item.label.split('(')[0].trim()}
                </span>

                {/* Tooltip */}
                <div className="absolute left-full ml-3 px-3 py-2 bg-gray-900 text-white text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                  {item.label}
                </div>
              </button>
            );
          })}
        </nav>

        {/* Avatar → Only Logout Dropdown */}
        <div className="relative mt-auto pb-4">
          <button
            ref={avatarRef}
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-600 font-bold text-lg hover:bg-indigo-500/20 transition-colors"
          >
            A
          </button>

          {dropdownOpen && (
            <div
              ref={dropdownRef}
              className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-40 bg-white rounded-2xl shadow-2xl border border-border overflow-hidden"
            >
              <button
                onClick={handleLogout}
                className="w-full flex items-center justify-center gap-2 px-4 py-4 hover:bg-red-50 text-red-600 font-medium transition-colors"
              >
                <LogOut className="w-5 h-5" />
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}