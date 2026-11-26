import React from "react";
import { cn } from "../../utils/cn";

export interface ReconXMarkProps {
  variant?: "full" | "icon" | "mono-light" | "mono-dark";
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZE_MAP = {
  sm: { box: "w-8 h-8", text: "text-lg" },
  md: { box: "w-10 h-10", text: "text-xl" },
  lg: { box: "w-14 h-14", text: "text-3xl" },
};

export const ReconXMark: React.FC<ReconXMarkProps> = ({
  variant = "full",
  size = "md",
  className,
}) => {
  const dims = SIZE_MAP[size];
  const colorClass =
    variant === "mono-light"
      ? "text-paper"
      : variant === "mono-dark"
        ? "text-ink-900"
        : "text-ink-900";

  const icon = (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      aria-hidden="true"
      className={cn(dims.box, "shrink-0", colorClass)}
    >
      {/* Rounded outer ledger frame */}
      <rect
        x="3"
        y="3"
        width="42"
        height="42"
        rx="12"
        stroke="currentColor"
        strokeWidth="2.5"
      />
      {/* Three converging nodes: PO (top-left), GRN (top-right), Invoice (bottom-center) */}
      <rect x="11" y="11" width="9" height="9" rx="4.5" fill="currentColor" fillOpacity="0.9" />
      <rect x="28" y="11" width="9" height="9" rx="4.5" fill="currentColor" fillOpacity="0.65" />
      <rect x="19.5" y="29" width="9" height="9" rx="4.5" fill="currentColor" fillOpacity="0.9" />
      {/* Converging X intersection */}
      <path
        d="M15.5 15.5L32.5 32.5M32.5 15.5L15.5 32.5"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <circle cx="24" cy="24" r="2.75" fill="currentColor" />
    </svg>
  );

  if (variant === "icon") {
    return <span className={cn("inline-flex items-center", className)}>{icon}</span>;
  }

  return (
    <span className={cn("inline-flex items-center gap-3 select-none", colorClass, className)}>
      {icon}
      <span className={cn("font-display font-bold tracking-tight leading-none", dims.text)}>
        ReconX
        <sup className="ml-0.5 text-[0.5em] font-semibold tracking-wider opacity-75">AI</sup>
        <span className="ml-0.5 text-[0.4em] align-top font-medium opacity-55">TM</span>
      </span>
    </span>
  );
};
