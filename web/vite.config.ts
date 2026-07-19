import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy /api to the FastAPI proxy (or a remote deployment via VITE_API_TARGET).
// In production the SPA is served by Caddy on the same origin as /api, so no proxy needed.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://127.0.0.1:8080",
        changeOrigin: true,
      },
    },
  },
});
