import { cn } from "@/lib/utils";

interface AnimatedGridPatternProps {
  className?: string;
}

export function AnimatedGridPattern({ className }: AnimatedGridPatternProps) {
  return (
    <div
      className={cn(
        "pointer-events-none absolute inset-0 overflow-hidden opacity-30 dark:opacity-20",
        className,
      )}
    >
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, rgba(16, 185, 129, 0.25) 1px, transparent 0)`,
          backgroundSize: "28px 28px",
        }}
      />
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-emerald-500/10 dark:bg-emerald-500/5 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-blue-500/10 dark:bg-blue-500/5 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "2s" }} />
    </div>
  );
}
