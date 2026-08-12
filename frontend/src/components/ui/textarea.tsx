import * as React from "react";
import { cn } from "@/lib/utils";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
  autoResize?: boolean;
  showCount?: boolean;
  wrapperClassName?: string;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      className,
      error,
      autoResize,
      showCount,
      maxLength,
      wrapperClassName,
      disabled,
      onChange,
      value,
      ...props
    },
    ref,
  ) => {
    const [charCount, setCharCount] = React.useState(0);
    const textareaRef = React.useRef<HTMLTextAreaElement>(null);

    React.useImperativeHandle(ref, () => textareaRef.current!);

    React.useEffect(() => {
      if (autoResize && textareaRef.current) {
        textareaRef.current.style.height = "auto";
        textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
      }
    }, [value, autoResize]);

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      if (showCount) {
        setCharCount(e.target.value.length);
      }
      onChange?.(e);
    };

    React.useEffect(() => {
      if (showCount && typeof value === "string") {
        setCharCount(value.length);
      }
    }, [value, showCount]);

    return (
      <div className={cn("relative min-w-0", wrapperClassName)}>
        <textarea
          ref={textareaRef}
          className={cn(
            "block min-h-[100px] w-full max-w-full rounded-xl border bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-300",
            "focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50",
            "transition-all duration-200",
            "disabled:cursor-not-allowed disabled:opacity-50",
            error
              ? "border-red-500/50 focus:ring-red-500/50 focus:border-red-500/50"
              : "border-white/20",
            autoResize ? "resize-none overflow-hidden" : "resize-y",
            showCount && "pb-8",
            className,
          )}
          disabled={disabled}
          onChange={handleChange}
          value={value}
          maxLength={maxLength}
          {...props}
        />

        {showCount && (
          <div
            className={cn(
              "absolute bottom-2 right-3 text-xs",
              maxLength && charCount >= maxLength
                ? "text-red-400"
                : "text-slate-300",
            )}
          >
            {charCount}
            {maxLength && ` / ${maxLength}`}
          </div>
        )}
      </div>
    );
  },
);

Textarea.displayName = "Textarea";

export { Textarea };
