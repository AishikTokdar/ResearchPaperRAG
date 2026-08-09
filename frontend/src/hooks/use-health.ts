import * as React from "react";
import { joinApiUrl } from "@/lib/constants";

export type HealthStatus = "connected" | "disconnected" | "checking";

interface UseHealthReturn {
  status: HealthStatus;
}

const POLL_INTERVAL_MS = 60_000;
const MAX_CONSECUTIVE_FAILURES = 3;

export function useHealth(): UseHealthReturn {
  const [status, setStatus] = React.useState<HealthStatus>("checking");
  const consecutiveFailuresRef = React.useRef<number>(0);

  React.useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const res = await fetch(joinApiUrl("/health"), {
          signal: AbortSignal.timeout(12000),
        });
        if (!cancelled) {
          if (res.ok) {
            consecutiveFailuresRef.current = 0;
            setStatus("connected");
          } else {
            consecutiveFailuresRef.current += 1;
            if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
              setStatus("disconnected");
            }
          }
        }
      } catch {
        if (!cancelled) {
          consecutiveFailuresRef.current += 1;
          if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
            setStatus("disconnected");
          }
        }
      }
    };

    check();
    const id = setInterval(check, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return { status };
}
