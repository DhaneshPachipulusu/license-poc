'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { authMe } from '@/lib/api';

// Auth context to share auth state across app
const AuthContext = createContext<{
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
} | null>(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthGuard');
  }
  return context;
}

export default function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Skip auth check on login page
    if (pathname === '/login') {
      setIsLoading(false);
      setIsAuthenticated(false);
      return;
    }

    // Check if valid JWT exists in HttpOnly cookie by calling /auth/me
    // Browser automatically includes the cookie on this request
    let cancelled = false;
    async function check() {
      try {
        console.log('🔐 Validating JWT from HttpOnly cookie...');
        await authMe(); // This call includes the HttpOnly cookie automatically
        console.log('✅ Authentication confirmed via HttpOnly cookie');
        if (!cancelled) {
          setIsAuthenticated(true);
          setError(null);
          setIsLoading(false);
        }
      } catch (err) {
        console.error('❌ Authentication failed:', err);
        // Cookie either missing or JWT invalid/expired
        // No need to manually clear - cookie will auto-expire or be cleared by server
        if (!cancelled) {
          setIsAuthenticated(false);
          setError('Session expired. Please login again.');
          setIsLoading(false);
          router.replace('/login');
        }
      }
    }
    check();
    return () => {
      cancelled = true;
    };
  }, [router, pathname]);

  // Show spinner while checking auth
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // On login page, skip auth rendering
  if (pathname === '/login') {
    return <>{children}</>;
  }

  // If auth fails, don't render children
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-red-600">Redirecting to login...</p>
      </div>
    );
  }

  // Render children only if authenticated
  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, error }}>
      {children}
    </AuthContext.Provider>
  );
}
