import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: process.env.VITE_BASE_PATH || "/",
  build: { outDir: "dist", sourcemap: false },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8400",
      "/health": "http://localhost:8400",
      "/query": "http://localhost:8400",
      "/ingest": "http://localhost:8400",
      "/gaps": "http://localhost:8400",
    },
  },
}));
