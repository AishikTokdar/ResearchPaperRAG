import * as React from "react";
import { joinApiUrl } from "@/lib/constants";

export type HealthStatus = "connected" | "disconnected" | "checking";

export interface HealthContextValue {
  status: HealthStatus;
  isOffline: boolean;
  isProlongedOffline: boolean;
  offlineSince: Date | null;
  consecutiveFailures: number;
  lastChecked: Date | null;
  isChecking: boolean;
  checkNow: () => Promise<void>;
}

const HealthContext = React.createContext<HealthContextValue | undefined>(undefined);

// Timing configurations
const INITIAL_TIMEOUT_MS = 8_000;
const ONLINE_POLL_INTERVAL_MS = 45_000;
const OFFLINE_POLL_INTERVAL_MS = 12_000;
const PROLONGED_OFFLINE_THRESHOLD_MS = 20_000;

export function HealthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<HealthStatus>("checking");
  const [isChecking, setIsChecking] = React.useState<boolean>(false);
  const [lastChecked, setLastChecked] = React.useState<Date | null>(null);
  const [offlineSince, setOfflineSince] = React.useState<Date | null>(null);
  const [consecutiveFailures, setConsecutiveFailures] = React.useState<number>(0);

  const consecutiveFailuresRef = React.useRef<number>(0);
  const offlineSinceRef = React.useRef<Date | null>(null);
  const pollTimerRef = React.useRef<number | null>(null);

  const checkHealth = React.useCallback(async (isManual = false) => {
    if (!isManual && document.visibilityState === "hidden") {
      return;
    }

    setIsChecking(true);
    const now = new Date();

    try {
      const res = await fetch(joinApiUrl("/health"), {
        signal: AbortSignal.timeout(INITIAL_TIMEOUT_MS),
        cache: "no-store",
      });

      setLastChecked(now);

      if (res.ok) {
        consecutiveFailuresRef.current = 0;
        offlineSinceRef.current = null;
        setConsecutiveFailures(0);
        setOfflineSince(null);
        setStatus("connected");
      } else {
        throw new Error(`Health check returned status ${res.status}`);
      }
    } catch {
      consecutiveFailuresRef.current += 1;
      const failures = consecutiveFailuresRef.current;
      setConsecutiveFailures(failures);
      setLastChecked(now);

      if (!offlineSinceRef.current) {
        offlineSinceRef.current = now;
        setOfflineSince(now);
      }

      // Mark as disconnected if >= 1 failure (or immediately on manual retry)
      setStatus("disconnected");
    } finally {
      setIsChecking(false);
    }
  }, []);

  // Manual trigger exposed to UI
  const checkNow = React.useCallback(async () => {
    await checkHealth(true);
  }, [checkHealth]);

  // Dynamic Polling Loop
  React.useEffect(() => {
    let cancelled = false;

    const scheduleNext = () => {
      if (cancelled) return;
      if (pollTimerRef.current) {
        window.clearTimeout(pollTimerRef.current);
      }

      // If disconnected, poll faster (12s) to detect waking servers (HF Spaces / free containers)
      // If connected, poll every 45s
      const delay = status === "disconnected" ? OFFLINE_POLL_INTERVAL_MS : ONLINE_POLL_INTERVAL_MS;

      pollTimerRef.current = window.setTimeout(async () => {
        if (!cancelled) {
          await checkHealth(false);
          scheduleNext();
        }
      }, delay);
    };

    // Run initial health check on mount
    void (async () => {
      await checkHealth(false);
      scheduleNext();
    })();

    // Also re-check when browser tab regains visibility
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void checkHealth(false);
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      if (pollTimerRef.current) {
        window.clearTimeout(pollTimerRef.current);
      }
    };
  }, [checkHealth, status]);

  const isOffline = status === "disconnected";
  const isProlongedOffline =
    isOffline &&
    Boolean(
      consecutiveFailures >= 2 ||
        (offlineSince && Date.now() - offlineSince.getTime() >= PROLONGED_OFFLINE_THRESHOLD_MS)
    );

  const value = React.useMemo<HealthContextValue>(
    () => ({
      status,
      isOffline,
      isProlongedOffline,
      offlineSince,
      consecutiveFailures,
      lastChecked,
      isChecking,
      checkNow,
    }),
    [
      status,
      isOffline,
      isProlongedOffline,
      offlineSince,
      consecutiveFailures,
      lastChecked,
      isChecking,
      checkNow,
    ]
  );

  return <HealthContext.Provider value={value}>{children}</HealthContext.Provider>;
}

export function useHealth(): HealthContextValue {
  const context = React.useContext(HealthContext);
  if (!context) {
    throw new Error("useHealth must be used within a HealthProvider");
  }
  return context;
}
