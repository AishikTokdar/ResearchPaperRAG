import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  startIcon?: React.ReactNode;
  endIcon?: React.ReactNode;
  wrapperClassName?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      type = "text",
      error,
      startIcon,
      endIcon,
      wrapperClassName,
      disabled,
      ...props
    },
    ref,
  ) => {
    if (startIcon || endIcon) {
      return (
        <div className={cn("relative flex items-center", wrapperClassName)}>
          {startIcon && (
            <span className="absolute left-3 text-white/90 pointer-events-none">
              {startIcon}
            </span>
          )}
          <input
            type={type}
            className={cn(
              "flex h-11 w-full rounded-xl border bg-white/5 px-4 py-2 text-sm text-white placeholder:text-slate-300",
              "focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50",
              "transition-all duration-200",
              "disabled:cursor-not-allowed disabled:opacity-50",
              error
                ? "border-red-500/50 focus:ring-red-500/50 focus:border-red-500/50"
                : "border-white/20",
              startIcon && "pl-10",
              endIcon && "pr-10",
              className,
            )}
            ref={ref}
            disabled={disabled}
            {...props}
          />
          {endIcon && (
            <span className="absolute right-3 text-white/90 pointer-events-none">
              {endIcon}
            </span>
          )}
        </div>
      );
    }

    // Simple input without icons
    return (
      <input
        type={type}
        className={cn(
          "flex h-11 w-full rounded-xl border bg-white/5 px-4 py-2 text-sm text-white placeholder:text-slate-300",
          "focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50",
          "transition-all duration-200",
          "disabled:cursor-not-allowed disabled:opacity-50",
          error
            ? "border-red-500/50 focus:ring-red-500/50 focus:border-red-500/50"
            : "border-white/20",
          className,
        )}
        ref={ref}
        disabled={disabled}
        {...props}
      />
    );
  },
);

Input.displayName = "Input";

export { Input };
