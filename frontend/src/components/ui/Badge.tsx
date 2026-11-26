import React from "react";
import { cn } from "../../utils/cn";

export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

const TONE_CLASSES: Record<StatusTone, string> = {
  success: "bg-status-success-bg text-status-success-fg border-status-success-fg/25",
  warning: "bg-status-warning-bg text-status-warning-fg border-status-warning-fg/25",
  danger: "bg-status-danger-bg text-status-danger-fg border-status-danger-fg/25",
  info: "bg-status-info-bg text-status-info-fg border-status-info-fg/25",
  neutral: "bg-status-neutral-bg text-status-neutral-fg border-sand-400/30",
};

const DOT_CLASSES: Record<StatusTone, string> = {
  success: "bg-status-success-fg",
  warning: "bg-status-warning-fg",
  danger: "bg-status-danger-fg",
  info: "bg-status-info-fg",
  neutral: "bg-status-neutral-fg",
};

export function inferStatusTone(value: string): StatusTone {
  const v = value.toUpperCase();
  if (
    [
      "MATCHED",
      "MATCHED_WITH_TOLERANCE",
      "APPROVED",
      "PASS",
      "SUCCEEDED",
      "ACTIVE",
      "VERIFIED",
      "EXTRACTED",
      "LOW",
    ].includes(v)
  ) {
    return "success";
  }
  if (
    [
      "VARIANCE",
      "PASS_WITH_TOLERANCE",
      "NEEDS_REVIEW",
      "REVIEW_REQUIRED",
      "INCOMPLETE",
      "MEDIUM",
      "OPEN",
      "DRAFT",
      "REQUEST_INFO",
    ].includes(v)
  ) {
    return "warning";
  }
  if (["EXCEPTION", "FAIL", "FAILED", "REJECTED", "CRITICAL", "HIGH", "ESCALATED"].includes(v)) {
    return "danger";
  }
  if (["INFO", "QUEUED", "PROCESSING", "RUNNING", "RISK_INDICATOR"].includes(v)) {
    return "info";
  }
  return "neutral";
}

export interface StatusPillProps {
  value: string;
  tone?: StatusTone;
  className?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({ value, tone, className }) => {
  const resolved = tone || inferStatusTone(value);
  return (
    <span
      data-testid="status-badge"
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-[11px] font-semibold tracking-wide whitespace-nowrap",
        TONE_CLASSES[resolved],
        className
      )}
    >
      <span
        className={cn("w-1.5 h-1.5 rounded-full shrink-0", DOT_CLASSES[resolved])}
        aria-hidden="true"
      />
      <span>{value}</span>
    </span>
  );
};

export const Badge = StatusPill;
