import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  outputFileTracingIncludes: {
    "/**": ["../public_data/*.json", "../data/prediction_history/**/*.json"],
  },
};

export default nextConfig;
