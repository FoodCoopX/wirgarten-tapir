import { defineConfig } from "vite";
import { join, resolve } from "path";
import react from "@vitejs/plugin-react-swc";

export default defineConfig(() => {
  const INPUT_DIR = "./src_frontend";
  const OUTPUT_DIR = "./dist/";

  return {
    plugins: [react()],
    root: resolve(INPUT_DIR),
    base: "/static/",
    build: {
      target: "es6",
      sourcemap: true,
      manifest: "manifest.json",
      emptyOutDir: true,
      outDir: resolve(OUTPUT_DIR),
      rollupOptions: {
        input: {
          home_test: join(INPUT_DIR, "/jokers/joker_test_entry.tsx"),
        },
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      cors: true,
    },
  };
});
