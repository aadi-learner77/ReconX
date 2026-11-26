import React from "react";
import { cn } from "../../utils/cn";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "hero" | "subtle";
}

export const Card: React.FC<CardProps> = ({
  variant = "default",
  className,
  children,
  ...props
}) => {
  const base =
    variant === "hero"
      ? "rounded-hero bg-sand-300 border border-sand-200 p-6 md:p-8 shadow-card"
      : variant === "subtle"
        ? "rounded-card bg-sand-100 border border-sand-200 p-5 shadow-hairline"
        : "rounded-card bg-paper border border-sand-200 p-5 shadow-card";

  return (
    <div className={cn(base, "animate-sandstone-enter", className)} {...props}>
      {children}
    </div>
  );
};

export interface StatProps {
  label: string;
  value: React.ReactNode;
  hint?: string;
  mono?: boolean;
  tone?: "default" | "success" | "warning" | "danger";
  className?: string;
}

export const Stat: React.FC<StatProps> = ({
  label,
  value,
  hint,
  mono = false,
  tone = "default",
  className,
}) => {
  const toneColor =
    tone === "success"
      ? "text-status-success-fg"
      : tone === "warning"
        ? "text-status-warning-fg"
        : tone === "danger"
          ? "text-status-danger-fg"
          : "text-ink-900";

  return (
    <div
      className={cn(
        "rounded-card bg-paper border border-sand-200 p-5 shadow-card",
        className
      )}
    >
      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
        {label}
      </div>
      <div
        className={cn(
          "mt-2 text-3xl md:text-[40px] md:leading-[1.08] font-bold tracking-tight",
          mono ? "font-mono tabular-nums text-2xl md:text-3xl" : "font-display",
          toneColor
        )}
      >
        {value}
      </div>
      {hint && <div className="mt-1.5 text-xs text-ink-500">{hint}</div>}
    </div>
  );
};

export interface PageCaptionProps {
  project?: string;
  module: string;
  index?: string;
  className?: string;
}

export const PageCaption: React.FC<PageCaptionProps> = ({
  project = "ReconX AI / Reconciliation Console",
  module,
  index = "Synchronise 2026 / PS-BA1_026",
  className,
}) => (
  <div
    className={cn(
      "grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5",
      className
    )}
  >
    {[project, module, index].map((col, idx) => (
      <div
        key={idx}
        className="border-t border-ink-900/35 pt-2 text-[11px] uppercase tracking-[0.08em] text-ink-500 font-medium truncate"
      >
        {col}
      </div>
    ))}
  </div>
);
