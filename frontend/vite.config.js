import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
/**
 * Vite — dev proxy target is `VITE_DEV_PROXY_TARGET` (default http://127.0.0.1:8000).
 * Frontend API URL is still `VITE_API_BASE_URL` in `src/lib/env.ts`.
 */
export default defineConfig(function (_a) {
    var _b, _c;
    var mode = _a.mode;
    var env = loadEnv(mode, process.cwd(), "");
    var targetPort = env.VITE_BACKEND_PORT || env.PORT || "8000";
    var proxyTarget = ((_b = env.VITE_DEV_PROXY_TARGET) === null || _b === void 0 ? void 0 : _b.trim()) ||
        (((_c = env.VITE_API_BASE_URL) === null || _c === void 0 ? void 0 : _c.trim().startsWith("http"))
            ? env.VITE_API_BASE_URL.trim()
            : "http://127.0.0.1:".concat(targetPort));
    var apiProxy = {
        "/api/": { target: proxyTarget, changeOrigin: true },
        "^/(health|status|upload|ask|models|runtime-summary|pipeline-info|docs|redoc|openapi\\.json)(/|$)": { target: proxyTarget, changeOrigin: true },
    };
    return {
        plugins: [react()],
        resolve: {
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
            sourcemap: false,
            target: "es2020",
            minify: "esbuild",
            cssCodeSplit: true,
            chunkSizeWarningLimit: 1000,
            rollupOptions: {
                output: {
                    manualChunks: function (id) {
                        if (id.includes("react-dom/server") || id.includes("react-dom/cjs/react-dom-server"))
                            return "pdf-renderer";
                        if (id.includes("react-router-dom") ||
                            id.includes("/react/") ||
                            id.includes("react-dom")) {
                            return "vendor";
                        }
                        if (id.includes("framer-motion"))
                            return "motion";
                        if (id.includes("lucide-react"))
                            return "icons";
                        return undefined;
                    },
                },
            },
        },
    };
});
