import React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Info,
  XCircle,
} from "lucide-react";
import { cn } from "../../utils/cn";

export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

const TONE_CLASSES: Record<StatusTone, string> = {
  success: "bg-status-success-bg text-status-success-fg",
  warning: "bg-status-warning-bg text-status-warning-fg",
  danger: "bg-status-danger-bg text-status-danger-fg",
  info: "bg-status-info-bg text-status-info-fg",
  neutral: "bg-status-neutral-bg text-status-neutral-fg",
};

const TONE_ICONS: Record<StatusTone, React.ComponentType<{ className?: string }>> = {
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
  info: Info,
  neutral: Clock,
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
      "PASS_WITH_TOLERANCE",
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
  const Icon = TONE_ICONS[resolved];
  return (
    <span
      data-testid="status-badge"
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold tracking-wide whitespace-nowrap",
        TONE_CLASSES[resolved],
        className
      )}
    >
      <Icon className="w-3 h-3 shrink-0" aria-hidden="true" />
      <span>{value}</span>
    </span>
  );
};

export const Badge = StatusPill;
