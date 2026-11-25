import React from "react";

const STYLE_MAP: Record<string, string> = {
  MATCHED: "bg-emerald-50 text-emerald-800 border-emerald-200",
  APPROVED: "bg-emerald-50 text-emerald-800 border-emerald-200",
  SUCCEEDED: "bg-emerald-50 text-emerald-800 border-emerald-200",
  EXTRACTED: "bg-emerald-50 text-emerald-800 border-emerald-200",
  VERIFIED: "bg-emerald-50 text-emerald-800 border-emerald-200",
  PASS: "bg-emerald-50 text-emerald-800 border-emerald-200",
  MATCHED_WITH_TOLERANCE: "bg-teal-50 text-teal-800 border-teal-200",
  PASS_WITH_TOLERANCE: "bg-teal-50 text-teal-800 border-teal-200",
  EXCEPTION: "bg-rose-50 text-rose-800 border-rose-200",
  REJECTED: "bg-rose-50 text-rose-800 border-rose-200",
  FAILED: "bg-rose-50 text-rose-800 border-rose-200",
  FAIL: "bg-rose-50 text-rose-800 border-rose-200",
  HIGH: "bg-rose-50 text-rose-800 border-rose-200",
  REVIEW_REQUIRED: "bg-amber-50 text-amber-800 border-amber-200",
  INCOMPLETE: "bg-amber-50 text-amber-800 border-amber-200",
  INFO_REQUESTED: "bg-amber-50 text-amber-800 border-amber-200",
  ESCALATED: "bg-orange-50 text-orange-800 border-orange-200",
  MEDIUM: "bg-amber-50 text-amber-800 border-amber-200",
  OPEN: "bg-sky-50 text-sky-800 border-sky-200",
  IN_REVIEW: "bg-indigo-50 text-indigo-800 border-indigo-200",
  QUEUED: "bg-slate-100 text-slate-700 border-slate-200",
  PROCESSING: "bg-blue-50 text-blue-800 border-blue-200",
  LOW: "bg-slate-100 text-slate-700 border-slate-200",
  NONE: "bg-slate-100 text-slate-600 border-slate-200",
};

export const StatusBadge: React.FC<{ value: string | null | undefined }> = ({ value }) => {
  const label = value || "UNKNOWN";
  const cls = STYLE_MAP[label] || "bg-slate-100 text-slate-700 border-slate-200";
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${cls}`}
      data-testid="status-badge"
    >
      {label}
    </span>
  );
};
