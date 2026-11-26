import type { CSSProperties } from "react";

export function flowEdgeStyle(highlighted = false): CSSProperties {
  return {
    stroke: highlighted ? "var(--ink-900)" : "var(--ink-500)",
    strokeWidth: highlighted ? 2 : 1.5,
  };
}

export function flowAccentForType(nodeType: string): string {
  const t = nodeType.toUpperCase();
  if (t.includes("EXCEPTION")) return "var(--status-danger-fg)";
  if (t.includes("GOODSRECEIPT") || t.includes("GRN") || t.includes("APPROVAL")) {
    return "var(--status-success-fg)";
  }
  if (t.includes("INVOICE")) return "var(--status-warning-fg)";
  if (t.includes("RISK") || t.includes("INVESTIGATION")) return "var(--status-info-fg)";
  if (t.includes("DELIVERY") || t.includes("PURCHASEORDER") || t.includes("PO")) {
    return "var(--ink-900)";
  }
  return "var(--sand-400)";
}

export function flowNodeStyle(nodeType: string, selected = false): CSSProperties {
  const accent = flowAccentForType(nodeType);
  return {
    background: "var(--paper)",
    color: "var(--ink-900)",
    border: selected ? "2px solid var(--ink-900)" : "1px solid var(--sand-200)",
    borderLeft: `4px solid ${accent}`,
    borderRadius: "14px",
    fontSize: "12px",
    fontWeight: 500,
    fontFamily: "Inter, sans-serif",
    padding: "10px 12px",
    boxShadow: selected ? "0 0 0 3px var(--sand-300)" : "var(--shadow-soft)",
    width: 224,
  };
}

export const flowControlStyle: CSSProperties = {
  background: "var(--paper)",
  border: "1px solid var(--sand-200)",
  borderRadius: "10px",
  color: "var(--ink-900)",
};
