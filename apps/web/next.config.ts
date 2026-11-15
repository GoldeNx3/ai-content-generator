import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Panel nie używa next/image; wyłączony optymalizator zamyka publiczny endpoint /_next/image.
  images: { unoptimized: true },
};

export default nextConfig;
