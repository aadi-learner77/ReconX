export const chartTheme = {
  gridStroke: "var(--sand-200)",
  axisStroke: "var(--ink-500)",
  axisTick: {
    fill: "var(--ink-500)",
    fontSize: 11,
    fontFamily: "JetBrains Mono, monospace",
  },
  tooltipStyle: {
    backgroundColor: "var(--paper)",
    border: "1px solid var(--sand-200)",
    borderRadius: "12px",
    color: "var(--ink-900)",
    fontSize: "12px",
    boxShadow: "var(--shadow-soft)",
  },
  barRadius: [8, 8, 0, 0] as [number, number, number, number],
  palette: {
    primary: "var(--ink-900)",
    sand: "var(--sand-300)",
    matched: "var(--status-success-fg)",
    variance: "var(--status-warning-fg)",
    exception: "var(--status-danger-fg)",
    info: "var(--status-info-fg)",
    neutral: "var(--status-neutral-fg)",
  },
};

export function outcomeBarColor(outcome: string): string {
  const key = outcome.toUpperCase();
  if (key === "MATCHED") return chartTheme.palette.matched;
  if (key === "EXCEPTION") return chartTheme.palette.exception;
  if (key === "INCOMPLETE" || key === "REVIEW_REQUIRED") return chartTheme.palette.variance;
  return chartTheme.palette.primary;
}
