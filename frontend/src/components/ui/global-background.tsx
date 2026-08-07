import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface GlobalBackgroundProps {
  className?: string;
}

export function GlobalBackground({ className }: GlobalBackgroundProps) {
  return (
    <div
      className={cn(
        "fixed inset-0 pointer-events-none z-0 overflow-hidden select-none transition-colors duration-500",
        className,
      )}
      aria-hidden="true"
    >
      {/* Dynamic Grid Dots Pattern */}
      <div
        className="absolute inset-0 opacity-[0.18] dark:opacity-[0.12]"
        style={{
          backgroundImage: `radial-gradient(circle at 1.5px 1.5px, currentColor 1px, transparent 0)`,
          backgroundSize: "32px 32px",
        }}
      />

      {/* Floating Animated Gradient Orb 1 (Emerald Glow) */}
      <motion.div
        animate={{
          x: [0, 80, -40, 0],
          y: [0, -60, 50, 0],
          scale: [1, 1.15, 0.95, 1],
        }}
        transition={{
          duration: 22,
          repeat: Number.POSITIVE_INFINITY,
          ease: "easeInOut",
        }}
        className="absolute -top-32 -left-32 w-[500px] h-[500px] rounded-full bg-gradient-to-tr from-emerald-500/15 via-teal-500/10 to-transparent blur-[120px] dark:from-emerald-500/10 dark:via-teal-500/5"
      />

      {/* Floating Animated Gradient Orb 2 (Blue Glow) */}
      <motion.div
        animate={{
          x: [0, -90, 50, 0],
          y: [0, 80, -40, 0],
          scale: [1, 0.9, 1.1, 1],
        }}
        transition={{
          duration: 26,
          repeat: Number.POSITIVE_INFINITY,
          ease: "easeInOut",
          delay: 3,
        }}
        className="absolute top-1/2 right-0 -translate-y-1/2 w-[550px] h-[550px] rounded-full bg-gradient-to-br from-blue-500/15 via-indigo-500/10 to-transparent blur-[140px] dark:from-blue-500/10 dark:via-indigo-500/5"
      />

      {/* Floating Animated Gradient Orb 3 (Bottom Center Ambient) */}
      <motion.div
        animate={{
          x: [0, 50, -50, 0],
          y: [0, -40, 40, 0],
          scale: [1, 1.1, 0.95, 1],
        }}
        transition={{
          duration: 28,
          repeat: Number.POSITIVE_INFINITY,
          ease: "easeInOut",
          delay: 7,
        }}
        className="absolute -bottom-40 left-1/3 w-[600px] h-[600px] rounded-full bg-gradient-to-t from-purple-500/10 via-emerald-500/5 to-transparent blur-[150px] dark:from-purple-500/5 dark:via-emerald-500/3"
      />

      {/* Subtle Radial Vignette Fade */}
      <div className="absolute inset-0 bg-radial from-transparent via-transparent to-white/40 dark:to-zinc-950/40" />
    </div>
  );
}
