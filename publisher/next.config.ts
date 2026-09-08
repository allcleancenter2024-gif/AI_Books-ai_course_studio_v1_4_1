import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  distDir: process.env.PUBLISHER_BUILD_DIR || '.next',
  turbopack: { root: __dirname },
};

export default nextConfig;
