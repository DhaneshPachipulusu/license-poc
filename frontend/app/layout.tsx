import type { Metadata } from 'next';
import './globals.css';
import AppFrame from '@/components/AppFrame';

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
        <AppFrame>{children}</AppFrame>
      </body>
    </html>
  );
}