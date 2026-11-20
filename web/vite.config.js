import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Igual que nginx: el navegador llama a /api/... y se reenvía sin el prefijo.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
