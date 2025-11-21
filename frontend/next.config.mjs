/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    LICENSE_SERVER_URL: process.env.LICENSE_SERVER_URL || 'http://localhost:8000',
  },
}

export default nextConfig;
