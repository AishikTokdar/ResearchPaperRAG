import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface SpotlightCardProps extends HTMLAttributes<HTMLDivElement> {
  spotlightColor?: string;
}

export function SpotlightCard({ children, className, spotlightColor: _spotlightColor, ...props }: SpotlightCardProps) {
  return <div className={cn("surface-card p-5 sm:p-6", className)} {...props}>{children}</div>;
}
