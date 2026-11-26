import React, { useState } from "react";
import { FileCheck2 } from "lucide-react";
import { cn } from "../../utils/cn";
import { formatInrString } from "../../utils/money";
import { Drawer } from "./Overlay";

export interface ConfidenceMeterProps {
  /** Score in 0..1 or 0..100 */
  value: number;
  segments?: number;
  label?: string;
  className?: string;
}

export const ConfidenceMeter: React.FC<ConfidenceMeterProps> = ({
  value,
  segments = 10,
  label,
  className,
}) => {
  const pct = value <= 1 ? Math.round(value * 100) : Math.round(value);
  const clamped = Math.max(0, Math.min(100, pct));
  const filledCount = Math.round((clamped / 100) * segments);
  const barTone =
    clamped >= 80
      ? "bg-status-success-fg"
      : clamped >= 50
        ? "bg-status-warning-fg"
        : "bg-status-danger-fg";

  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      {label && <span className="text-xs text-ink-500">{label}</span>}
      <div
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={clamped}
        aria-label={label || "Confidence"}
        className="inline-flex items-center gap-0.5"
      >
        {Array.from({ length: segments }).map((_, i) => (
          <span
            key={i}
            className={cn(
              "h-1.5 w-2.5 rounded-[2px] transition-colors",
              i < filledCount ? barTone : "bg-sand-200"
            )}
          />
        ))}
      </div>
      <span className="font-mono tabular-nums text-[11px] font-semibold text-ink-700">
        {clamped}%
      </span>
    </div>
  );
};

export interface CitationEvidence {
  citation_id: string;
  source_type?: string;
  record_id?: string;
  field?: string;
  observed_value?: string;
  page?: number;
}

export interface CitationChipProps {
  id: string;
  evidence?: CitationEvidence;
  onClick?: () => void;
  className?: string;
}

export const CitationChip: React.FC<CitationChipProps> = ({
  id,
  evidence,
  onClick,
  className,
}) => {
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      setDrawerOpen(true);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        className={cn(
          "inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-status-warning-fg/55 bg-status-warning-bg/40 text-ink-900 font-mono text-[11px] font-medium hover:bg-status-warning-bg/70 transition-colors",
          className
        )}
      >
        <FileCheck2 className="w-3 h-3 text-status-warning-fg shrink-0" aria-hidden="true" />
        <span>{id}</span>
      </button>

      {!onClick && (
        <Drawer
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          title={`Evidence Reference · ${id}`}
          subtitle={evidence?.source_type || "Authoritative PostgreSQL Provenance"}
        >
          <div className="space-y-4 text-sm">
            <div className="rounded-card border border-sand-200 bg-sand-50 p-4 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] uppercase tracking-[0.08em] text-ink-500">
                  Citation ID
                </span>
                <span className="font-mono text-xs font-semibold text-ink-900">{id}</span>
              </div>
              {evidence?.source_type && (
                <div className="flex items-center justify-between">
                  <span className="text-[11px] uppercase tracking-[0.08em] text-ink-500">
                    Source Type
                  </span>
                  <span className="font-mono text-xs text-ink-900">{evidence.source_type}</span>
                </div>
              )}
              {evidence?.record_id && (
                <div className="flex items-center justify-between">
                  <span className="text-[11px] uppercase tracking-[0.08em] text-ink-500">
                    Record
                  </span>
                  <span className="font-mono text-xs text-ink-900">{evidence.record_id}</span>
                </div>
              )}
              {evidence?.field && (
                <div className="flex items-center justify-between">
                  <span className="text-[11px] uppercase tracking-[0.08em] text-ink-500">
                    Field
                  </span>
                  <span className="font-mono text-xs text-ink-900">{evidence.field}</span>
                </div>
              )}
              {evidence?.observed_value && (
                <div className="pt-2 border-t border-sand-200">
                  <div className="text-[11px] uppercase tracking-[0.08em] text-ink-500 mb-1">
                    Observed Value
                  </div>
                  <div className="font-mono text-xs text-ink-900 break-all">
                    {evidence.observed_value}
                  </div>
                </div>
              )}
              {!evidence && (
                <p className="text-xs text-ink-500">
                  Validated citation reference linked to deterministic PostgreSQL evidence.
                </p>
              )}
            </div>
          </div>
        </Drawer>
      )}
    </>
  );
};

export interface AmountCellProps {
  amount: string | null | undefined;
  currency?: string;
  variance?: string | null;
  className?: string;
}

export const AmountCell: React.FC<AmountCellProps> = ({
  amount,
  currency = "INR",
  variance,
  className,
}) => {
  const trimmedVar = variance ? String(variance).trim() : "";
  const hasNonZeroVar =
    Boolean(trimmedVar) && !/^-?0+(?:\.0+)?$/.test(trimmedVar);
  const isNegativeVar = trimmedVar.startsWith("-");
  const formattedVar = hasNonZeroVar
    ? `${isNegativeVar ? "" : "+"}${formatInrString(trimmedVar, currency)}`
    : null;

  return (
    <div className={cn("inline-flex flex-col items-end font-mono tabular-nums", className)}>
      <span className="text-ink-900 font-medium">{formatInrString(amount, currency)}</span>
      {formattedVar && (
        <span
          className={cn(
            "text-[11px] font-semibold",
            isNegativeVar ? "text-status-success-fg" : "text-status-danger-fg"
          )}
        >
          Δ {formattedVar}
        </span>
      )}
    </div>
  );
};
