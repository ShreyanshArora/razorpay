/** @type {import('next').NextConfig} */
const dev = process.env.NODE_ENV !== 'production';
module.exports = {
  reactStrictMode: true,
  async rewrites() {
    // In dev, proxy /api to the local backend. In prod the app calls
    // NEXT_PUBLIC_API_URL directly (set in Vercel), so no rewrite needed.
    return dev ? [{ source: '/api/:path*', destination: 'http://127.0.0.1:8000/api/:path*' }] : [];
  },
};
