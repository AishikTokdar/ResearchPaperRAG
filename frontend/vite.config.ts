import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const targetPort = env.VITE_BACKEND_PORT || env.PORT || "8000";
  const proxyTarget =
    env.VITE_DEV_PROXY_TARGET?.trim() ||
    (env.VITE_API_BASE_URL?.trim().startsWith("http")
      ? env.VITE_API_BASE_URL.trim()
      : `http://127.0.0.1:${targetPort}`);

  const apiProxy = {
    "/api/": { target: proxyTarget, changeOrigin: true },
    "^/(health|status|upload|ask|models|runtime-summary|pipeline-info|docs|redoc|openapi\\.json)(/|$)": { target: proxyTarget, changeOrigin: true },
  };

  return {
    plugins: [react()],
    resolve: {
      dedupe: ["react", "react-dom"],
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
        "@/components": fileURLToPath(new URL("./src/components", import.meta.url)),
        "@/hooks": fileURLToPath(new URL("./src/hooks", import.meta.url)),
        "@/lib": fileURLToPath(new URL("./src/lib", import.meta.url)),
        "@/types": fileURLToPath(new URL("./src/types", import.meta.url)),
        "@/context": fileURLToPath(new URL("./src/context", import.meta.url)),
        "@/pages": fileURLToPath(new URL("./src/pages", import.meta.url)),
      },
    },
    server: {
      port: 5173,
      proxy: apiProxy,
    },
    preview: { proxy: apiProxy },
    build: {
      outDir: "dist",
      emptyOutDir: false,
      sourcemap: false,
      target: "es2020",
      minify: "esbuild",
      cssCodeSplit: true,
      chunkSizeWarningLimit: 1000,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes("react-dom/server") || id.includes("react-dom/cjs/react-dom-server")) return "pdf-renderer";
            if (
              id.includes("react-router-dom") ||
              id.includes("/react/") ||
              id.includes("react-dom")
            ) {
              return "vendor";
            }
            if (id.includes("framer-motion")) return "motion";
            if (id.includes("lucide-react")) return "icons";
            return undefined;
          },
        },
      },
    },
  };
});
