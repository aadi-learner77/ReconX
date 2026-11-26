import React, { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileCheck2,
  FileText,
  Lock,
  PackageCheck,
  Receipt,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  AmountCell,
  Badge,
  Button,
  Card,
  CitationChip,
  Drawer,
  EmptyState,
  PageCaption,
  PageSkeleton,
  StatusPill,
  Stepper,
  toast,
} from "../components/ui";
import { flowAccentForType, flowControlStyle, flowEdgeStyle } from "../theme/flowTheme";
import { formatInrString } from "../utils/money";

function iconForNodeType(nodeType: string) {
  const t = nodeType.toUpperCase();
  if (t.includes("VENDOR")) return Building2;
  if (t.includes("PURCHASEORDER") || t === "PO") return FileText;
  if (t.includes("GOODSRECEIPT") || t.includes("GRN")) return PackageCheck;
  if (t.includes("INVOICE")) return Receipt;
  if (t.includes("EXCEPTION")) return AlertTriangle;
  if (t.includes("APPROVAL")) return CheckCircle2;
  if (t.includes("INVESTIGATION")) return Sparkles;
  if (t.includes("RISK")) return ShieldAlert;
  return FileCheck2;
}

const EvidenceNodeCard: React.FC<NodeProps> = ({ data, selected }) => {
  const nodeType = String(data?.raw?.type || "Record");
  const label = String(data?.raw?.label || data?.label || "");
  const Icon = iconForNodeType(nodeType);
  const accent = flowAccentForType(nodeType);

  return (
    <div
      className="rounded-card bg-paper border px-3.5 py-2.5 min-w-[205px] max-w-[240px] shadow-card transition-all"
      style={{
        borderColor: selected ? "var(--ink-900)" : "var(--sand-200)",
        borderLeftWidth: "4px",
        borderLeftColor: accent,
      }}
    >
      <Handle type="target" position={Position.Left} className="!bg-ink-500 !w-2 !h-2" />
      <div className="flex items-center gap-2">
        <Icon className="w-3.5 h-3.5 shrink-0 text-ink-700" aria-hidden="true" />
        <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-500 truncate">
          {nodeType}
        </span>
      </div>
      <div className="font-mono text-xs font-semibold text-ink-900 mt-1 truncate">{label}</div>
      <Handle type="source" position={Position.Right} className="!bg-ink-500 !w-2 !h-2" />
    </div>
  );
};

const NODE_TYPES = { evidenceNode: EvidenceNodeCard };

export const TransactionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [expandedLines, setExpandedLines] = useState<Record<string, boolean>>({});
  const [aiDrawerOpen, setAiDrawerOpen] = useState(false);
  const [rationale, setRationale] = useState("");

  const { data: bundle, isLoading, error } = useQuery({
    queryKey: ["transaction", id],
    queryFn: () => api.getTransaction(id!),
    enabled: Boolean(id),
  });

  const { data: graphData } = useQuery({
    queryKey: ["transaction-graph", id],
    queryFn: () => api.getTransactionGraph(id!),
    enabled: Boolean(id),
    retry: false,
  });

  const primaryException = bundle?.exceptions?.[0];

  const { data: exceptionDetail } = useQuery({
    queryKey: ["exception", primaryException?.id],
    queryFn: () => api.getException(primaryException!.id),
    enabled: Boolean(primaryException?.id),
    retry: false,
  });

  const reconcileMut = useMutation({
    mutationFn: () => api.reconcileTransaction(id!),
    onSuccess: () => {
      toast.success("Reconciliation completed");
      qc.invalidateQueries({ queryKey: ["transaction", id] });
      qc.invalidateQueries({ queryKey: ["transaction-graph", id] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
    onError: (e: Error) => toast.error(e.message || "Reconciliation failed"),
  });

  const riskMut = useMutation({
    mutationFn: () => api.getTransactionRisk(id!),
    onSuccess: () => {
      toast.success("Risk indicators refreshed");
      qc.invalidateQueries({ queryKey: ["transaction", id] });
    },
  });

  const investigateMut = useMutation({
    mutationFn: (caseId: string) => api.startInvestigation(caseId),
    onSuccess: () => {
      toast.success("AI Investigation completed");
      qc.invalidateQueries({ queryKey: ["exception", primaryException?.id] });
      qc.invalidateQueries({ queryKey: ["transaction", id] });
    },
    onError: (e: Error) => toast.error(e.message || "Investigation failed"),
  });

  const decisionMut = useMutation({
    mutationFn: ({ decision }: { decision: "APPROVED" | "REJECTED" }) =>
      api.decideException(
        primaryException!.id,
        decision,
        rationale.trim(),
        exceptionDetail?.version || 1
      ),
    onSuccess: (_, vars) => {
      toast.success(`Exception ${vars.decision.toLowerCase()}`);
      setRationale("");
      qc.invalidateQueries({ queryKey: ["exception", primaryException?.id] });
      qc.invalidateQueries({ queryKey: ["transaction", id] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
    onError: (e: Error) => toast.error(e.message || "Decision failed"),
  });

  const rfNodes: Node[] = useMemo(
    () =>
      (graphData?.nodes || []).map((n: any, idx: number) => ({
        id: n.id,
        type: "evidenceNode",
        position: { x: (idx % 4) * 265, y: Math.floor(idx / 4) * 115 },
        data: { label: `${n.type}: ${n.label}`, raw: n },
      })),
    [graphData]
  );

  const rfEdges: Edge[] = useMemo(
    () =>
      (graphData?.edges || []).map((e: any) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        animated: true,
        style: flowEdgeStyle(false),
        labelStyle: { fontSize: 10, fill: "var(--ink-500)", fontFamily: "JetBrains Mono, monospace" },
      })),
    [graphData]
  );

  if (isLoading) return <PageSkeleton />;
  if (error || !bundle) {
    return (
      <Card className="border-status-danger-fg/30 bg-status-danger-bg text-status-danger-fg text-sm">
        Transaction not found or unauthorized.
      </Card>
    );
  }

  const poLines = bundle.purchase_order?.lines || [];
  const grnLines = bundle.goods_receipts.flatMap((g) => g.lines);
  const invLines = bundle.invoices.flatMap((i) => i.lines);

  const totalOrderedQty = poLines.reduce((s, l) => s + Number(l.quantity || 0), 0);
  const totalAcceptedQty = grnLines.reduce((s, l) => s + Number(l.accepted_qty || 0), 0);
  const totalInvoicedQty = invLines.reduce((s, l) => s + Number(l.quantity || 0), 0);
  const headerQtyDelta = totalInvoicedQty - totalAcceptedQty;
  const poTotalNum = Number(bundle.purchase_order?.total_amount || 0);
  const invTotalNum = bundle.invoices.reduce((s, i) => s + Number(i.total_amount || 0), 0);
  const hasHeaderAmountMismatch =
    bundle.purchase_order && bundle.invoices.length > 0 && Math.abs(invTotalNum - poTotalNum) > 0.01;
  const hasGrnMismatch = bundle.goods_receipts.length === 0 || totalAcceptedQty !== totalOrderedQty;
  const hasInvMismatch = bundle.invoices.length === 0 || headerQtyDelta !== 0 || hasHeaderAmountMismatch;

  const latestInvestigation = exceptionDetail?.investigations?.[0];
  const canApprove = hasPermission("exceptions:approve");

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <PageCaption
          module="Module / Three-Way Match Detail"
          index={bundle.purchase_order?.po_number || bundle.transaction_id.slice(0, 8)}
        />
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="font-display text-3xl font-bold text-ink-900">
                {bundle.purchase_order?.po_number || `Transaction ${bundle.transaction_id.slice(0, 8)}`}
              </h1>
              <StatusPill value={bundle.latest_reconciliation?.outcome || bundle.current_status} />
            </div>
            <p className="text-sm text-ink-500 mt-1">
              Vendor:{" "}
              <Link to={`/vendors/${bundle.vendor.id}`} className="text-ink-900 underline font-medium">
                {bundle.vendor.legal_name}
              </Link>{" "}
              • Tax ID: <span className="font-mono">{bundle.vendor.tax_identifier || "N/A"}</span>
            </p>
          </div>

          <div className="flex flex-col items-end gap-3">
            {bundle.purchase_order && (
              <div className="font-mono tabular-nums text-2xl md:text-3xl font-bold text-ink-900">
                {formatInrString(bundle.purchase_order.total_amount, bundle.purchase_order.currency)}
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              {primaryException && (
                <Button variant="secondary" size="sm" onClick={() => setAiDrawerOpen(true)}>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>AI Investigation</span>
                </Button>
              )}
              {primaryException && (
                <Link
                  to={`/exceptions/${primaryException.id}`}
                  className="inline-flex items-center px-3 py-1.5 rounded-control border border-status-danger-fg/40 bg-status-danger-bg text-status-danger-fg text-xs font-semibold hover:opacity-90"
                >
                  Open Case →
                </Link>
              )}
              <Button variant="outline" size="sm" loading={riskMut.isPending} onClick={() => riskMut.mutate()}>
                Refresh Risk Indicators
              </Button>
              {hasPermission("reconciliation:run") && (
                <Button
                  size="sm"
                  loading={reconcileMut.isPending}
                  onClick={() => reconcileMut.mutate()}
                >
                  {reconcileMut.isPending ? "Reconciling..." : "Reconcile"}
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Three Side-by-Side Document Cards with Vertical Connectors */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-0 rounded-card border border-sand-200 bg-paper shadow-card overflow-hidden md:divide-x md:divide-sand-200">
        {/* Card 1: Purchase Order */}
        <div className="p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-ink-500 uppercase tracking-[0.08em] inline-flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" />
              Purchase Order
            </span>
            <Badge value="Baseline" tone="neutral" />
          </div>
          {bundle.purchase_order ? (
            <div className="space-y-2 text-sm">
              <div className="font-mono font-semibold text-ink-900">
                {bundle.purchase_order.po_number}
              </div>
              <div className="text-ink-500 font-mono text-xs">
                Date: {bundle.purchase_order.issue_date} • Ordered: {totalOrderedQty}
              </div>
              <div className="pt-1">
                <AmountCell
                  amount={bundle.purchase_order.total_amount}
                  currency={bundle.purchase_order.currency}
                />
              </div>
            </div>
          ) : (
            <div className="text-sm text-status-warning-fg font-medium">Missing PO</div>
          )}
        </div>

        {/* Card 2: Goods Receipts */}
        <div
          className={`p-5 space-y-3 transition-colors ${
            hasGrnMismatch ? "bg-status-warning-bg/35" : ""
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] font-semibold text-ink-500 uppercase tracking-[0.08em] inline-flex items-center gap-1.5">
              <PackageCheck className="w-3.5 h-3.5" />
              Goods Receipts ({bundle.goods_receipts.length})
            </span>
            {hasGrnMismatch && totalOrderedQty > 0 && (
              <Badge
                value={`${totalAcceptedQty - totalOrderedQty >= 0 ? "+" : ""}${totalAcceptedQty - totalOrderedQty} vs PO`}
                tone="warning"
              />
            )}
          </div>
          {bundle.goods_receipts.length ? (
            <ul className="space-y-1.5 text-sm">
              {bundle.goods_receipts.map((g) => (
                <li key={g.id} className="flex justify-between font-mono text-xs">
                  <span className="font-semibold text-ink-900">{g.grn_number}</span>
                  <span className="text-ink-700">
                    Acc: {g.lines.reduce((s, l) => s + Number(l.accepted_qty), 0)} | Rej:{" "}
                    {g.lines.reduce((s, l) => s + Number(l.rejected_qty), 0)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-status-warning-fg font-medium">No GRNs recorded</div>
          )}
        </div>

        {/* Card 3: Supplier Invoices */}
        <div
          className={`p-5 space-y-3 transition-colors ${
            hasInvMismatch ? "bg-status-danger-bg/35" : ""
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] font-semibold text-ink-500 uppercase tracking-[0.08em] inline-flex items-center gap-1.5">
              <Receipt className="w-3.5 h-3.5" />
              Supplier Invoices ({bundle.invoices.length})
            </span>
            {headerQtyDelta !== 0 && (
              <Badge
                value={`${headerQtyDelta > 0 ? "+" : ""}${headerQtyDelta} EA vs GRN`}
                tone="danger"
              />
            )}
          </div>
          {bundle.invoices.length === 0 ? (
            <div className="text-sm text-status-warning-fg font-medium">No invoices recorded</div>
          ) : (
            bundle.invoices.map((inv) => (
              <div
                key={inv.id}
                className="text-sm border-t border-sand-200 pt-2 first:border-t-0 first:pt-0"
              >
                <div className="font-mono font-semibold text-ink-900">{inv.invoice_number}</div>
                <div className="font-mono text-xs text-ink-700 mt-0.5">
                  {formatInrString(inv.total_amount, inv.currency)} (Tax:{" "}
                  {formatInrString(inv.tax_amount, inv.currency)})
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Expandable Line-Items Comparison Table */}
      <Card className="overflow-x-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display text-lg font-bold text-ink-900">
            Side-by-Side Line Comparison (PO vs GRN Accepted vs Invoiced)
          </h2>
          <span className="text-[11px] uppercase tracking-[0.08em] text-ink-500">
            Click row to expand calculation
          </span>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-[0.08em] text-ink-500 border-b border-sand-200">
              <th scope="col" className="py-2.5 w-8" />
              <th scope="col" className="py-2.5">Item</th>
              <th scope="col" className="py-2.5">PO Qty / Price</th>
              <th scope="col" className="py-2.5">GRN Accepted / Rej</th>
              <th scope="col" className="py-2.5">Invoiced Qty / Price</th>
              <th scope="col" className="py-2.5">Rule</th>
              <th scope="col" className="py-2.5 text-right">Variance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-sand-200">
            {poLines.map((pl) => {
              const acc = grnLines
                .filter((g) => g.po_line_id === pl.id || g.item_code === pl.item_code)
                .reduce((s, g) => s + Number(g.accepted_qty), 0);
              const rej = grnLines
                .filter((g) => g.po_line_id === pl.id || g.item_code === pl.item_code)
                .reduce((s, g) => s + Number(g.rejected_qty), 0);
              const matchedInvs = invLines.filter(
                (i) => i.po_line_id === pl.id || i.item_code === pl.item_code
              );
              const invQty = matchedInvs.reduce((s, i) => s + Number(i.quantity), 0);
              const invPrice = matchedInvs[0]?.unit_price || "—";
              const qtyDiff = invQty - acc;
              const priceDiff =
                invPrice !== "—" ? Number(invPrice) - Number(pl.unit_price) : 0;
              const hasDiff = qtyDiff !== 0 || Math.abs(priceDiff) > 0.0001;
              const matchedRule = bundle.latest_reconciliation?.results.find(
                (r) =>
                  r.entity_line_id === pl.id ||
                  (qtyDiff !== 0 && r.field_name.includes("quantity")) ||
                  (priceDiff !== 0 && r.field_name.includes("price"))
              );
              const isExpanded = Boolean(expandedLines[pl.id]);

              return (
                <React.Fragment key={pl.id}>
                  <tr
                    onClick={() =>
                      setExpandedLines((prev) => ({ ...prev, [pl.id]: !prev[pl.id] }))
                    }
                    className={`cursor-pointer transition-colors hover:bg-sand-100/70 ${
                      hasDiff ? "bg-status-danger-bg/40" : ""
                    }`}
                  >
                    <td className="py-3 text-ink-500">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </td>
                    <td className="py-3 font-medium text-ink-900">
                      <span className="font-mono text-xs">{pl.item_code}</span> — {pl.description}
                    </td>
                    <td className="py-3 font-mono text-xs">
                      {pl.quantity} {pl.uom} @ {pl.unit_price}
                    </td>
                    <td className="py-3 font-mono text-xs">
                      {acc} {pl.uom} (Rej {rej})
                    </td>
                    <td className="py-3 font-mono text-xs">
                      {invQty} {pl.uom} @ {invPrice}
                    </td>
                    <td className="py-3">
                      {matchedRule ? (
                        <Badge
                          value={`Rule ${matchedRule.rule_id}`}
                          tone={matchedRule.result === "FAIL" ? "danger" : "neutral"}
                        />
                      ) : (
                        <span className="font-mono text-xs text-ink-500">—</span>
                      )}
                    </td>
                    <td className="py-3 font-mono text-xs text-right font-semibold">
                      {hasDiff ? `Qty Δ=${qtyDiff}` : "Exact"}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr className="bg-sand-50">
                      <td colSpan={7} className="p-4">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
                          <div className="p-2.5 rounded-control border border-sand-200 bg-paper">
                            <div className="text-[10px] uppercase text-ink-500">1. Ordered</div>
                            <div className="font-semibold text-ink-900 mt-0.5">
                              {pl.quantity} {pl.uom} × {pl.unit_price}
                            </div>
                          </div>
                          <div className="p-2.5 rounded-control border border-sand-200 bg-paper">
                            <div className="text-[10px] uppercase text-ink-500">2. GRN Accepted</div>
                            <div className="font-semibold text-ink-900 mt-0.5">
                              {acc} {pl.uom} (Rej: {rej})
                            </div>
                          </div>
                          <div className="p-2.5 rounded-control border border-sand-200 bg-paper">
                            <div className="text-[10px] uppercase text-ink-500">3. Billed</div>
                            <div className="font-semibold text-ink-900 mt-0.5">
                              {invQty} {pl.uom} × {invPrice}
                            </div>
                          </div>
                          <div className="p-2.5 rounded-control border border-sand-200 bg-paper">
                            <div className="text-[10px] uppercase text-ink-500">
                              4. Deterministic Delta
                            </div>
                            <div className="font-semibold text-status-danger-fg mt-0.5">
                              ΔQty = {invQty} - {acc} = {qtyDiff} {pl.uom}
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </Card>

      {/* Rule-by-rule breakdown */}
      {bundle.latest_reconciliation && (
        <Card className="overflow-x-auto">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
            <h2 className="font-display text-lg font-bold text-ink-900">
              Deterministic Rule Breakdown (v{bundle.latest_reconciliation.rule_version})
            </h2>
            <div className="text-xs font-mono text-ink-700">
              Undisputed:{" "}
              {formatInrString(String(bundle.latest_reconciliation.totals.undisputed_amount || "0.00"))} |
              Disputed:{" "}
              {formatInrString(String(bundle.latest_reconciliation.totals.disputed_amount || "0.00"))}
            </div>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-[0.08em] text-ink-500 border-b border-sand-200">
                <th scope="col" className="py-2.5">Rule ID</th>
                <th scope="col" className="py-2.5">Field</th>
                <th scope="col" className="py-2.5">Expected</th>
                <th scope="col" className="py-2.5">Actual</th>
                <th scope="col" className="py-2.5">Variance</th>
                <th scope="col" className="py-2.5">Tolerance</th>
                <th scope="col" className="py-2.5">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sand-200">
              {bundle.latest_reconciliation.results.map((r) => (
                <tr key={r.id}>
                  <td className="py-2.5 font-mono font-semibold text-ink-900">{r.rule_id}</td>
                  <td className="py-2.5 text-ink-700">{r.field_name}</td>
                  <td className="py-2.5 font-mono text-xs">{r.expected_value}</td>
                  <td className="py-2.5 font-mono text-xs">{r.actual_value}</td>
                  <td className="py-2.5 font-mono text-xs">{r.variance}</td>
                  <td className="py-2.5 text-xs text-ink-500">{r.tolerance_applied}</td>
                  <td className="py-2.5">
                    <StatusPill value={r.result} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Approval Panel + Risk Indicators */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-bold text-ink-900">
              Maker-Checker Approval Panel
            </h2>
            {primaryException && <StatusPill value={primaryException.status} />}
          </div>
          <Stepper
            activeId={
              primaryException?.status === "APPROVED" || primaryException?.status === "REJECTED"
                ? "checker"
                : latestInvestigation
                  ? "investigated"
                  : "maker"
            }
            steps={[
              { id: "maker", label: "Exception Raised", state: primaryException ? "done" : "idle" },
              {
                id: "investigated",
                label: "Evidence Verified",
                state: latestInvestigation ? "done" : primaryException ? "running" : "idle",
              },
              {
                id: "checker",
                label: "Checker Decision",
                state:
                  primaryException?.status === "APPROVED" || primaryException?.status === "REJECTED"
                    ? "done"
                    : "idle",
              },
            ]}
          />
          {!primaryException ? (
            <EmptyState
              title="No Exception Requires Approval"
              description="This transaction matched cleanly or has no open exception case."
            />
          ) : (
            <div className="space-y-3">
              <label className="block space-y-1.5">
                <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                  Approval Rationale (Required)
                </span>
                <textarea
                  rows={3}
                  disabled={!canApprove}
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  placeholder="Document verified PO/GRN/Invoice evidence supporting your decision..."
                  className="w-full rounded-control border border-sand-200 bg-paper px-3 py-2 text-sm text-ink-900 disabled:opacity-60"
                />
              </label>

              {!canApprove ? (
                <div className="p-3 rounded-control border border-sand-200 bg-sand-100 text-xs text-ink-700 flex items-start gap-2">
                  <Lock className="w-4 h-4 shrink-0 mt-0.5 text-ink-500" />
                  <span>
                    Approval disabled (Maker-Checker / 403 RBAC): Operators cannot approve or reject
                    exceptions. An Approver or Admin must submit the final decision.
                  </span>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={!rationale.trim()}
                    loading={decisionMut.isPending}
                    onClick={() => decisionMut.mutate({ decision: "APPROVED" })}
                  >
                    Approve Exception
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={!rationale.trim()}
                    loading={decisionMut.isPending}
                    onClick={() => decisionMut.mutate({ decision: "REJECTED" })}
                  >
                    Reject Exception
                  </Button>
                </div>
              )}
            </div>
          )}
        </Card>

        <Card>
          <h2 className="font-display text-lg font-bold text-ink-900 mb-1">Risk Indicators</h2>
          <p className="text-xs text-ink-500 mb-3">
            Explainable risk indicators for human review — not proof of fraud.
          </p>
          {bundle.risk_signals.length === 0 ? (
            <div className="text-sm text-ink-500">No risk signals recorded.</div>
          ) : (
            <ul className="space-y-2.5">
              {bundle.risk_signals.map((s) => (
                <li
                  key={s.id}
                  className="p-3.5 rounded-card border border-status-info-fg/30 bg-status-info-bg/60 text-xs"
                >
                  <div className="flex justify-between font-semibold text-status-info-fg">
                    <span>{s.signal_type}</span>
                    <span className="font-mono">Score: {s.score}</span>
                  </div>
                  <div className="text-ink-900 mt-1">
                    {(s.reason.contributing_signals || []).join("; ")}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* Neo4j Evidence Graph (React Flow) */}
      {graphData && rfNodes.length > 0 && (
        <Card>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display text-lg font-bold text-ink-900">
              Financial Evidence Graph ({graphData.source === "neo4j" ? "Neo4j Live" : "Relational Projection"})
            </h2>
            {selectedNode && (
              <span className="text-xs text-ink-900 font-mono">
                Selected: {selectedNode.type} — {selectedNode.label}
              </span>
            )}
          </div>
          <div className="h-80 border border-sand-200 rounded-card bg-sand-50 overflow-hidden">
            <ReactFlow
              nodes={rfNodes}
              edges={rfEdges}
              nodeTypes={NODE_TYPES}
              fitView
              onNodeClick={(_, node) => setSelectedNode((node.data as any)?.raw)}
            >
              <Background color="var(--sand-200)" gap={18} />
              <Controls style={flowControlStyle} />
              <MiniMap style={flowControlStyle} nodeColor="var(--sand-300)" />
            </ReactFlow>
          </div>
        </Card>
      )}

      {/* Right Drawer: AI Investigation Summary */}
      <Drawer
        open={aiDrawerOpen}
        onClose={() => setAiDrawerOpen(false)}
        title="AI Investigation Summary"
        subtitle={
          latestInvestigation
            ? `Provider: ${latestInvestigation.model_provider}`
            : "Run orchestrated 7-stage investigation"
        }
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Badge value="Generated · verify against evidence" tone="info" />
            {primaryException && (
              <Button
                variant="secondary"
                size="sm"
                loading={investigateMut.isPending}
                onClick={() => investigateMut.mutate(primaryException.id)}
              >
                {latestInvestigation ? "Re-run Investigation" : "Run Investigation"}
              </Button>
            )}
          </div>

          {!latestInvestigation ? (
            <EmptyState
              title="No Investigation Yet"
              description="Trigger the 7-stage AI investigation to generate an evidence-cited summary."
            />
          ) : (
            <div className="space-y-4 text-sm">
              <div className="rounded-card border border-sand-200 bg-sand-50 p-4 text-ink-900 leading-relaxed">
                {String(
                  latestInvestigation.structured_output?.summary ||
                    latestInvestigation.structured_output?.narrative ||
                    "Investigation completed."
                )}
              </div>

              <div className="space-y-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                  Verified Evidence Citations
                </div>
                <div className="flex flex-wrap gap-2">
                  {(
                    latestInvestigation.structured_output?.evidence_citations ||
                    latestInvestigation.structured_output?.citations ||
                    []
                  ).map((cit: any, i: number) => (
                    <CitationChip
                      key={cit.citation_id || i}
                      id={cit.citation_id || `CIT-00${i + 1}`}
                      evidence={{
                        citation_id: cit.citation_id || `CIT-00${i + 1}`,
                        source_type: cit.source_type || cit.type,
                        record_id: cit.record_id || cit.id,
                        field: cit.field,
                        observed_value: cit.observed_value || cit.label,
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </Drawer>
    </div>
  );
};
