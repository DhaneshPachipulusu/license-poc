import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  fallback: [
    '-apple-system',
    'BlinkMacSystemFont',
    'Segoe UI',
    'Roboto',
    'Helvetica Neue',
    'Arial',
    'sans-serif',
  ],
})

export const metadata: Metadata = {
  title: 'License Admin Dashboard',
  description: 'Manage software licenses and customer deployments',
  keywords: [
    'license management',
    'software licensing',
    'admin dashboard',
  ],
  authors: [
    {
      name: 'Your Company',
    },
  ],
  robots: {
    index: false,
    follow: false,
  },
}

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: '#4f46e5',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head>
        {/* Prevent layout shift */}
        <meta charSet="utf-8" />
      </head>
      <body className={`${inter.className} antialiased`}>
        {/* Global providers/contexts can go here in the future */}
        {children}
      </body>
    </html>
  )
}