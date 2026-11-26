import React from "react";
import { cn } from "../../utils/cn";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, id, ...props }, ref) => (
    <label className="block space-y-1.5 text-xs">
      {label && (
        <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
          {label}
        </span>
      )}
      <input
        ref={ref}
        id={id}
        className={cn(
          "w-full rounded-control border border-sand-200 bg-paper px-3 py-2 text-sm text-ink-900 placeholder:text-ink-500/70 focus:border-ink-900 focus:outline-none transition-colors",
          error && "border-status-danger-fg",
          className
        )}
        {...props}
      />
      {error && <span className="block text-xs text-status-danger-fg">{error}</span>}
    </label>
  )
);
Input.displayName = "Input";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, className, children, ...props }, ref) => (
    <label className="block space-y-1.5 text-xs">
      {label && (
        <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
          {label}
        </span>
      )}
      <select
        ref={ref}
        className={cn(
          "w-full rounded-control border border-sand-200 bg-paper px-3 py-2 text-sm text-ink-900 focus:border-ink-900 focus:outline-none transition-colors",
          className
        )}
        {...props}
      >
        {children}
      </select>
    </label>
  )
);
Select.displayName = "Select";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, className, ...props }, ref) => (
    <label className="block space-y-1.5 text-xs">
      {label && (
        <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
          {label}
        </span>
      )}
      <textarea
        ref={ref}
        className={cn(
          "w-full rounded-control border border-sand-200 bg-paper px-3 py-2 text-sm text-ink-900 placeholder:text-ink-500/70 focus:border-ink-900 focus:outline-none transition-colors",
          className
        )}
        {...props}
      />
    </label>
  )
);
Textarea.displayName = "Textarea";
