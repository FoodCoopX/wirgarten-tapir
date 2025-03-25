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
          member_profile: join(
            INPUT_DIR,
            "/member_profile/member_profile_entry.tsx",
          ),
          csv_export_editor: join(
            INPUT_DIR,
            "/csv_export_editor/csv_export_editor_entry.tsx",
          ),
          pdf_export_editor: join(
            INPUT_DIR,
            "/pdf_export_editor/pdf_export_editor_entry.tsx",
          ),
          product_config: join(
            INPUT_DIR,
            "/product_config/product_config_entry.tsx",
          ),
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
