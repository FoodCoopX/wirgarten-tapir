import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  root: resolve(__dirname, "src"),
  base: "/static/mail/",
  resolve: {
    alias: {
      "tapir-api-client": resolve(__dirname, "../src_frontend/api-client"),
    },
  },
  server: {
    port: 5174,
  },
  build: {
    sourcemap: true,
    // The Arco theme bundled with easy-email contains invalid CSS that lightningcss refuses to minify.
    cssMinify: "esbuild",
    manifest: "manifest.json",
    emptyOutDir: true,
    outDir: resolve(__dirname, "../dist/mail"),
    rollupOptions: {
      input: { main: resolve(__dirname, "src/main.tsx") },
    },
  },
});
