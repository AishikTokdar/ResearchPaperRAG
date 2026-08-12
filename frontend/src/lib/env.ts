/**
 * Environment resolution for Vite (Cloud & Local).
 *
 * 1. Localhost query parameter override (`?port=7860` or `?api_port=7860`):
 *    If present in `window.location.search` or session, targets local backend on specified port.
 * 2. Cloud deployment: Uses `VITE_API_BASE_URL` environment variable.
 * 3. Localhost fallback: Defaults to `http://localhost:8000`.
 */

function trimTrailingSlashes(s: string): string {
  return s.replace(/\/+$/, "");
}

export function resolveApiBaseUrl(): string {
  // 1. Check for browser query parameter ?port= or ?api_port= (used in local development)
  if (typeof window !== "undefined") {
    try {
      const search = window.location.search;
      if (search) {
        const urlParams = new URLSearchParams(search);
        const queryPort =
          urlParams.get("port") ||
          urlParams.get("api_port") ||
          urlParams.get("backend_port");
        if (queryPort && /^\d+$/.test(queryPort.trim())) {
          const port = queryPort.trim();
          sessionStorage.setItem("RESEARCH_PAG_PORT", port);
          const host = window.location.hostname || "localhost";
          return `http://${host}:${port}`;
        }

        const queryUrl = urlParams.get("api_url") || urlParams.get("backend_url");
        if (queryUrl && queryUrl.trim()) {
          const cleaned = trimTrailingSlashes(queryUrl.trim());
          sessionStorage.setItem("RESEARCH_PAG_API_URL", cleaned);
          return cleaned;
        }
      }

      const storedPort = sessionStorage.getItem("RESEARCH_PAG_PORT");
      if (storedPort && /^\d+$/.test(storedPort.trim())) {
        const host = window.location.hostname || "localhost";
        return `http://${host}:${storedPort.trim()}`;
      }

      const storedUrl = sessionStorage.getItem("RESEARCH_PAG_API_URL");
      if (storedUrl && storedUrl.trim()) {
        return trimTrailingSlashes(storedUrl.trim());
      }
    } catch {
      // Ignore sessionStorage/URL parsing error
    }
  }

  // 2. Check environment variable VITE_API_BASE_URL (used in Cloud deployments)
  const raw = import.meta.env.VITE_API_BASE_URL;
  const trimmed = typeof raw === "string" ? raw.trim() : "";

  if (trimmed) {
    if (trimmed.startsWith("/")) {
      const rel = trimTrailingSlashes(trimmed) || "/";
      if (rel !== "/") {
        return rel;
      }
    } else {
      return trimTrailingSlashes(trimmed);
    }
  }

  // 3. Dev proxy target / backend port env vars
  const envProxyTarget = import.meta.env.VITE_DEV_PROXY_TARGET;
  if (typeof envProxyTarget === "string" && envProxyTarget.trim()) {
    return trimTrailingSlashes(envProxyTarget.trim());
  }

  const envPort =
    import.meta.env.VITE_BACKEND_PORT || import.meta.env.VITE_PORT;
  if (envPort && String(envPort).trim()) {
    const host =
      typeof window !== "undefined" && window.location.hostname
        ? window.location.hostname
        : "localhost";
    return `http://${host}:${String(envPort).trim()}`;
  }

  // 4. Default localhost fallback
  const defaultHost =
    typeof window !== "undefined" && window.location.hostname
      ? window.location.hostname
      : "localhost";
  return `http://${defaultHost}:8000`;
}

export function resolveSentryTunnelUrl(apiBaseUrl: string): string {
  const base = trimTrailingSlashes(apiBaseUrl);
  if (base.startsWith("http://") || base.startsWith("https://")) {
    return `${base}/api/oversight`;
  }
  if (base.startsWith("/")) {
    return `${base}/oversight`;
  }
  return `${base}/api/oversight`;
}

export const API_BASE_URL = resolveApiBaseUrl();
export const SENTRY_TUNNEL_URL = resolveSentryTunnelUrl(API_BASE_URL);

/** Dynamically join API base (absolute URL or path like ``/api``) with an endpoint path */
export function joinApiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  const currentBase = trimTrailingSlashes(resolveApiBaseUrl());
  if (!currentBase || currentBase === "/") {
    return p;
  }
  return `${currentBase}${p}`;
}



