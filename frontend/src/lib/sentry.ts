import * as Sentry from "@sentry/react";

export function initSentry(): void {
  // Error reporting is an explicit deployment choice, never a bundled destination.
  const dsn = import.meta.env.VITE_SENTRY_DSN?.trim();
  if (!dsn) return;

  Sentry.init({
    dsn,
    sendDefaultPii: false,
    // Documents, prompts and generated answers must not enter replay or trace payloads.
    integrations: [],
    tracesSampleRate: 0,
    tracePropagationTargets: [],
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
    enableLogs: false,
    beforeBreadcrumb: () => null,
    beforeSend(event) {
      delete event.user;
      delete event.request;
      delete event.extra;
      delete event.contexts;
      delete event.breadcrumbs;
      delete event.message;
      delete event.tags;
      delete event.transaction;
      delete event.fingerprint;
      if (event.exception?.values) {
        for (const exception of event.exception.values) {
          delete exception.mechanism;
          exception.value = "Application error (message redacted)";
          if (exception.stacktrace?.frames) {
            for (const frame of exception.stacktrace.frames) {
              if (frame.filename) frame.filename = frame.filename.split(/[?#]/, 1)[0];
              delete frame.vars;
              delete frame.pre_context;
              delete frame.post_context;
              delete frame.context_line;
            }
          }
        }
      }
      return {
        type: event.type,
        event_id: event.event_id,
        timestamp: event.timestamp,
        platform: event.platform,
        level: event.level,
        release: event.release,
        environment: event.environment,
        exception: event.exception,
      };
    },
    environment: import.meta.env.VITE_APP_ENV || import.meta.env.MODE || "development",
    ignoreErrors: [
      "ResizeObserver loop limit exceeded",
      "ResizeObserver loop completed with undelivered notifications",
    ],
  });
}

export { Sentry };
