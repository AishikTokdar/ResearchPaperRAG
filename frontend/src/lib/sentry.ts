import * as Sentry from "@sentry/react";
import { API_BASE_URL } from "./env";

const SENTRY_DSN =
  import.meta.env.VITE_SENTRY_DSN ||
  "https://e7954adc927ca26a7b9c6af391c43e14@o4510346504699904.ingest.de.sentry.io/4511213060751440";

const sentryTunnelUrl = `${API_BASE_URL.replace(/\/+$/, "")}/api/oversight`;

export function initSentry(): void {
  if (!SENTRY_DSN) return;

  Sentry.init({
    dsn: SENTRY_DSN,
    tunnel: sentryTunnelUrl,
    sendDefaultPii: true,

    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: false,
        blockAllMedia: false,
      }),
    ],

    tracesSampleRate: parseFloat(
      import.meta.env.VITE_SENTRY_TRACES_RATE || "1.0",
    ),
    tracePropagationTargets: [
      "localhost",
      /^https?:\/\/.*\.vercel\.app/,
      /^https?:\/\/.*$/,
    ],

    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,

    enableLogs: true,

    environment:
      import.meta.env.VITE_APP_ENV ||
      import.meta.env.MODE ||
      "development",

    ignoreErrors: [
      "top.GLOBALS",
      "ResizeObserver loop limit exceeded",
      "ResizeObserver loop completed with undelivered notifications",
      "Non-Error promise rejection captured",
    ],
  });
}

export { Sentry };
