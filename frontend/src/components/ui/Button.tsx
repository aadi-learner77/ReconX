import React from "react";
import { Loader2 } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../utils/cn";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-control text-sm font-medium transition-all duration-150 ease-out active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none select-none",
  {
    variants: {
      variant: {
        primary:
          "bg-ink-900 text-on-ink hover:-translate-y-px hover:opacity-95 shadow-hairline",
        secondary:
          "bg-transparent text-ink-900 border border-ink-900 hover:bg-sand-100",
        ghost:
          "bg-transparent text-ink-700 hover:bg-sand-100 hover:text-ink-900",
        outline:
          "bg-paper text-ink-900 border border-sand-200 hover:border-sand-400 hover:bg-sand-50",
        danger:
          "bg-status-danger-fg text-paper hover:-translate-y-px hover:opacity-95 shadow-hairline",
        destructive:
          "bg-status-danger-fg text-paper hover:-translate-y-px hover:opacity-95 shadow-hairline",
      },
      size: {
        sm: "px-3 py-1.5 text-xs",
        md: "px-4 py-2 text-sm",
        lg: "px-5 py-2.5 text-sm font-semibold",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type = "button", loading = false, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    >
      {loading && <Loader2 className="w-4 h-4 animate-spin shrink-0" aria-hidden="true" />}
      {children}
    </button>
  )
);
Button.displayName = "Button";

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ label, className, children, type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex items-center justify-center w-9 h-9 rounded-control border border-sand-200 bg-paper text-ink-700 hover:text-ink-900 hover:border-sand-400 hover:bg-sand-50 transition-colors duration-150",
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
);
IconButton.displayName = "IconButton";
