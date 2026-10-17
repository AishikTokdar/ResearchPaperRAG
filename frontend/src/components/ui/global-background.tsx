import { cn } from "@/lib/utils";

export function GlobalBackground({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("fixed inset-0 pointer-events-none z-0 bg-[var(--bg-main)]", className)} />;
}
