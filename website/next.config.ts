import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  outputFileTracingIncludes: {
    "/**": ["../public_data/*.json"],
  },
};

export default nextConfig;
