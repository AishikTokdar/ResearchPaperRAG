import { AlertTriangle } from "lucide-react";
import { GlassCard } from "./glass-card";


interface ProviderWarningAlertProps {
  warnings: string[];
  className?: string;
}

export function ProviderWarningAlert({ warnings, className = "" }: ProviderWarningAlertProps) {
  if (!warnings || warnings.length === 0) return null;

  return (
    <GlassCard
      padding="default"
      className={`mb-6 border-amber-500/40 bg-amber-500/10 text-amber-900 dark:text-amber-200 ${className}`}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
        <div className="space-y-1 text-xs">
          <p className="font-semibold text-amber-800 dark:text-amber-300 text-sm">
            AI Provider API Key Warning
          </p>
          <ul className="list-disc list-inside space-y-0.5 text-amber-700 dark:text-amber-300/90 font-mono">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      </div>
    </GlassCard>
  );
}
