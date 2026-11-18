import type { NextConfig } from "next";

// All API traffic goes through this app (same origin), so the backend needs no CORS and the
// refresh token can live in an httpOnly cookie. Route handlers under /api/auth take precedence
// over this rewrite; everything else under /api is forwarded to FastAPI.
const backend = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  reactCompiler: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/:path*` }];
  },
};

export default nextConfig;
