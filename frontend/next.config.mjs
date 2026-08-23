/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const apiBase = process.env.BACKEND_ORIGIN || "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${apiBase}/api/:path*` },
      { source: "/backend-api/:path*", destination: `${apiBase}/api/:path*` },
    ];
  },
};

export default nextConfig;
