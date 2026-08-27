import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The SPA talks to both services through the same origin. In dev, the proxy
// strips the /api/<service> prefix and forwards to the running services.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api/crypto": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/crypto/, ""),
      },
      "/api/target": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/target/, ""),
      },
    },
  },
});