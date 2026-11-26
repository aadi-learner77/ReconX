import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import ReactFlow, { Background, Controls, MiniMap, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, PageCaption, PageSkeleton, StatusPill } from "../components/ui";
import { flowControlStyle, flowEdgeStyle, flowNodeStyle } from "../theme/flowTheme";
import { formatInrString } from "../utils/money";

export const TransactionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const [selectedNode, setSelectedNode] = useState<any | null>(null);

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

  const reconcileMut = useMutation({
    mutationFn: () => api.reconcileTransaction(id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transaction", id] });
      qc.invalidateQueries({ queryKey: ["transaction-graph", id] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const riskMut = useMutation({
    mutationFn: () => api.getTransactionRisk(id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transaction", id] }),
  });

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

  const rfNodes: Node[] = (graphData?.nodes || []).map((n: any, idx: number) => ({
    id: n.id,
    position: { x: (idx % 4) * 250, y: Math.floor(idx / 4) * 120 },
    data: { label: `${n.type}: ${n.label}`, raw: n },
    style: flowNodeStyle(n.type, selectedNode?.id === n.id),
  }));
  const rfEdges: Edge[] = (graphData?.edges || []).map((e: any) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: true,
    style: flowEdgeStyle(false),
    labelStyle: { fontSize: 10, fill: "var(--ink-500)", fontFamily: "JetBrains Mono, monospace" },
  }));

  return (
    <div className="space-y-8">
      <div>
        <PageCaption
          module="Module / Three-Way Match Detail"
          index={bundle.purchase_order?.po_number || bundle.transaction_id.slice(0, 8)}
        />
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
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

          <div className="flex flex-wrap gap-2">
            {bundle.exceptions.length > 0 && (
              <Link
                to={`/exceptions/${bundle.exceptions[0].id}`}
                className="inline-flex items-center px-3.5 py-2 rounded-control border border-status-danger-fg/40 bg-status-danger-bg text-status-danger-fg text-sm font-semibold hover:opacity-90"
              >
                Investigate Exception →
              </Link>
            )}
            <Button variant="outline" onClick={() => riskMut.mutate()}>
              Refresh Risk Indicators
            </Button>
            {hasPermission("reconciliation:run") && (
              <Button onClick={() => reconcileMut.mutate()} disabled={reconcileMut.isPending}>
                {reconcileMut.isPending ? "Reconciling..." : "Reconcile"}
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Side-by-side PO / GRN / Invoice Header Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="text-[11px] font-semibold text-ink-500 uppercase tracking-[0.08em]">
            Purchase Order
          </div>
          {bundle.purchase_order ? (
            <div className="mt-3 space-y-1.5 text-sm">
              <div className="font-mono font-semibold text-ink-900">
                {bundle.purchase_order.po_number}
              </div>
              <div className="text-ink-500 font-mono text-xs">
                Date: {bundle.purchase_order.issue_date}
              </div>
              <div className="font-mono text-ink-900 font-semibold">
                {formatInrString(bundle.purchase_order.total_amount, bundle.purchase_order.currency)}
              </div>
            </div>
          ) : (
            <div className="mt-3 text-sm text-status-warning-fg font-medium">Missing PO</div>
          )}
        </Card>

        <Card>
          <div className="text-[11px] font-semibold text-ink-500 uppercase tracking-[0.08em]">
            Goods Receipts ({bundle.goods_receipts.length})
          </div>
          {bundle.goods_receipts.length ? (
            <ul className="mt-3 space-y-1.5 text-sm">
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
            <div className="mt-3 text-sm text-status-warning-fg font-medium">No GRNs recorded</div>
          )}
        </Card>

        <Card>
          <div className="text-[11px] font-semibold text-ink-500 uppercase tracking-[0.08em]">
            Supplier Invoices ({bundle.invoices.length})
          </div>
          {bundle.invoices.map((inv) => (
            <div key={inv.id} className="mt-2.5 text-sm border-t border-sand-200 pt-2 first:border-t-0 first:pt-0">
              <div className="font-mono font-semibold text-ink-900">{inv.invoice_number}</div>
              <div className="font-mono text-xs text-ink-700 mt-0.5">
                {formatInrString(inv.total_amount, inv.currency)} (Tax:{" "}
                {formatInrString(inv.tax_amount, inv.currency)})
              </div>
            </div>
          ))}
        </Card>
      </div>

      {/* Line-level Side-by-Side Comparison */}
      <Card className="overflow-x-auto">
        <h2 className="font-display text-lg font-bold text-ink-900 mb-4">
          Side-by-Side Line Comparison (PO vs GRN Accepted vs Invoiced)
        </h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-[0.08em] text-ink-500 border-b border-sand-200">
              <th scope="col" className="py-2.5">Item</th>
              <th scope="col" className="py-2.5">PO Qty / Price</th>
              <th scope="col" className="py-2.5">GRN Accepted / Rej</th>
              <th scope="col" className="py-2.5">Invoiced Qty / Price</th>
              <th scope="col" className="py-2.5 text-right">Difference</th>
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
              const hasDiff =
                qtyDiff !== 0 || (invPrice !== "—" && invPrice !== pl.unit_price && Number(invPrice) !== Number(pl.unit_price));
              return (
                <tr key={pl.id} className={hasDiff ? "bg-status-danger-bg/45" : ""}>
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
                  <td className="py-3 font-mono text-xs text-right font-semibold">
                    {hasDiff ? `Qty Δ=${qtyDiff}` : "Exact"}
                  </td>
                </tr>
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

      {/* Exceptions & Risk Indicators */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h2 className="font-display text-lg font-bold text-ink-900 mb-3">
            Exceptions ({bundle.exceptions.length})
          </h2>
          {bundle.exceptions.length === 0 ? (
            <div className="text-sm text-ink-500">No exceptions for this transaction.</div>
          ) : (
            <ul className="space-y-2.5">
              {bundle.exceptions.map((e) => (
                <li
                  key={e.id}
                  className="p-3.5 rounded-card border border-sand-200 bg-sand-50 flex justify-between items-start gap-3"
                >
                  <div>
                    <Link
                      to={`/exceptions/${e.id}`}
                      className="text-sm font-semibold text-ink-900 underline"
                    >
                      {e.type} (<span className="font-mono">{e.rule_id}</span>)
                    </Link>
                    <p className="text-xs text-ink-700 mt-1">{e.summary}</p>
                  </div>
                  <StatusPill value={e.status} />
                </li>
              ))}
            </ul>
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

      {/* Relational Financial Evidence Graph (D2, React Flow) */}
      {graphData && rfNodes.length > 0 && (
        <Card>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display text-lg font-bold text-ink-900">
              Financial Evidence Graph (PostgreSQL Relational Projection)
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
    </div>
  );
};
