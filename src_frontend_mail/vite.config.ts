import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  root: resolve(import.meta.dirname, "src"),
  base: "/static/mail/",
  resolve: {
    alias: {
      "tapir-api-client": resolve(
        import.meta.dirname,
        "../src_frontend/api-client",
      ),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5174,
    cors: true,
    // The page is served by Django, so asset URLs in CSS (e.g. fonts) must point to the dev server.
    origin: "http://localhost:5174",
  },
  build: {
    // The Arco theme bundled with easy-email contains invalid CSS that lightningcss refuses to minify.
    cssMinify: "esbuild",
    manifest: "manifest.json",
    emptyOutDir: true,
    outDir: resolve(import.meta.dirname, "../dist/mail"),
    rollupOptions: {
      input: { main: resolve(import.meta.dirname, "src/main.tsx") },
    },
  },
});
