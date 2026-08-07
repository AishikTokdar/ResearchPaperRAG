import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 dark:focus-visible:ring-zinc-600 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-zinc-900 text-zinc-100 hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 shadow-sm",
        destructive:
          "bg-red-600 text-white hover:bg-red-700 shadow-sm",
        outline:
          "border border-zinc-200 dark:border-zinc-800 bg-transparent text-zinc-900 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800/80",
        secondary:
          "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-200 dark:hover:bg-zinc-700",
        ghost:
          "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-100",
        link:
          "text-zinc-900 dark:text-zinc-100 underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 px-3 text-xs rounded-lg",
        lg: "h-12 px-6 text-base rounded-2xl",
        icon: "h-9 w-9 p-0 rounded-lg",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  withRipple?: boolean;
  withShine?: boolean;
  icon?: React.ReactNode;
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      withRipple = false,
      withShine = false,
      icon,
      children,
      onClick,
      asChild = false,
      ...props
    },
    ref,
  ) => {
    const buttonClasses = cn(buttonVariants({ variant, size }), className);

    if (asChild && React.isValidElement(children)) {
      return React.cloneElement(
        children as React.ReactElement<{ className?: string }>,
        {
          className: cn(
            buttonClasses,
            (children as React.ReactElement<{ className?: string }>).props
              .className,
          ),
        },
      );
    }

    return (
      <button className={buttonClasses} ref={ref} onClick={onClick} {...props}>
        {icon && <span className="shrink-0">{icon}</span>}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";

export { Button, buttonVariants };
