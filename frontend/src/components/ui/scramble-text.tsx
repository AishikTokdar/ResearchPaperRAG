import * as React from "react";
import { cn } from "@/lib/utils";

interface ScrambleTextProps {
  text: string;
  className?: string;
  speed?: number;
  chars?: string;
}

const CLEAN_GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

export function ScrambleText({
  text,
  className = "",
  speed = 90,
  chars = CLEAN_GLYPHS,
}: ScrambleTextProps) {
  const [displayText, setDisplayText] = React.useState(text);
  const [isScrambling, setIsScrambling] = React.useState(false);
  const containerRef = React.useRef<HTMLSpanElement>(null);
  const hasTriggeredRef = React.useRef(false);

  const startScramble = React.useCallback(() => {
    if (isScrambling) return;
    setIsScrambling(true);

    let progress = 0;
    const totalChars = text.length;

    const interval = setInterval(() => {
      setDisplayText(
        text
          .split("")
          .map((char, index) => {
            if (char === " ") return " ";
            if (index < progress) return text[index];
            return chars[Math.floor(Math.random() * chars.length)];
          })
          .join(""),
      );

      progress += 0.35;

      if (progress >= totalChars) {
        clearInterval(interval);
        setDisplayText(text);
        setIsScrambling(false);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed, chars, isScrambling]);

  React.useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !hasTriggeredRef.current) {
          hasTriggeredRef.current = true;
          startScramble();
        }
      },
      { threshold: 0.2 },
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, [startScramble]);

  return (
    <span
      ref={containerRef}
      onMouseEnter={startScramble}
      className={cn("inline-block cursor-default font-mono transition-colors tracking-tight", className)}
    >
      {displayText}
    </span>
  );
}
