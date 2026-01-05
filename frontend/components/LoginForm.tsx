"use client";

import { useState, FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function Lockup() {
  return (
    <div className="flex flex-col items-center gap-4">
      <div className="w-14 h-14 rounded-2xl bg-white shadow-[0_10px_30px_rgba(0,0,0,0.08)] flex items-center justify-center border border-gray-100">
        <svg aria-hidden className="w-7 h-7 text-gray-900" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <rect x="5" y="9" width="14" height="10" rx="2" ry="2" />
          <path d="M9 9V6a3 3 0 0 1 6 0v3" />
        </svg>
      </div>
      <div className="text-center">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900">POC Licence</h1>
        <p className="text-sm text-gray-600 mt-1">Sign in to access your portal</p>
      </div>
    </div>
  );
}

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const formData = new FormData(e.currentTarget);
    const username = formData.get('username')?.toString() || '';
    const password = formData.get('password')?.toString() || '';

    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Critical: sends/receives HttpOnly cookies
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.detail || 'Invalid credentials');
        setLoading(false);
        return;
      }

      console.log('📦 Login response:', data);
      console.log('👤 User:', data.user);

      // JWT is automatically stored in HttpOnly cookie via Set-Cookie header
      // Browser will send it automatically on all subsequent requests
      // No need for localStorage - it's secure and stateless
      router.push('/dashboard');
    } catch (err) {
      console.error('❌ Login error:', err);
      setError('Login failed. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f7fb] flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-xl bg-white rounded-[22px] shadow-[0_20px_80px_rgba(0,0,0,0.08)] p-8 md:p-10 border border-gray-100">
        <div className="flex items-center justify-center mb-8">
          <Lockup />
        </div>
        <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-gray-900" htmlFor="username">
              Username
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
                <svg aria-hidden className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <circle cx="12" cy="7" r="3" />
                  <path d="M6 20c0-3 2-5 6-5s6 2 6 5" />
                </svg>
              </span>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                required
                className="w-full rounded-xl border border-gray-200 bg-white px-11 py-3 text-gray-900 placeholder:text-gray-400 focus:border-gray-400 focus:ring-0 outline-none"
                placeholder="Enter your username"
              />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-gray-900" htmlFor="password">
              Password
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
                <svg aria-hidden className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <rect x="5" y="10" width="14" height="10" rx="2" />
                  <path d="M9 10V7a3 3 0 0 1 6 0v3" />
                </svg>
              </span>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="w-full rounded-xl border border-gray-200 bg-white px-11 py-3 text-gray-900 placeholder:text-gray-400 focus:border-gray-400 focus:ring-0 outline-none"
                placeholder="Enter your password"
              />
            </div>
          </div>
          {error ? (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          ) : null}
          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex justify-center items-center gap-2 rounded-xl bg-black text-white font-semibold px-4 py-3 shadow-[0_12px_24px_rgba(0,0,0,0.15)] hover:bg-gray-900 disabled:opacity-60 disabled:cursor-not-allowed transition"
          >
            {loading ? "Signing in..." : "Sign In"}
            <span aria-hidden>→</span>
          </button>
        </form>
      </div>
    </div>
  );
}
