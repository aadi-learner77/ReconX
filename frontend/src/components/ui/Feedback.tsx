import React from "react";
import { cn } from "../../utils/cn";

export const Skeleton: React.FC<{ className?: string }> = ({ className }) => (
  <div
    aria-hidden="true"
    className={cn("animate-shimmer rounded-card bg-sand-100 border border-sand-200/60", className)}
  />
);

export const PageSkeleton: React.FC = () => (
  <div className="space-y-6" aria-label="Loading content">
    <Skeleton className="h-32 w-full rounded-hero" />
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Skeleton className="h-28" />
      <Skeleton className="h-28" />
      <Skeleton className="h-28" />
      <Skeleton className="h-28" />
    </div>
    <Skeleton className="h-64 w-full" />
  </div>
);

export const EmptyState: React.FC<{
  title: string;
  description: string;
  action?: React.ReactNode;
}> = ({ title, description, action }) => (
  <div className="rounded-card border border-sand-200 bg-paper p-10 text-center space-y-3 shadow-hairline">
    <svg
      viewBox="0 0 80 56"
      fill="none"
      aria-hidden="true"
      className="w-20 h-14 mx-auto text-sand-400"
    >
      <rect x="6" y="8" width="44" height="40" rx="8" stroke="currentColor" strokeWidth="2" />
      <rect x="28" y="4" width="46" height="40" rx="8" fill="var(--sand-100)" stroke="currentColor" strokeWidth="2" />
      <path d="M38 18H64M38 26H58M38 34H52" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
    <div className="font-display text-base font-bold text-ink-900">{title}</div>
    <p className="text-xs text-ink-500 max-w-sm mx-auto">{description}</p>
    {action && <div className="pt-2">{action}</div>}
  </div>
);
