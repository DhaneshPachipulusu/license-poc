import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/Sidebar';

export const metadata: Metadata = {
  title: 'License Control Panel',
  description: 'Enterprise License Management System',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-mesh" style={{ minHeight: '100vh' }}>
        <div style={{ display: 'flex', minHeight: '100vh' }}>
          <Sidebar />
          <main style={{ flex: 1, marginLeft: '256px', padding: '32px' }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}