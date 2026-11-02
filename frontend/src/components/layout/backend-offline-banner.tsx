import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RefreshCw, ServerOff } from "lucide-react";
import { Link } from "react-router-dom";
import { useHealth } from "@/context/health-context";
import { Button } from "@/components/ui/button";

export function BackendOfflineBanner() {
  const { isProlongedOffline, isChecking, checkNow } = useHealth();
  const [dismissed, setDismissed] = React.useState(false);

  // If backend comes back online, reset dismissed state so it shows if it drops again
  React.useEffect(() => {
    if (!isProlongedOffline) {
      setDismissed(false);
    }
  }, [isProlongedOffline]);

  if (!isProlongedOffline || dismissed) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.aside
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={{ duration: 0.2 }}
        className="relative z-40 bg-red-950/40 border-b border-red-500/30 text-red-200 px-4 py-2.5 backdrop-blur-md"
        role="alert"
        aria-live="polite"
      >
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-red-500/20 text-red-400 shrink-0">
              <ServerOff className="h-4 w-4" />
            </span>
            <div className="leading-snug">
              <strong className="font-semibold text-red-300">Backend Server Offline:</strong>{" "}
              <span className="text-zinc-300">
                The API server is currently unreachable. If running on a cloud free tier (e.g. Hugging Face Spaces), it may take 30–60s to wake up.
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => void checkNow()}
              disabled={isChecking}
              className="h-7 px-2.5 text-xs bg-red-500/10 hover:bg-red-500/20 text-red-200 border-red-500/40 gap-1.5"
            >
              <RefreshCw className={`w-3 h-3 ${isChecking ? "animate-spin" : ""}`} />
              {isChecking ? "Checking..." : "Retry Connection"}
            </Button>
            <Link
              to="/api-status"
              className="text-xs text-red-300 hover:text-red-100 underline underline-offset-2 px-1"
            >
              Status
            </Link>
            <button
              type="button"
              onClick={() => setDismissed(true)}
              className="ml-1 text-red-400 hover:text-red-200 text-sm font-semibold p-1"
              aria-label="Dismiss offline banner"
            >
              ✕
            </button>
          </div>
        </div>
      </motion.aside>
    </AnimatePresence>
  );
}
