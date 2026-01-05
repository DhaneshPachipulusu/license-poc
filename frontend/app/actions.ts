// app/actions.ts
'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const SESSION_COOKIE_NAME = 'admin_session';

function parseSessionCookie(headerValue: string | null): string | null {
  if (!headerValue) return null;
  // Support multiple Set-Cookie headers concatenated; find our cookie
  const parts = headerValue.split(/, (?=[^;]+=)/g);
  for (const p of parts) {
    const m = p.match(new RegExp(`${SESSION_COOKIE_NAME}=([^;]+)`));
    if (m) return m[1];
  }
  return null;
}

export async function login(username: string, password: string): Promise<{ success: boolean; user?: unknown; token?: string; error?: string }> {
  try {
    const resp = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
      credentials: 'include',
    });

    const data = await resp.json().catch(() => ({}));
    const sessionCookie = parseSessionCookie(resp.headers.get('set-cookie'));

    if (!resp.ok || !sessionCookie) {
      return { success: false, error: data?.message || 'Invalid credentials' };
    }

    // Set the session cookie in Next.js response
    const jar = cookies();
    jar.set({
      name: SESSION_COOKIE_NAME,
      value: sessionCookie,
      httpOnly: true,
      path: '/',
      sameSite: 'lax',
      // Optional: add secure: true in production
      // secure: process.env.NODE_ENV === 'production',
    });

    return { success: true, user: data?.user, token: sessionCookie };
  } catch (error) {
    console.error('login error', error);
    return { success: false, error: 'Login failed' };
  }
}

export async function getOrganizations(locale: string) {
  // Placeholder
  return [] as Array<{ orgId: string; spaces: Array<{ spaceId: string; features?: string[] }> }>;
}

// NEW: Secure logout action
export async function logout() {
  const cookieStore = cookies();

  // Delete the session cookie
  cookieStore.delete(SESSION_COOKIE_NAME);

  // Optional: delete any other auth-related cookies
  // cookieStore.delete('username');
  // cookieStore.delete('other_token');

  // Redirect to login page
  redirect('/login');
}